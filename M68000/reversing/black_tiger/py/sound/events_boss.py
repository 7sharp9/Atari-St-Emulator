"""Sound requests during the boss fight of each level.
LABELLED POKE: the hero is moved onto the level-exit object (kind $20, $cfa4) with
`w 1f014 <x><y>` (hero x and y words), then joystick-1 fire is held (`kbd ff 80`) for N steps
with `watch 17848 4`; the exit loads the boss bank and spawns the boss at $1f020.
Output: $BT_WORK/agents/sound/events_boss.tsv and per-level lines on stdout.
"""
import argparse
import os

from btsnd_common import BT_WORK, OUT
from btsnd_common import Snap
from events_drive import drive, items, snap_path

ap = argparse.ArgumentParser()
ap.add_argument("--levels", default="0,1,2,3,4,5,6,7")
ap.add_argument("--steps", type=int, default=3000000)
a = ap.parse_args()
rows = []
for lv in [int(x) for x in a.levels.split(",")]:
    sp = snap_path(lv)
    s = Snap(sp)
    x, y = items(s)[0x20]
    c = drive(sp, ["w 1f014 %04x%04x" % (x, y), "kbd ff 80"], a.steps, "boss_l%d" % lv)
    rows.append((lv, x, y, c))
    print("level %d exit (%d,%d): %s" % (lv, x, y, ", ".join("$%06x->id%d x%d" % (pc, v, n) for (pc, v), n in sorted(c.items())) or "no request"))
with open(os.path.join(OUT, "events_boss.tsv"), "w") as f:
    f.write("level\texit_x\texit_y\twriter_pc\tid\tcount\n")
    for lv, x, y, c in rows:
        for (pc, v), n in sorted(c.items()):
            f.write("%d\t%d\t%d\t%06x\t%d\t%d\n" % (lv, x, y, pc, v, n))
