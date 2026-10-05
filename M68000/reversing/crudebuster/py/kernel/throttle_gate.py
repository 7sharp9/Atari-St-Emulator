"""Gate: list A (enemy script) spawns only while fewer than 5 pool A records were active at the end of the previous frame.
The dispatcher $10254 counts active pool A records in $81e02 and sets $81e03 bit 7 when the count is 5 or more; $f3b4 skips the spawn then.
Input: spawnlog.txt from lua/spawnlog.lua (E lines carry $81e02/$81e03).  usage: throttle_gate.py <spawnlog.txt>
"""
import sys
ev = [l.split() for l in open(sys.argv[1])]
E = {int(p[1]): int(p[2], 16) for p in ev if p[0] == "E"}
fr = sorted(E)
import bisect
def e_at(f):
    i = bisect.bisect_right(fr, f) - 1
    return E[fr[i]] if i >= 0 else 0
ok = bad = 0
for p in ev:
    if p[0] == "S" and int(p[2][5:]) < 16:
        e = e_at(int(p[1]) - 1)
        if (e >> 8) < 5 and not (e & 0x80): ok += 1
        else: bad += 1; print("violation frame", p[1], hex(e))
print("list A spawns with count < 5 and block flag clear at the previous frame end: %d, violations: %d; max count seen %d" % (ok, bad, max(v >> 8 for v in E.values())))
print("block flag set in %d of %d frames with count >= 5" % (sum(1 for v in E.values() if (v >> 8) >= 5 and v & 0x80), sum(1 for v in E.values() if (v >> 8) >= 5)))
