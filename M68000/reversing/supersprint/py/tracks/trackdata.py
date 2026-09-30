"""Super Sprint track data, read from the data files only (SUPER.DAT + INIT.DAT), no emulator RAM.

SUPER.DAT is one flat blob that the game `Fread`s to $28e00 and then addresses through sub-array pointers that
`$fbca`/`$14c4a` (see ../notes) compute; every file offset below is (runtime address - $28e00).

    0x00000  -98(A4)   0x0da0  crowd/grandstand frames
    0x00da0  -102(A4)  0x23a0
    0x03140  -106(A4)  0x1c16
    0x04d56  -3602(A4) 0x8000
    0x0cd56  -1196(A4) TILE BLOCK header (5 words: n_tilemaps=11, n0=606, n1=1158, n2=1115, n3=65)
    0x0cd60  -1192(A4) 11 tilemaps x 2000 B (40x25 words; 8 are raced, 3 are other screens)
    0x12350  -1188(A4) tile set 0: n0 x 10 B (1 plane + colour word)
    0x13afc  -1184(A4) tile set 1: n1 x 18 B (2 planes + colour word)
    0x18c68  -1180(A4) tile set 2: n2 x 26 B (3 planes + colour word)
    0x1fda6  -1176(A4) tile set 3: n3 x 32 B (4 raw planes, no colour word)
    0x205d6  -1722(A4) object sprite sheet (16x16 sprites +$70e0, 1bpp shadows +$72e0)
    0x27b06  -8076(A4) track outline polylines + flood-fill seeds (collision mask source)
    0x286be  -4936(A4) 0xbb8
    0x2947e  -110(A4)  0xdc0
    0x29c4e  -118(A4)  0x300c
    0x2cc5a  -122(A4)  0x1e0
    0x2ce3a  -4080(A4) waypoint/racing-line blocks, 8 tracks: [count word][count x 8 B]
    0x2e9f6  -126(A4)  0x1f40 ...
"""
import struct
from tkcommon import *

BASE = 0x28e00
F = dict(tileblk=0xcd56, tilemaps=0xcd60, set0=0x12350, set1=0x13afc, set2=0x18c68, set3=0x1fda6,
         sprites=0x205d6, poly=0x27b06, wp=0x2ce3a)
WP_OFFS = [0, 0x2a2, 0x554, 0x826, 0xc78, 0xfaa, 0x13fc, 0x17ce]      # -8510(A4) (from INIT.DAT via $11b24)
NTRACKS = 8

_sup = None
def sup():
    global _sup
    if _sup is None: _sup = datfile('SUPER.DAT')
    return _sup

def w16(b, o): return (b[o] << 8) | b[o+1]

def waypoints(t):
    """Track t (0-based) racing-line block: list of (x, y, len, hd) 8-byte records in table order."""
    d = sup(); o = F['wp'] + WP_OFFS[t]; n = w16(d, o)
    return [struct.unpack('>4H', d[o+2+8*i:o+10+8*i]) for i in range(n)]

def tile_header():
    d = sup(); return struct.unpack('>5H', d[F['tileblk']:F['tileblk']+10])

def tilemap(i):
    d = sup(); o = F['tilemaps'] + 2000 * i
    return struct.unpack('>1000H', d[o:o+2000])

def poly_table():
    """-8076(A4): word index table by track then per-track polyline lists (see $14cd4)."""
    d = sup(); return d[F['poly']:F['poly']+0xbb8]


def outline(track):
    """Track outline from -8076(A4) (see $14cd4): list of polylines [(x,y),...] (pen lifts at (ffff,ffff) pairs)
    plus the flood-fill seed points."""
    t = poly_table(); w = struct.unpack('>%dH' % (len(t) // 2), t)
    i = w[track]; n = w[i]; i += 1
    lines = []; cur = []
    for k in range(n):
        x, y = w[i], w[i + 1]; i += 2
        if x == 0xffff:
            if cur: lines.append(cur)
            cur = []
        else: cur.append((x, y))
    if cur: lines.append(cur)
    ns = w[i]; i += 1
    seeds = [(w[i + 2 * k], w[i + 2 * k + 1]) for k in range(ns)]
    return lines, seeds
