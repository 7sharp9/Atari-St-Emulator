"""Experiment B: hit reactions.  One enemy at a time (spawned 90 px right of the pinned, invulnerable P1); the hit flag value V is OR-ed into +6 at fixed frames
(what $f82e writes when a player's attack box overlaps: $80 | strength-table[+25] = $80,$81,$82,$84; P2 adds $40; a thrown object adds $88).
6 cycles of 300 frames per (type,var,V): kill + spawn at the cycle start, hits at +60,+110,+160,+210,+260.  Output out/expB/<t>_<v>_<V>/.
usage: expB.py [type:var ...]"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from labrun import run_plans
TV = [(0,0),(1,1),(2,2),(3,0),(4,0),(4,1),(5,0),(5,1),(6,0),(6,1),(7,0),(8,0),(20,0),(20,1),(21,1)]
if len(sys.argv) > 1: TV = [tuple(int(x) for x in a.split(":")) for a in sys.argv[1:]]
PX, PY = 0x187, 0x1c0
plans = []
for t, v in TV:
    for V in (0x80, 0x81, 0x82, 0x84, 0x88):
        ev = []
        for c in range(6):
            c0 = 5 + c * 300
            for s in range(4): ev.append((c0, "kill", s))
            ev.append((c0 + 1, "spawn", t, v, PX + 90, PY))
            for k in range(5): ev.append((c0 + 60 + 50 * k, "hit", 0, V))
        plans.append(("%d_%d_%02x" % (t, v, V), dict(stop=1820, pin=(PX, PY), events=ev)))
run_plans("expB", plans, parallel=6)
