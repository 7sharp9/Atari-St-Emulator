"""rebuild_surface.py - rebuild the 40x25 byte surface ('event') map at [-1910(A4)] from the track's segment list ($15550) and diff it with RAM.
$15550(track): clear 1000 bytes; records i in [ -1172(A4)[track], -1172(A4)[track+1] ) at -3598(A4)+4*i are (x, y, len, value):
   cell = y*40 + x; len >= 0: `len` cells going DOWN (stride 40); len bit7 set: (len & 0x7f) cells going RIGHT; each cell |= value.
usage: rebuild_surface.py [snap] [track]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pl import *
import numpy as np


def build(r, track):
    sm = bytearray(1000)
    i0 = r.u16(A4 - 1172 + 2 * track)
    i1 = r.u16(A4 - 1172 + 2 * track + 2)
    recs = []
    for i in range(i0, i1):
        a = A4 - 3598 + 4 * i
        x, y, ln, val = r.u8(a), r.u8(a + 1), r.u8(a + 2), r.u8(a + 3)
        recs.append((x, y, ln, val))
        cell = y * 40 + x
        if ln & 0x80:
            n = ln & 0x7f
            for k in range(n):
                sm[cell + k] |= val
        else:
            for k in range(ln):
                sm[cell + 40 * k] |= val
    return bytes(sm), recs


if __name__ == '__main__':
    snap = sys.argv[1] if len(sys.argv) > 1 else sscfg.SNAP_RACE
    track = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    r = Ram(snap)
    sm, recs = build(r, track)
    ref = r.bytes(r.gl(-1910), 1000)
    eq = sum(1 for a, b in zip(sm, ref) if a == b)
    print('records:', len(recs), recs)
    print('surface map rebuilt vs RAM: %d/1000 cells equal' % eq)
    print('-1172 table', [r.u16(A4 - 1172 + 2 * i) for i in range(10)])
