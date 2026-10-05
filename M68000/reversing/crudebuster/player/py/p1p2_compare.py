"""p1p2_compare.py <reclog> : compare P1's and P2's per-frame state sequences for the same inputs (reclog regions 0 = $80100, 1 = $80180).
   Each sequence starts at the first frame the sub-action byte (+5) is non-zero after the given press frame; compared fields exclude +25 (random jab variant)
   and +1 bit 2. Fields: +1&fb +3 +4 +5 +6 +15 +16 +24 +27 +28 +29."""
import sys
rows = {}
for ln in open(sys.argv[1]):
    p = ln.split(); rows[int(p[0])] = (bytes.fromhex(p[1]), bytes.fromhex(p[2]))
def seq(rec, t0, n):
    f = t0
    while rows[f][rec][5] == 0: f += 1
    return f, [tuple((rows[f + i][rec][k] & (0xfb if k == 1 else 0xff)) for k in (1, 3, 4, 5, 6, 15, 16, 24, 27, 28, 29)) for i in range(n)]
tests = [("jab chain x3 (b1 taps 7 apart)", 1300, 1420, 44), ("jump neutral", 1540, 1640, 36), ("jump forward", 1740, 1840, 36), ("grab, empty hands", 1940, 2040, 20)]
tot = ok = 0
for name, a, b, n in tests:
    fa, s1 = seq(0, a, n); fb, s2 = seq(1, b, n)
    same = sum(1 for x, y in zip(s1, s2) if x == y); tot += n; ok += same
    print("%-32s P1 from %d, P2 from %d: %d of %d frames identical" % (name, fa, fb, same, n))
print("total %d of %d" % (ok, tot))
