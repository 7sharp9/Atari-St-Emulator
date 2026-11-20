"""Gate: the tile filler $26b78 against the real tile calls of a frame.  The register sets (D0..D7 = four (x,y) pairs, A0 = colour
index) come from tile_capture.py's `bp 26b78` log.  Each is replayed through stserver on a zeroed back buffer ($27062 -> $78a00) and the
drawn pixels are compared with the polygon v0,v1,v3,v2 (the perimeter order the filler rotates through): pixels >= 1.5 px inside
must carry the tile's colour, pixels >= 1.5 px outside must stay 0.  `control` uses the bow-tie order v0,v1,v2,v3 (must fail).
Also counts the slope-table lookups the frame makes (edges with dx in -64..63 and dy 0..63).
Usage: tile_gate.py <bp_log.txt> <snap> [control]"""
import math, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from stclient import StServer
calls = []; cur = {}
for l in open(sys.argv[1]).read().split('\n'):
    for k, v in re.findall(r'([DA]\d):([0-9a-f]{8})', l): cur[k] = int(v, 16)
    if l.startswith('PC: 00026b78'): calls.append(dict(cur))
CONTROL = len(sys.argv) > 3 and sys.argv[3] == 'control'
s = StServer(ROOT); s('load', snapshot=sys.argv[2]); BUF = 0x78a00
s('poke', addr=0x27062, width=4, value=BUF)
def pixels():
    raw = s.read(BUF, 160 * 184); out = {}
    for y in range(184):
        for x in range(320):
            o = y * 160 + (x >> 4) * 8; bit = 15 - (x & 15); v = 0
            for p in range(4): v |= ((((raw[o + 2 * p] << 8) | raw[o + 2 * p + 1]) >> bit) & 1) << p
            if v: out[(x, y)] = v
    return out
def sd(px, py, a, b):
    ax, ay = a; bx, by = b; dx, dy = bx - ax, by - ay
    t = 0 if dx == dy == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))
def inside(px, py, poly):
    c = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        if (y1 > py) != (y2 > py) and px < (x2 - x1) * (py - y1) / (y2 - y1) + x1: c = not c
    return c
s16 = lambda v: (v & 0xffff) - 0x10000 if v & 0x8000 else v & 0xffff
n = ii = iN = oo = oN = bad = edges = edges_in = 0
for c in calls:
    v = [(s16(c['D%d' % (2 * i)]), s16(c['D%d' % (2 * i + 1)])) for i in range(4)]
    if not all(0 <= x < 320 and 0 <= y < 184 for x, y in v): continue
    for off in range(0, 160 * 184, 4): s('poke', addr=BUF + off, width=4, value=0)
    s.call(0x26b78, max_steps=2000000, **{**{f'd{i}': c[f'D{i}'] for i in range(8)}, 'a0': c['A0']})
    px = pixels(); col = c['A0'] & 0xffff; allowed = {col} if col < 16 else {col - 16, col - 8}
    poly = [v[0], v[1], v[2], v[3]] if CONTROL else [v[0], v[1], v[3], v[2]]
    per = [v[0], v[1], v[3], v[2]]; k = min(range(4), key=lambda i: per[i][1]); per = per[k:] + per[:k]
    for (x2, y2), (x1, y1) in [(per[1], per[0]), (per[3], per[0]), (per[2], per[1]), (per[2], per[3])]:
        if y2 != y1:
            edges += 1; edges_in += -64 <= x2 - x1 <= 63 and abs(y2 - y1) <= 63
    xs = [x for x, y in v]; ys = [y for x, y in v]; a = b = c2 = d = 0
    for y in range(max(0, min(ys) - 3), min(184, max(ys) + 4)):
        for x in range(max(0, min(xs) - 3), min(320, max(xs) + 4)):
            if min(sd(x, y, poly[i], poly[(i + 1) % 4]) for i in range(4)) < 1.5: continue
            p = px.get((x, y), 0)
            if inside(x, y, poly): a += 1; b += p in allowed
            else: c2 += 1; d += p == 0
    n += 1; ii += b; iN += a; oo += d; oN += c2; bad += (b != a or d != c2)
print('tile calls replayed%s: %d' % (' (control: bow-tie vertex order)' if CONTROL else '', n))
print('pixels >= 1.5 px inside the quad with the tile colour: %d/%d' % (ii, iN))
print('pixels >= 1.5 px outside the quad left 0: %d/%d' % (oo, oN))
print('tiles with any miss: %d' % bad)
if not CONTROL: print('slope-table edge lookups inside the modelled range (dx -64..63, dy <= 63): %d/%d' % (edges_in, edges))
s.close()
