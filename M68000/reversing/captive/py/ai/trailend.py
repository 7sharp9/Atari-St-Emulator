"""Where the trail leads: follow plane-2 bits 3-5 (the direction creatures read, ai.md "The trail") from every open
non-wall cell (tile & $7f nonzero, as field.py) until the walk reaches the party's cell, a lift value (4-7), a wall
(tile 0) or the map edge, or loops.
Usage: trailend.py <snap> [<snap> ...]   (relative paths are tried under scratchpad/captive/, then the repo root)
Bytes whose bits 3-5 differ from bits 0-2 are listed for open cells only, tile > $1a: tile 0 and the decorated rock
faces (feature $2c, tile = side mask $01-$0f, e.g. $02, $04, $08) carry a plane-2 byte the encoder writes unshifted
(mapgen.md "Output encoding"), bits 3-5 = 0; their count is printed as "rock". Prints, per snapshot, the party cell,
those open-cell differences (the party's footprints), and the walk ends. The walk stops at the party's cell, so the party's own byte, which still holds an
older value, does not make a cycle with the footprint beside it."""
import os, sys, collections, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cap import A6, snappath  # noqa: E402  (also puts tools/ on sys.path)
from gfxview import load_ram  # noqa: E402

D = {0: (0, -1), 1: (-1, 0), 2: (0, 1), 3: (1, 0)}
for snap in sys.argv[1:]:
    ram, base = load_ram(snappath(snap))
    rd = lambda o, n: ram[A6 + o - base:][:n]
    g = rd(9242, 2048); p = rd(11322, 2048)
    px, py = struct.unpack('>hh', rd(26, 4))
    is_open = lambda i: (g[i] & 0x7f) > 0x1a
    marks = [(i % 64, i // 64, (p[i] >> 3) & 7, p[i] & 7) for i in range(2048) if is_open(i) and (p[i] & 7) != ((p[i] >> 3) & 7)]
    rock = sum(1 for i in range(2048) if not is_open(i) and (p[i] & 7) != ((p[i] >> 3) & 7))
    ends = collections.Counter()
    for y in range(32):
        for x in range(64):
            if g[y * 64 + x] & 0x7f == 0: continue
            cx, cy, seen = x, y, set()
            while True:
                if (cx, cy) == (px, py): ends['party'] += 1; break
                if (cx, cy) in seen: ends['loop'] += 1; break
                seen.add((cx, cy))
                d = (p[cy * 64 + cx] >> 3) & 7
                if d > 3: ends[('lift', cx, cy, d)] += 1; break
                nx, ny = cx + D[d][0], cy + D[d][1]
                if not (0 <= nx < 64 and 0 <= ny < 32) or g[ny * 64 + nx] & 0x7f == 0: ends[('wall/edge', cx, cy)] += 1; break
                cx, cy = nx, ny
    print(os.path.basename(snap), 'party', (px, py), 'non-wall cells', sum(1 for b in g if b & 0x7f),
          'open with bits 3-5 != bits 0-2 (x, y, bits 3-5, bits 0-2):', len(marks), marks, '; rock:', rock)
    lifts = collections.Counter({k: v for k, v in ends.items() if isinstance(k, tuple) and k[0] == 'lift'})
    walls = sum(v for k, v in ends.items() if isinstance(k, tuple) and k[0] == 'wall/edge')
    print('  ends: party', ends['party'], 'loop', ends['loop'], 'wall/edge', walls, 'lifts', dict(lifts))
