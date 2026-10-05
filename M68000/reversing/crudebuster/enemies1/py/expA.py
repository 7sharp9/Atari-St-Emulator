"""Experiment A: one enemy of a given (type, variant) spawned at several offsets from the pinned, invulnerable P1 (x=$187, y=$1c0); 1500 frames each.
Writes out/expA/<type>_<var>_<tag>/enemylog.txt.  usage: expA.py [type:var ...]"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from labrun import run_plans
TV = [(0,0),(1,1),(2,2),(3,0),(4,0),(4,1),(5,0),(5,1),(6,0),(6,1),(7,0),(8,0),(20,0),(20,1),(21,1)]
if len(sys.argv) > 1: TV = [tuple(int(x) for x in a.split(":")) for a in sys.argv[1:]]
PX, PY = 0x187, 0x1c0
plans = []
for t, v in TV:
    for tag, dx, y in (("r90", 90, PY), ("l90", -90, PY), ("r50", 50, PY), ("r90u", 90, 0x190)):
        plans.append(("%d_%d_%s" % (t, v, tag), dict(stop=1500, pin=(PX, PY), events=[(5, "spawn", t, v, PX + dx, y)])))
run_plans("expA", plans, parallel=6)
