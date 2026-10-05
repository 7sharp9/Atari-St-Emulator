"""replay_check.py <demo framelog.csv> <demo first replay frame> <streamplay csv> <real first replay frame> [n]
Compares per-frame (P1x,P1y,P2x,P2y) of the attract-mode demo (framelog columns 15-18) with a fresh game fed the decoded streams."""
import sys
H = lambda s: int(s, 16)
demo = {int(r[0]): r for r in (l.strip().split(",") for l in open(sys.argv[1]))}
real = {int(r[0]): r for r in (l.strip().split(",") for l in open(sys.argv[3]))}
d0, r0 = int(sys.argv[2]), int(sys.argv[4]); n = int(sys.argv[5]) if len(sys.argv) > 5 else 633
ok = 0; first_bad = None
for i in range(n):
    a = tuple(H(demo[d0+i][c]) for c in (15, 16, 17, 18))
    b = tuple(H(real[r0+i][c]) for c in (1, 2, 3, 4))
    if a == b: ok += 1
    elif first_bad is None: first_bad = (i, a, b)
print("frames equal %d/%d; first difference: %s" % (ok, n, first_bad))
# longest equal prefix
pre = 0
for i in range(n):
    a = tuple(H(demo[d0+i][c]) for c in (15, 16, 17, 18)); b = tuple(H(real[r0+i][c]) for c in (1, 2, 3, 4))
    if a != b: break
    pre += 1
print("equal prefix %d frames" % pre)
