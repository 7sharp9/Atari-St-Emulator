"""Chain the gated ports from the base seed alone and compare the whole module block with the emulator's.

    uv run python -I reversing/captive/py/mapgen/full/shafts/shafts.py chain <capture.bin> [...]

For each captured case (D0, D2) the state at $23ca4 (the bsr $245e2) is built from D0 and D2 alone:
  - a constant template: the block at $23ca4 of the first case read, with every seed-dependent byte overwritten below
    (the check that this is enough is the first count printed: built == emulator at $23ca4);
  - zones.plan(D0) (floors, lift offsets, entrance, block walls: module bytes 0..55, the RNG word, G0);
  - D0 at 12406 and 12408, D2 at 12412, the pillar threshold 13660 = $eeff - 8 min(D0, $7f7) ($23bb0),
    the drawn floor count at 12418 and the placed one (46(A6)) at 13274 (both written during $2011e), and 13748 from $2624a.
Then: $245e2 shafts, RNG word restored ($23ca8), $263c2 reservations, the digger $244b6 (dig.py), compared at
$23cb4; then $24d78, $24f4c (flow field, a block-level version of mapgen/flowfield.py's model), $25198, $2533a,
$25198, $25162 (stages/models.py) and $263fa, compared at $23cd0.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.join(os.path.dirname(os.path.dirname(HERE)), 'digger'))  # dig.py
from dig import G0, G1  # noqa: E402
from shafts import Gen  # noqa: E402
import zones  # noqa: E402

R = os.path.dirname(HERE)
while not os.path.exists(os.path.join(R, 'tools', 'rdis.py')):
    R = os.path.dirname(R)
sys.path.insert(0, os.path.join(R, 'reversing', 'captive', 'py', 'mapgen', 'stages'))
import models  # noqa: E402

G2 = 8280
UP = (0x1c, 0x37, 0x06, 0x1a, 0x35, 0x04)
DOWN = (0x1c, 0x37, 0x06, 0x1b, 0x36, 0x05)
NO_NEIGHBOURS = (0x1c, 0x1a, 0x1b)


def W(b, o):
    return (b[o] << 8) | b[o + 1]


def SW(b, o, v):
    b[o], b[o + 1] = (v >> 8) & 0xff, v & 0xff


def s16(b, o):
    v = W(b, o)
    return v - 0x10000 if v & 0x8000 else v


def mode_2624a(d0, d2):  # 13748(A6)
    if d2 == 1:
        return 8
    if d0 <= 9:
        return models.code()[0][0x26240 - models.code()[1] + d0]
    x = (d0 * 0x5e5) & 0xffffffff
    x = (x & 0xffff0000) | ((x + 0x29) & 0xffff)
    x = ((x & 0xffff) * 0x5e5) & 0xffffffff
    x = (x & 0xffff0000) | ((x + 0x29) & 0xffff)
    q = ((x & 0xffff) * 3) >> 16
    return {0: 3, 1: 5}.get(q, 6)


def build(template, d0, d2):
    b = bytearray(template)
    v, x, g0 = zones.plan(d0)
    b[0:56] = v
    SW(b, 12404, x)
    b[G0:G0 + 4096] = g0
    SW(b, 12406, d0)
    SW(b, 12408, d0)
    SW(b, 12412, d2)
    SW(b, 13276, d2 & ~1)
    SW(b, 13660, 0xeeff - 8 * min(d0, 0x7f7))
    SW(b, 12418, zones.LAST_NZ)      # floors drawn
    SW(b, 13274, W(v, 46))           # floors placed
    SW(b, 13748, mode_2624a(d0, d2))
    return b


def flowfield(b):  # $24f4c on the whole block
    g0 = [W(b, G0 + 2 * i) for i in range(2048)]
    for y in range(32):
        for x in range(64):
            i = 64 * y + x
            if g0[i] in (0, 0xffff):
                continue
            best, val = 0x4000, 0xfe
            f = b[G1 + 2 * i + 1]
            k = b[(y >> 3) * 4 + (x >> 4)]
            cands = []
            if f in UP:
                cands.append((x + s16(b, 16 + 2 * (k - 1)), y + s16(b, 24 + 2 * (k - 1)), 4))
            if f in DOWN:
                cands.append((x - s16(b, 16 + 2 * (k - 2)), y - s16(b, 24 + 2 * (k - 2)), 5))
            if f not in NO_NEIGHBOURS:
                cands += [(x, y - 1, 0), (x, y + 1, 2), (x + 1, y, 3), (x - 1, y, 1)]
            for cx, cy, cv in cands:
                if 0 <= cx < 64 and 0 <= cy < 32:
                    c = g0[64 * cy + cx]
                    if c not in (0, 0xffff) and c <= best:
                        best, val = c, cv
            b[G2 + 2 * i] = val
            if f == 0:
                b[G1 + 2 * i + 1] = 7
    ex = W(b, 32)
    b[G1 + 2 * ex] = 0x7e
    SW(b, G2 + 2 * ex, 0)
    for grp in range(5):
        d6, d4 = 4, 26
        for w in range(5):
            o = 13410 + 10 * grp + 2 * w
            if b[o] & 0x80:
                continue
            x, y = b[o], b[o + 1]
            i = 64 * y + x
            if b[G1 + 2 * i + 1] == 0x1d:
                b[G2 + 2 * i] = 3 if x == 0 or g0[i - 1] == 0xffff else 1
                d6, d4 = 5, 27
            else:
                b[G2 + 2 * i] = d6
                SW(b, G1 + 2 * i, d4)


def chain(recs):
    template = recs[0]['st'][0x23ca4][1]
    n = ok_in = ok_dig = ok_end = 0
    miss = []
    for r in recs:
        n += 1
        d0, d2 = r['seed'], r['d2']
        b = build(template, d0, d2)
        if b == r['st'][0x23ca4][1]:
            ok_in += 1
        elif len(miss) < 6:
            miss.append(('in', d2, d0, [i for i in range(len(b)) if b[i] != r['st'][0x23ca4][1][i]][:6]))
        g = Gen(b)
        saved = g.W(12404)
        g.shafts()
        g.SW(12404, saved)
        g.reserve()
        g.run()
        if g.m == r['st'][0x23cb4][1]:
            ok_dig += 1
        elif len(miss) < 6:
            miss.append(('dig', d2, d0, [i for i in range(len(b)) if g.m[i] != r['st'][0x23cb4][1][i]][:6]))
        g.unreserve()
        flowfield(g.m)
        S = models.State(g.m, bytearray(0x1d9e8 - 0x1bd3e))
        for f in (models.s_25198, models.s_2533a, models.s_25198, models.s_25162):
            f(S)
        g.m = S.b.a
        g.pass2()
        if g.m == r['st'][0x23cd0][1]:
            ok_end += 1
        elif len(miss) < 6:
            miss.append(('end', d2, d0, [i for i in range(len(b)) if g.m[i] != r['st'][0x23cd0][1][i]][:6]))
    print(f'built from (D0, D2) == emulator block at $23ca4: {ok_in}/{n}')
    print(f'chain to the digger return $23cb4, whole module block equal: {ok_dig}/{n}')
    print(f'chain to the $263fa return $23cd0, whole module block equal: {ok_end}/{n}')
    for m in miss:
        print('  miss', m)
