"""plane2_decode.py - collision plane 2 ($15182) record format, decoded from the routine and proved against the live plane on all 8 tracks.

Record table (INIT.DAT, live at -1154(A4)): byte pair per track [count, start] at -1154+2*track; the 6-byte records start at -1154+16+6*start.
Record = [x16, y, ws, h, cs_lo, cs_hi]:
   x16  16-pixel group column (0..19), y pixel row;  ws = (groups << 4) | edge:  `groups` whole 16-px groups, plus, when edge != 0, one more group
   in which only the leftmost EDGE[edge] bits (mask word table at $152ae: 0, 8000, c000 ... fffe) take part;  h = rows (the loop runs h times).
   cs = colour set (16-bit, bit c set = art colour index c).
Effect: for every (group, row) the record visits, the plane-2 word is first set to $ffff ($15220: a record REPLACES the word it touches, so later records
   overwrite earlier ones) and then the bits of the pixels whose art colour is in cs (and inside the edge mask in the partial group) are cleared.
   Walking past x16 = 19 continues on the next pixel row (the pointer simply advances 8 bytes per group).  Plane 2 is 0 where a car must be drawn behind.
The art read is the tile composition ($152d2) BEFORE the scenery sprites, taken from trackrender (the live art at $beb2 already has scenery).
This script implements the routine from the asm (independent of tracks/occlusion.py) and compares with both the live plane and occlusion.py.
usage: plane2_decode.py [track ...]    (0-based; default all)"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
os.environ['M68000_ROOT'] = ROOT
TK = os.path.join(ROOT, 'reversing', 'supersprint', 'py', 'tracks')
sys.path.insert(0, TK)
os.chdir(TK)
from tkcommon import *
import trackrender as TR, numpy as np, occlusion as OCC
os.chdir(ROOT)
A4_ = sscfg.A4
EDGE_ASM = None

def edge_table(ram):
    return [int.from_bytes(bytes(ram[0x152ae + 2 * i:0x152b0 + 2 * i]), 'big') for i in range(16)] if len(ram) > 0x152d0 else None

def records(ram, track):
    t = A4_ - 1154
    cnt, start = ram[t + 2 * track], ram[t + 2 * track + 1]
    base = t + 16 + 6 * start
    return [tuple(ram[base + 6 * k: base + 6 * k + 6]) for k in range(cnt)]

def decode_plane2(recs, idx, edges):
    plane = np.ones(200 * 320, bool)                 # linear pixel array: row-major, so a group past column 19 wraps to the next row
    flat = idx.reshape(-1)
    for x16, y, ws, h, lo, hi in recs:
        cs = (hi << 8) | lo
        full, edge = ws >> 4, edges[ws & 15]
        passes = [(g, None) for g in range(full)] + ([(full, edge)] if edge else [])
        for g, mask in passes:
            for r in range(h):
                base = (y + r) * 320 + (x16 + g) * 16
                if base + 16 > flat.size: continue
                plane[base:base + 16] = True          # move.w #$ffff,(A2)
                for b in range(16):
                    if (cs >> int(flat[base + b])) & 1 and (mask is None or (mask >> (15 - b)) & 1):
                        plane[base + b] = False
    return plane.reshape(200, 320)

if __name__ == '__main__':
    tracks = list(map(int, sys.argv[1:])) or range(8)
    g = TR.Gfx(); tot = 0
    for t in tracks:
        ram = load_snap(out('snaps', 'race_%d.snap' % t))
        edges = edge_table(ram)
        assert edges == OCC.EDGE, (edges, OCC.EDGE)
        recs = records(ram, t)
        idx = planar_to_idx(g.tiles(t))
        mine = decode_plane2(recs, idx, edges)
        live = np.unpackbits(np.frombuffer(bytes(ram[0x61436 + 16000:0x61436 + 24000]), dtype=np.uint8)).reshape(200, 320).astype(bool)
        ref = OCC.occlusion(g, t, idx)
        eq = int((mine == live).sum()); tot += eq
        print('Track %d: %2d records, cleared px: decode %d live %d; decode vs live %d/64000 equal (differ %d); decode vs occlusion.py %d/64000' %
              (t + 1, len(recs), int((~mine).sum()), int((~live).sum()), eq, 64000 - eq, int((mine == ref).sum())))
        if t == tracks[0] or len(sys.argv) == 2:
            for r in recs[:50]:
                print('   x16=%2d y=%3d  groups=%d edge=%2d (mask %04x) h=%3d  colours %s' % (r[0], r[1], r[2] >> 4, r[2] & 15, edges[r[2] & 15], r[3], [c for c in range(16) if ((r[5] << 8 | r[4]) >> c) & 1]))
    print('total equal %d/%d' % (tot, 64000 * len(list(tracks))))
