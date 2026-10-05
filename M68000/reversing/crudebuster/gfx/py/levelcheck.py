"""Check the static map model (levelmaps.py) against live tilemap RAM.  For every dumped frame of a level, each of the 64 columns of
chip0 playfield 2 (layer A) must equal the strip column c with c mod 64 == column (any c; rows of the two vertical halves may be swapped).
Empty (all-zero) live columns are not yet streamed and are skipped.  usage: levelcheck.py <dumpname> <level> [layer A|B|C] [first frame]"""
import os, sys, glob, re
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cbrender as R
import levelmaps as M

def live_page(st, chip, pf):
    """live tilemap RAM as a [32 rows, 64 cols] tile-word array (16x16 mode scan_rows)"""
    v = st.vram[chip][pf]
    idx = np.zeros((32, 64), int)
    r_, c_ = np.mgrid[0:32, 0:64]
    idx = (c_ & 0x1f) + ((r_ & 0x1f) << 5) + ((c_ & 0x20) << 5)
    return v[idx]

if __name__ == "__main__":
    name, level = sys.argv[1], int(sys.argv[2])
    layer = sys.argv[3] if len(sys.argv) > 3 else "A"
    fmin = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    base, tbl, chip, pf = {"A": (M.BASE_A, M.TBL_A, 0, 1), "B": (M.BASE_B, M.TBL_B, 1, 0), "C": (M.BASE_C, M.TBL_C, 1, 1)}[layer]
    words = M.level_table(tbl, level)
    S = M.strip(base, words)
    cols = {}
    for c in range(S.shape[1]):
        cols.setdefault(c % 64, []).append(c)
    tot = []
    for b in sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dumps", name, "f*.bin"))):
        f = int(re.search(r"f(\d+)", b).group(1))
        if f < fmin: continue
        st = R.State.load(b, f)
        live = live_page(st, chip, pf)
        n = 0; ne = 0
        for j in range(64):
            lc = live[:, j]
            if not lc.any():
                continue
            ne += 1
            for c in cols.get(j, []):
                sc = S[:, c]
                if (sc == lc).all() or (np.roll(sc, 16) == lc).all():
                    n += 1; break
        tot.append((f, n, ne))
    full = sum(1 for f, n, ne in tot if n == ne and ne > 0)
    print(name, "level", level, "layer", layer, "screens", len(words), "frames", len(tot), "frames with every non-empty live column matched: %d; columns matched %d of %d non-empty" % (full, sum(n for _, n, _ in tot), sum(ne for _, _, ne in tot)))
