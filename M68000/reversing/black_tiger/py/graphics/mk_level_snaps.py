"""mk_level_snaps.py - one frame-boundary snapshot per level (0..7) via the labelled start poke."""
import sys
from concurrent.futures import ThreadPoolExecutor
from drive import *

def one(n):
    lines = jump_to_level_start(n) + ["s 3000000", "bp aad8 2000000", "snap %s/L%da.snap" % (SNAPDIR, n)]
    out = run_repl("play_start.snap", lines, log=os.path.join(SNAPDIR, "L%da.log" % n))
    return n, "state saved" in out

if __name__ == "__main__":
    ns = [int(a) for a in sys.argv[1:]] or range(8)
    with ThreadPoolExecutor(4) as ex:
        for n, ok in ex.map(one, ns):
            print("level", n, "ok" if ok else "FAILED")
