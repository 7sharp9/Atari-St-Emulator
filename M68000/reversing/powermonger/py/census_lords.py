"""pm129: per foreign lord, live entities by owner side near the lord's cell and along the straight corridor
from a start cell. Usage: census_lords.py <ram> <start_x> <start_y> [radius]"""
import struct, sys
from collections import Counter
R = open(sys.argv[1], 'rb').read()
sx, sy = int(sys.argv[2]), int(sys.argv[3]); rad = int(sys.argv[4]) if len(sys.argv) > 4 else 4
w = lambda a: struct.unpack('>H', R[a:a+2])[0]
sw = lambda a: struct.unpack('>h', R[a:a+2])[0]
loc = w(0x57ffe)
ents = []
for i in range(1, 511):
    a = 0x51b66 + 50*i
    o = struct.unpack('>b', R[a+5:a+6])[0]
    if o == 0: continue
    ents.append((i, o, sw(a+8) >> 8, sw(a+10) >> 8, R[a+6], R[a+31]))
print("total live entities", len(ents), dict(Counter(e[1] for e in ents)))
def near(cx, cy, r):
    return [e for e in ents if abs(e[2]-cx) <= r and abs(e[3]-cy) <= r]
for i in range(64):
    b = 0x4e514 + 32*i
    if R[b] == 0 and w(b+4) == 0: continue
    if R[b] == loc: continue
    c = w(b+4); lx, ly = c & 63, (c >> 6) & 127
    n = near(lx, ly, rad)
    hostile = [e for e in n if e[1] != loc]
    d = max(abs(lx-sx), abs(ly-sy))
    # corridor: waypoints every 3 cells on the straight line, r=3, hostile (non-own) entities
    steps = max(1, d // 3); cor = set()
    for k in range(steps+1):
        px = sx + (lx-sx)*k//steps; py = sy + (ly-sy)*k//steps
        for e in near(px, py, 3):
            if e[1] != loc: cor.add(e[0])
    print(f"lord {i:2d} side {R[b]} cell ({lx:2d},{ly:3d}) cheb-dist {d:3d} | r{rad} around lord: {dict(Counter(e[1] for e in n))} "
          f"| corridor(r3 waypoints) non-own: {len(cor)} bysides {dict(Counter(e[1] for e in ents if e[0] in cor))}")
