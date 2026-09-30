"""'JEK PACKER V1.2' (EMOTION+.PRG stub $182-$25a; an Atomik-style packer): depacker transcribed from the stub disassembly.
Layout at the end of the program text: ... packed stream (read backwards as 32-bit words), D0 = last word, D5 = check word, u32 unpacked length, then the
relocation table (4 bytes here).  Bits are taken LSB first from big-endian longwords fetched from the END of the stream downwards; a sentinel is shifted in
when the word runs out (move #$10,CCR; roxr.l #1,D0).  Output is written backwards from the end of the unpacked image."""
import struct
def depack(prg):
    tlen = struct.unpack('>I', prg[2:6])[0]
    end = 0x1c + tlen                     # A0 = 16(A5) = end of the text segment
    pos = end
    def rl():
        nonlocal pos
        pos -= 4
        return struct.unpack('>I', prg[pos:pos+4])[0]
    U = rl(); D5 = rl(); D0 = rl(); D5 ^= D0
    out = bytearray(U); a2 = U
    st = {'d0': D0, 'd5': D5}
    def bit():
        d0 = st['d0']; c = d0 & 1; d0 >>= 1
        if d0 == 0:
            w = rl(); st['d5'] ^= w
            c = w & 1; d0 = (w >> 1) | 0x80000000     # roxr with X = 1
        st['d0'] = d0
        return c
    def bits(n):                                  # $242: n bits, first bit read is the MSB of the result
        v = 0
        for _ in range(n): v = (v << 1) | bit()
        return v
    while a2 > 0:
        if not bit():                             # literal run
            d1 = 8; d3 = 1
            if not bit():
                d1 = 3; d4 = 0
                d2 = bits(d1); d3 = d2 + d4
            else:
                # $220 path with D1 = 8 offset? (second bit set -> $220: bsr $242 with D1 = 8 gives D2 = 8 bits, D3 = 1: 2-byte match)
                d2 = bits(8); a2 -= 1
                for _ in range(2):
                    out[a2] = out[a2 + d2] if a2 + d2 < U else 0; a2 -= 1
                a2 += 1
                continue
            for _ in range(d3 + 1):
                a2 -= 1; out[a2] = bits(8)
        else:
            d2 = bits(2)
            if d2 < 2:
                d1 = 9 + d2; d3 = d2 + 2 + 0
                d3 = (d2 + 2)
            elif d2 == 3:
                d1 = 8; d4 = 8                     # $1ee: long literal run: count = 8 bits + 8
                d2b = bits(8); d3 = d2b + 8
                for _ in range(d3 + 1):
                    a2 -= 1; out[a2] = bits(8)
                continue
            else:
                d2 = bits(8); d3 = d2; d1 = 12
            off = bits(d1)
            for _ in range(d3 + 1):
                a2 -= 1; out[a2] = out[a2 + off] if a2 + off < U else 0
    return bytes(out), st['d5'], pos
if __name__ == '__main__':
    import sys
    d = open(sys.argv[1], 'rb').read()
    o, chk, pos = depack(d)
    print('unpacked', len(o), 'check word left in D5:', hex(chk), 'stream pos', pos)
    open(sys.argv[2], 'wb').write(o)
