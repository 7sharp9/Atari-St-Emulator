"""Replicates the $13506 icon hit-test (edge lists $12e6a/$12ee4) over the screen: icon id -> pixel centroid."""
import sys, struct
R = open(sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/pm121/run/k60_s2.ram', 'rb').read()
sw = lambda a: struct.unpack('>h', R[a:a+2])[0]
def edges(a):
    out = []
    while True:
        e = [sw(a + 2*i) for i in range(4)]; a += 8
        if e[0] == 0: out.append(e); return out
        out.append(e)
C, Rw = edges(0x12e6a), edges(0x12ee4)
def icon(x, y):
    d6 = 0
    for d2, d3, d4, d5 in C:           # $1350e: advance while the point is right of the edge
        if d2 == 0: break
        if y - d3 < (x - d2) * (d5 - d3) // (d4 - d2) if False else None: pass
        v = int((x - d2) * (d5 - d3) / (d4 - d2)) if d4 != d2 else 0
        # muls D5,D0 ; divs D4,D0 with D0=x-d2, D4=d4-d2, D5=d5-d3 ; loop while (y-d3) < v
        d6 += 1
        if not (y - d3 < v): break
    for d2, d3, d4, d5 in Rw:
        if d2 == 0: break
        v = int((x - d2) * (d5 - d3) / (d4 - d2)) if d4 != d2 else 0
        d6 += 16
        if not (y - d3 > v): break
    return d6
ids = []; a = 0x19bde
while sw(a) >= 0: ids.append(sw(a)); a += 2
acc = {}
for y in range(200):
    for x in range(320):
        i = icon(x, y)
        if i in ids:
            s = acc.setdefault(i, [0, 0, 0]); s[0] += x; s[1] += y; s[2] += 1
print("columns", C); print("rows", Rw)
for slot, i in enumerate(ids):
    if i and i in acc:
        sx, sy, n = acc[i]; print(f"slot D1={2*slot:#04x} icon {i:#04x} centre ({sx//n},{sy//n}) px={n}")
