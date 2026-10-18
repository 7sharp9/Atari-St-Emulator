"""Port of the game's depacker at $49e4 (Pack-Ice style, packed data read backwards)."""
import struct
def depack(data):
    pos = len(data)
    def rl():
        nonlocal pos
        pos -= 4
        return struct.unpack_from(">I", data, pos)[0]
    orig = rl()
    out = bytearray(orig)
    a2 = orig                  # write pointer, decrements
    d5 = rl()
    d0 = rl(); d5 ^= d0
    def bit():
        nonlocal d0, d5
        c = d0 & 1; d0 >>= 1
        if d0 == 0:
            d0 = rl(); d5 ^= d0
            c = d0 & 1; d0 = (d0 >> 1) | 0x80000000
        return c
    def bits(n):
        v = 0
        for _ in range(n): v = (v << 1) | bit()
        return v
    def copy(n, off):          # n bytes, source a2+off after decrement each
        nonlocal a2
        for _ in range(n):
            a2 -= 1
            out[a2] = out[a2 + off]
    while a2 > 0:
        if bit():              # carry: match forms
            d2 = bits(2)
            if d2 < 2:
                nbits = 9 + d2; n = d2 + 3
                copy(n, bits(nbits))
            elif d2 == 3:      # long literal run
                n = bits(8) + 8 + 1
                for _ in range(n):
                    a2 -= 1; out[a2] = bits(8)
            else:
                n = bits(8) + 1
                copy(n, bits(12))
        else:
            if bit():          # short match, 2 bytes, 8-bit offset
                copy(2, bits(8))
            else:
                n = bits(3) + 1
                for _ in range(n):
                    a2 -= 1; out[a2] = bits(8)
    return bytes(out), (d5 == 0)
