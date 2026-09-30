"""lzhuf.py: Cadaver's depacker ($0118ec entry, $011904 body) reimplemented.  It is Yoshizaki's LZHUF
(adaptive Huffman over 314 symbols, N=4096 ring buffer, F=60, THRESHOLD=2, match length c-253 at $011984, r starts at
N-F=$fc4) with one change: the ring buffer is pre-filled by $011a4e with a binary-friendly pattern instead of spaces:
13 copies of each byte 0..255 (3328 bytes), 0..255 ascending, 255..0 descending, 128 x $00, 128 x $20 (4096 bytes).
d_code/d_len tables are the standard ones; they sit at $011cce/$011dce in the image (this module carries its own copy,
built the standard way, and checks it against a snapshot when run as a script).
Usage as module: decode(data, size) -> bytes (data starts AFTER the 4-byte big-endian length).
Script: python3 lzhuf.py <disk.st> <first_sector> <nsectors> [snapshot]  -> decodes, prints length and head;
if a snapshot is given, the d_code/d_len tables are compared with RAM $011cce/$011dce."""
import sys, struct
N = 4096; F = 60; THRESHOLD = 2; N_CHAR = 256 - THRESHOLD + F; T = N_CHAR * 2 - 1; R = T - 1; MAX_FREQ = 0x8000

def std_tables():
    d_code = []; d_len = []
    for ln, cnt_codes in ((3, 1), (4, 3), (5, 8), (6, 12), (7, 24), (8, 16)):
        pass
    # lzhuf.c: d_code run lengths 32,16x? -- derive from the bit length table: 3 bits:32 entries(code 0),
    # 4 bits:48 (codes 1..3, 16 each), 5 bits:64 (codes 4..11, 8 each), 6 bits:48 (codes 12..23, 4 each),
    # 7 bits:48 (codes 24..47, 2 each), 8 bits:16 (codes 48..63, 1 each)
    for ln, per, first, ncodes in ((3, 32, 0, 1), (4, 16, 1, 3), (5, 8, 4, 8), (6, 4, 12, 12), (7, 2, 24, 24), (8, 1, 48, 16)):
        for c in range(first, first + ncodes):
            for _ in range(per):
                d_code.append(c); d_len.append(ln)
    assert len(d_code) == 256
    return d_code, d_len

class Dec:
    def __init__(self, data, d_code=None, d_len=None):
        self.data = data; self.pos = 0; self.getbuf = 0; self.getlen = 0
        self.d_code, self.d_len = (d_code, d_len) if d_code else std_tables()
        self.freq = [0] * (T + 1); self.prnt = [0] * (T + N_CHAR); self.son = [0] * T
        for i in range(N_CHAR):
            self.freq[i] = 1; self.son[i] = i + T; self.prnt[i + T] = i
        i = 0; j = N_CHAR
        while j <= R:
            self.freq[j] = self.freq[i] + self.freq[i + 1]; self.son[j] = i
            self.prnt[i] = self.prnt[i + 1] = j; i += 2; j += 1
        self.freq[T] = 0xffff; self.prnt[R] = 0
    def bit(self):
        if self.getlen == 0:
            b = self.data[self.pos] if self.pos < len(self.data) else 0
            self.pos += 1; self.getbuf = b; self.getlen = 8
        self.getlen -= 1
        return (self.getbuf >> self.getlen) & 1
    def byte(self):
        v = 0
        for _ in range(8): v = (v << 1) | self.bit()
        return v
    def reconst(self):
        freq, prnt, son = self.freq, self.prnt, self.son
        j = 0
        for i in range(T):
            if son[i] >= T:
                freq[j] = (freq[i] + 1) >> 1; son[j] = son[i]; j += 1
        i = 0; j = N_CHAR
        while j < T:
            k = i + 1; f = freq[j] = freq[i] + freq[k]
            k = j - 1
            while f < freq[k]: k -= 1
            k += 1; l = (j - k)
            freq[k + 1:k + 1 + l] = freq[k:k + l]; freq[k] = f
            son[k + 1:k + 1 + l] = son[k:k + l]; son[k] = i
            i += 2; j += 1
        for i in range(T):
            k = son[i]
            if k >= T: prnt[k] = i
            else: prnt[k] = prnt[k + 1] = i
    def update(self, c):
        freq, prnt, son = self.freq, self.prnt, self.son
        if freq[R] == MAX_FREQ: self.reconst()
        c = prnt[c + T]
        while True:
            freq[c] += 1; k = freq[c]
            l = c + 1
            if k > freq[l]:
                while k > freq[l + 1]: l += 1
                freq[c] = freq[l]; freq[l] = k
                i = son[c]; prnt[i] = l
                if i < T: prnt[i + 1] = l
                j = son[l]; son[l] = i
                prnt[j] = c
                if j < T: prnt[j + 1] = c
                son[c] = j
                c = l
            c = prnt[c]
            if c == 0: break
    def char(self):
        c = self.son[R]
        while c < T: c = self.son[c + self.bit()]
        c -= T; self.update(c); return c
    def position(self):
        i = self.byte(); c = self.d_code[i] << 6; j = self.d_len[i] - 2
        for _ in range(j): i = (i << 1) | self.bit()
        return c | (i & 0x3f)

def ring_init():
    b = bytearray()
    for v in range(256): b += bytes([v]) * 13
    b += bytes(range(256)); b += bytes(range(255, -1, -1)); b += bytes(128); b += b'\x20' * 128
    assert len(b) == N
    return b

def decode(data, size, d_code=None, d_len=None):
    d = Dec(data, d_code, d_len); buf = ring_init(); r = N - F; out = bytearray()
    while len(out) < size:
        c = d.char()
        if c < 256:
            out.append(c); buf[r] = c; r = (r + 1) & (N - 1)
        else:
            i = (r - d.position() - 1) & (N - 1); j = c - 255 + THRESHOLD
            for k in range(j):
                v = buf[(i + k) & (N - 1)]; out.append(v); buf[r] = v; r = (r + 1) & (N - 1)
    return bytes(out[:size])

def read_sectors(disk_path, first, n):
    with open(disk_path, 'rb') as f:
        f.seek(first * 512); return f.read(n * 512)

if __name__ == '__main__':
    disk, first, n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    raw = read_sectors(disk, first, n)
    size = struct.unpack('>I', raw[:4])[0]
    dc = dl = None
    if len(sys.argv) > 4:
        sys.path.insert(0, 'tools')
        from gfxview import load_ram
        ram, _ = load_ram(sys.argv[4])
        dc = list(ram[0x11cce:0x11cce + 256]); dl = list(ram[0x11dce:0x11dce + 256])
        print('tables match std:', (dc, dl) == std_tables())
    out = decode(raw[4:], size, dc, dl)
    print('size', size, 'head', out[:16].hex())
