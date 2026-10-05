"""Experiment C: bosses and big types in the lab.  Each (type,var) is spawned at its script position (list A entry) with the scroll counter set to its trigger
so that its own 'wait for the camera' test passes; P1 pinned 0x87 px into the screen.  Mode 'n' = no hits (attack patterns, 2400 frames), mode 'h' = a light hit
poke (+6 |= $80) every 45 frames from frame 120 (phases and death, 4000 frames).  Output out/expC/<t>_<v>_<mode>/.
usage: expC.py [type:var ...]"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from labrun import run_plans
# type, var, x, y, scroll_x
CFG = [(9,0,0x620,0x1c0,0x500),(10,0,0x620,0x1c0,0x500),(11,0,0x620,0x1c0,0x500),(14,0,0x8dc,0x140,0x7d7),(15,0,0x920,0x1c0,0x7e0),
       (28,0,0x700,0x80,0x700),(28,1,0x800,0x80,0x800),(32,0,0x620,0x1c0,0x500),(21,1,0x7a0,0x1c0,0x680),(23,2,0xb40,0x160,0xa00)]
if len(sys.argv) > 1:
    want = [tuple(int(x) for x in a.split(":")) for a in sys.argv[1:]]
    CFG = [c for c in CFG if (c[0], c[1]) in want]
plans = []
for t, v, x, y, sx in CFG:
    px = sx + 0x87
    base = dict(pin=(px, 0x1c0), scroll=(sx, 0x100))
    plans.append(("%d_%d_n" % (t, v), dict(base, stop=2400, events=[(5, "spawn", t, v, x, y)])))
    ev = [(5, "spawn", t, v, x, y)] + [(120 + 45 * k, "hit", 0, 0x80) for k in range(80)]
    plans.append(("%d_%d_h" % (t, v), dict(base, stop=4000, events=ev)))
run_plans("expC", plans, parallel=6)
