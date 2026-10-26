"""Unpack AUTO/MENU67.PRG's self-extracting stub (ByteKiller-style, from the stub at text $11e).

usage: bk_stub.py <MENU67.PRG> <out.prg>
"""
import struct, sys

def bk_unpack(src):
    p = len(src)
    def rl():
        nonlocal p
        p -= 4
        return struct.unpack('>I', src[p:p+4])[0]
    n = rl(); d0 = rl()
    out = bytearray(n); q = n
    def bit():
        nonlocal d0
        c = d0 & 1; d0 >>= 1
        if d0 == 0:
            w = rl(); c2 = w & 1; d0 = (w >> 1) | (c << 31); c = c2
        return c
    def bits(k):
        v = 0
        for _ in range(k): v = (v << 1) | bit()
        return v
    while q > 0:
        if bit():
            d2 = bits(2)
            if d2 < 2:
                off = bits(9 + d2); cnt = d2 + 3
            elif d2 == 3:
                cnt = bits(8) + 9; off = None
            else:
                cnt = bits(8) + 1; off = bits(12)
        elif bit():
            off = bits(8); cnt = 2
        else:
            cnt = bits(3) + 1; off = None
        for _ in range(cnt):
            q -= 1
            if off is None:
                b = 1
                while b < 0x100: b = (b << 1) | bit()
                out[q] = b & 0xff
            else:
                out[q] = out[q + off]
    assert q == 0, q
    return bytes(out)

if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    tlen = struct.unpack('>I', d[2:6])[0]
    open(sys.argv[2], 'wb').write(bk_unpack(d[28:28 + tlen][:]))
