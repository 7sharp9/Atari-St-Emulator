"""pics_check.py - prove BTCLIPS / BTOBJ picture formats by finding each picture on live screens.
For every entry, slide it (colour 0 transparent) over the draw and displayed buffers of every snapshot
in the corpus and report the best (ok/tot, snapshot, x, y).  Exact = ok == tot."""
import glob
import os
import sys

import numpy as np

from pics import *  # noqa


def corpus():
    names = [os.path.join("agents/graphics/snaps", os.path.basename(p)) for p in sorted(glob.glob(os.path.join(OUT, "snaps", "*.snap")))]
    names += ["play_start.snap", "mv_right.snap", "mv_up.snap"] + ["tl/t%02d.snap" % i for i in (5, 10, 15, 24, 25, 26, 27, 28)]
    return names


def screens(name):
    ram = load_snap(name)
    regs = load_video_regs(snap_path(name))
    out = {}
    for tag, base in (("shown", regs["base"]), ("draw", l32(ram, 0xc31a))):
        if 0x10000 <= base < 0x100000 - 32000:
            out[tag] = np.array(screen_indices(ram, base), dtype=np.uint8)
    return out


def main():
    cache = {}
    for n in corpus():
        try:
            cache[n] = screens(n)
        except Exception as e:
            print("skip", n, e)
    lines = []
    for nm in ("BTCLIPS", "BTOBJ"):
        d, offs, ents = collection(nm)
        for k, rows in enumerate(ents):
            if rows is None:
                continue
            best = (-1, 1, "", "", 0, 0)
            for n, sc in cache.items():
                for tag, scr in sc.items():
                    ok, tot, x, y = best_match(scr, rows)
                    if tot and ok / tot > best[0] / best[1] or (tot and ok == best[0] and False):
                        best = (ok, tot, n, tag, x, y)
            line = "%-8s %2d  %3dx%-3d  best %4d/%-4d (%5.1f%%) %s/%s at (%d,%d)" % (
                nm, k, len(rows[0]), len(rows), best[0], best[1], 100.0 * best[0] / best[1], best[2], best[3], best[4], best[5])
            print(line)
            lines.append(line)
    open(os.path.join(OUT, "pics_check.txt"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
