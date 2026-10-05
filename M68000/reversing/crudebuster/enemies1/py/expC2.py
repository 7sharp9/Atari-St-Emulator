"""Experiment C2: type 15 (level 1 final boss) and type 10 with hits, in the lab (scroll counter 0x800 / 0x500).  Output out/expC2/<name>/enemylog.txt; view with bosslog.py."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from labrun import run_plans
base = dict(pin=(0x887, 0x1c0), scroll=(0x800, 0x100))
run_plans("expC2", [("15_0_n", dict(base, stop=2400, events=[(5, "spawn", 15, 0, 0x940, 0x1c0)])),
    ("15_0_h", dict(base, stop=4500, events=[(5, "spawn", 15, 0, 0x940, 0x1c0)] + [(150 + 45*k, "hit", 0, 0x80) for k in range(90)]))], parallel=2)
