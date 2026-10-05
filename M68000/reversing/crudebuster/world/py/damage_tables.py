"""damage_tables.py: pool C hit damage from $fc34: energy -= 4 * table[(DSW $80054 & $c) / 4][C type]; table pointers at $fcba. Compares with the harness (out/f/force_pv0_C.txt)."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from cbrom import *
HERE = os.path.dirname(os.path.abspath(__file__))
ptr = [L(0xfcba + 4*i) for i in range(4)]
print("difficulty tables at", [hex(p) for p in ptr], "(index = (DSW $80054 & $c) >> 2: pointer order as listed)")
tabs = [[B(p + t) for t in range(44)] for p in ptr]
for i, t in enumerate(tabs): print("idx %d:" % i, " ".join("%d" % (4*x) for x in t))
print("hurt-reaction byte (player +23) per C type at $fdba:", " ".join("%d" % B(0xfdba + t) for t in range(44)))
# harness
dmg = {}; cur = None
for l in open(os.path.join(HERE, "..", "out", "f", "force_pv0_C.txt")):
    l = l.rstrip()
    if l.startswith("CASE"): cur = int(l.split()[2]); dmg[cur] = []
    elif cur is not None and l.startswith("P "): dmg[cur].append(int(l.split()[3], 16))
h = [0x38 - min(dmg[t]) if dmg[t] else 0 for t in range(44)]
# first hit only: harness C22 is a 2-hit case; compare first drop
first = []
for t in range(44):
    v = dmg[t]; first.append(0x38 - v[0] if v and v[0] < 0x38 else (0x38 - min(v) if v else 0))
hit = [t for t in range(44) if h[t] > 0]
for i in range(4):
    per_hit = lambda t: h[t] // (2 if t == 22 else 1)   # C22 hit twice in the 60-frame record (2 x 16)
    ok = sum(1 for t in hit if per_hit(t) == 4 * tabs[i][t])
    print("types that damaged P1 in the harness: %d (%s); equal to 4 x table idx %d: %d of %d" % (len(hit), hit, i, ok, len(hit)))
