"""Cadaver's resource expander ($0118ec) in Python: LZSS + adaptive-Huffman ("LZHUF" / LHA -lh1- family).

Transcribed from the 68000 at $0118ec-$011cb6 (entry $0118ec, StartHuff $119c4, dict init $011a4e,
DecodeChar $011a8a, DecodePosition $011b20, update $011b5e, reconst $011c10, bit readers $011bc8/$011be8/$011cb6).
Block format on disk: 4-byte big-endian expanded length, then the MSB-first bit stream.
Used as a library (decode(data_after_length, outlen) -> bytes) and as a script: it checks the
d_code/d_len tables against the ones in a snapshot ($011cce / $011dce) and prints them.

    uv run python reversing/cadaver/py/secrets/cad_lzh.py      (from M68000/)
expected: 'd_code table matches live RAM: 256/256', 'd_len table matches live RAM: 256/256'
"""
import struct, sys, os
N, F, THRESH = 4096, 60, 2
N_CHAR = 256 - THRESH + F          # 314
T = N_CHAR * 2 - 1                 # 627 ; the asm's D6 = $4e6 = 2*T bytes
R = T - 1
MAX_FREQ = 0x8000

def std_tables():
    d_code = []; d_len = []
    # 1 code of len 3 (32 slots), 3 of len 4, 8 of len 5, 12 of len 6, 24 of len 7, 16 of len 8
    code = 0
    for ln, ncodes in ((3, 1), (4, 3), (5, 8), (6, 12), (7, 24), (8, 16)):
        for _ in range(ncodes):
            d_code += [code] * (1 << (8 - ln)); d_len += [ln] * (1 << (8 - ln)); code += 1
    return bytes(d_code), bytes(d_len)
D_CODE, D_LEN = std_tables()

def init_dict():
    """$011a4e: 256 values x13, 256 ascending, 256 descending (255..0), 128 zeros, 128 spaces = 4096 bytes"""
    b = bytearray()
    for v in range(256): b += bytes([v]) * 13
    b += bytes(range(256)); b += bytes(range(255, -1, -1)); b += bytes(128); b += b' ' * 128
    assert len(b) == N
    return b

class Dec:
    def __init__(self, data):
        self.d = data; self.pos = 0; self.bitbuf = 0; self.bitcnt = 0
        self.freq = [0] * (T + 1); self.prnt = [0] * (T + N_CHAR); self.son = [0] * T
        for i in range(N_CHAR):
            self.freq[i] = 1; self.son[i] = i + T; self.prnt[i + T] = i
        i, j = 0, N_CHAR
        while j <= R:
            self.freq[j] = self.freq[i] + self.freq[i + 1]; self.son[j] = i
            self.prnt[i] = self.prnt[i + 1] = j; i += 2; j += 1
        self.freq[T] = 0xffff; self.prnt[R] = 0
    def getbit(self):
        if self.bitcnt == 0:
            self.bitbuf = self.d[self.pos] if self.pos < len(self.d) else 0; self.pos += 1; self.bitcnt = 8
        self.bitcnt -= 1
        return (self.bitbuf >> self.bitcnt) & 1
    def getbits(self, n):
        v = 0
        for _ in range(n): v = (v << 1) | self.getbit()
        return v
    def reconst(self):
        j = 0
        for i in range(T):
            if self.son[i] >= T:
                self.freq[j] = (self.freq[i] + 1) // 2; self.son[j] = self.son[i]; j += 1
        i = 0
        for j in range(N_CHAR, T):
            k = i + 1; f = self.freq[j] = self.freq[i] + self.freq[k]
            k = j - 1
            while f < self.freq[k]: k -= 1
            k += 1; l = (j - k)
            self.freq[k + 1:k + 1 + l] = self.freq[k:k + l]; self.freq[k] = f
            self.son[k + 1:k + 1 + l] = self.son[k:k + l]; self.son[k] = i
            i += 2
        for i in range(T):
            k = self.son[i]
            if k >= T: self.prnt[k] = i
            else: self.prnt[k] = self.prnt[k + 1] = i
    def update(self, c):
        if self.freq[R] == MAX_FREQ: self.reconst()
        c = self.prnt[c + T]
        while True:
            self.freq[c] += 1; k = self.freq[c]
            l = c + 1
            if k > self.freq[l]:
                while k > self.freq[l + 1]: l += 1
                self.freq[c] = self.freq[l]; self.freq[l] = k
                i = self.son[c]; self.prnt[i] = l
                if i < T: self.prnt[i + 1] = l
                j = self.son[l]; self.son[l] = i
                self.prnt[j] = c
                if j < T: self.prnt[j + 1] = c
                self.son[c] = j; c = l
            c = self.prnt[c]
            if c == 0: break
    def decode_char(self):
        c = self.son[R]
        while c < T: c = self.son[c + self.getbit()]
        c -= T; self.update(c); return c
    def decode_pos(self):
        i = self.getbits(8); c = D_CODE[i] << 6; j = D_LEN[i] - 2
        while j > 0: i = (i << 1) | self.getbit(); j -= 1
        return c | (i & 0x3f)

def decode(stream, outlen):
    """stream = bytes after the 4-byte length; returns (bytes, bytes_of_stream_consumed)."""
    dec = Dec(stream); tb = init_dict(); r = N - F; out = bytearray()
    while len(out) < outlen:
        c = dec.decode_char()
        if c < 256:
            out.append(c); tb[r] = c; r = (r + 1) & (N - 1)
        else:
            i = (r - dec.decode_pos() - 1) & (N - 1); j = c - 255 + THRESH
            for k in range(j):
                c = tb[(i + k) & (N - 1)]; out.append(c); tb[r] = c; r = (r + 1) & (N - 1)
    return bytes(out[:outlen]), dec.pos

def decode_block(blk):
    n = struct.unpack('>I', blk[:4])[0]
    return decode(blk[4:], n)

if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
    from ram import ram
    r = ram()
    print('d_code table matches live RAM: %d/256' % sum(a == b for a, b in zip(D_CODE, r[0x11cce:0x11cce + 256])))
    print('d_len table matches live RAM: %d/256' % sum(a == b for a, b in zip(D_LEN, r[0x11dce:0x11dce + 256])))
