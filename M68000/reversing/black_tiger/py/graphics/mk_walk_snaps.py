"""mk_walk_snaps.py - per level: start (labelled poke), hold joystick-1 right, snapshot at three page flips."""
import sys
from concurrent.futures import ThreadPoolExecutor
from drive import *

def one(n):
    lines = jump_to_level_start(n) + ["s 3000000", "kbd ff 08", "s 400000"]
    for k in range(3):
        lines += ["bp aad8 2000000", "snap %s/W%d_%d.snap" % (SNAPDIR, n, k), "s 300000"]
    out = run_repl("play_start.snap", lines, log=os.path.join(SNAPDIR, "W%d.log" % n))
    return n, out.count("state saved")

if __name__ == "__main__":
    with ThreadPoolExecutor(4) as ex:
        for n, c in ex.map(one, range(8)):
            print("level", n, "snapshots", c)
