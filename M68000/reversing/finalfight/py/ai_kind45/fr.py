"""fr.py: reader for drv.lua traces (.bin or .bin.gz). frames(path) yields (frame, bytes of $ff8000..$ffbfff); record bases: players $ff8568, pool 2 $ff86e8, pool 6 $ff90a8, pool 4 $ff9528, pool 8 $ff9b28, props (tag $a) $ffb2e8."""
import sys, struct, gzip
SZ = 4 + 0x4000
BASE = 0xff8000
def frames(path):
    d = (gzip.open(path, 'rb') if path.endswith('.gz') else open(path, 'rb')).read()
    for o in range(0, len(d) - SZ + 1, SZ):
        yield struct.unpack('>I', d[o:o + 4])[0], d[o + 4:o + SZ]
def b(buf, a): return buf[a - BASE]
def w(buf, a): o = a - BASE; return (buf[o] << 8) | buf[o + 1]
def sw(buf, a):
    v = w(buf, a); return v - 65536 if v & 0x8000 else v
def l(buf, a): o = a - BASE; return int.from_bytes(buf[o:o + 4], 'big')
POOL2 = 0xff86e8
def rec2(i): return POOL2 + 0xc0 * i
def rec_by_p92(buf, p92):
    for i in range(13):
        if (l(buf, rec2(i) + 92) & 0xffffff) == p92: return rec2(i)
    return None
