"""mk_boss_snaps.py - boss snapshots per level.  LABELLED POKES (MERGE.md correction 9):
 phase 1: hero record ($1f014 x, $1f016 y) moved onto the level-exit object (kind $20, cell from the map);
          900,000 steps run: $cfa4 loads the boss bank over BTSPR and spawns the boss at marker $3d.
 phase 2: hero record moved 70 px left of the boss's resting position (read from its record), then
          N snapshots at page-flip entries ($aad8) every STEP steps.
Level index 0 starts from play_start.snap, index k from agents/systems/lvl<k>.snap (built-in level skip).
Outputs $OUT/boss/B<k>_<i>.snap (+ phase 1 snapshot B<k>_p1.snap)."""
import sys
from concurrent.futures import ThreadPoolExecutor
from drive import *
from bt_common import load_snap, w16

EXIT = {0: (1856, 304), 1: (928, 224), 2: (768, 192), 3: (880, 208), 4: (1184, 256), 5: (1680, 256),
        6: (1648, 240), 7: (1728, 368)}
BOSSDIR = os.path.join(OUT, "boss")
os.makedirs(BOSSDIR, exist_ok=True)


def start_snap(k):
    return "play_start.snap" if k == 0 else os.path.join("agents", "systems", "lvl%d.snap" % k)


def one(k, n=8, step=200000, right=False):
    x, y = EXIT[k]
    p1 = os.path.join(BOSSDIR, "B%d_p1.snap" % k)
    run_repl(start_snap(k), ["w 1f014 %04x%04x" % (x + 8, y), "s 900000", "bp aad8 2000000", "snap " + p1],
             log=os.path.join(BOSSDIR, "B%d_p1.log" % k))
    ram = load_snap(p1)
    bx, by = w16(ram, 0x1f024), w16(ram, 0x1f026)
    hx = bx + 110 if right else max(bx - 70, 40)
    lines = ["w 1f014 %04x%04x" % (hx, by), "s 100000"]
    tag = "BR" if right else "B"
    for i in range(n):
        lines += ["bp aad8 2000000", "snap %s/%s%d_%d.snap" % (BOSSDIR, tag, k, i), "s %d" % step]
    out = run_repl(p1, lines, log=os.path.join(BOSSDIR, "%s%d.log" % (tag, k)))
    return k, (bx, by), out.count("state saved")


if __name__ == "__main__":
    right = "--right" in sys.argv
    ks = [int(a) for a in sys.argv[1:] if not a.startswith("--")] or range(8)
    with ThreadPoolExecutor(4) as ex:
        for r in ex.map(lambda k: one(k, right=right), ks):
            print("level index %d boss at %s snapshots %d" % r)
