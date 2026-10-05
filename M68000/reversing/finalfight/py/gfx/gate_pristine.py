"""gate_pristine.py: the pristine maps of bgmaps.py against every gameplay dump.  For each dump, the tile entries of
its trusted window (scroll 2: world columns camcol-9 .. camcol+32, scroll 3: camcol3-5 .. camcol3+16; see
backgrounds.py) are compared with the pristine map at the same world column and map row, for the rows the pristine
map fills.  Counts: entries equal / entries compared (code and the video bits of the attribute, then the whole
attribute word incl. the terrain code).  The best camera-y page of the pristine set is taken per dump.  Dumps that
are stage-select maps are skipped (backgrounds.is_map_screen)."""
import glob, os, sys, collections
import numpy as np
from cpsgfx import *
from census import dumps
import backgrounds as B

OUTD = os.path.join(OUT, "pristine")


def main():
    G = Gfx()
    pages = collections.defaultdict(dict)
    for p in glob.glob(os.path.join(OUTD, "stage*_s*_y*.npy")):
        b = os.path.basename(p)[:-4]
        st, l, y = b.split("_")
        pages[(int(st[5:]), int(l[1:]))][int(y[1:], 16)] = np.load(p)
    tot = collections.Counter()
    for gp, rp in dumps():
        d = B.info(gp, rp)
        g = np.fromfile(gp, dtype=">u2")
        r = d["regs"]
        if B.is_map_screen(G, g, r):
            continue
        st = d["stage"]
        for L, ts, win, cam, bkey in ((2, 16, (-9, 33), d["cam2x"], A_S2B), (3, 32, (-5, 17), d["cam3x"], A_S3B)):
            if (st, L) not in pages:
                continue
            code, attr = tile_grid(L, g, cps_base(r.a[bkey], 0x4000))
            if L == 3:
                code = code & 0x3fff
            best = None
            for y, arr in pages[(st, L)].items():
                eq = ne = eqa = 0
                for wc in range(cam // ts + win[0], cam // ts + win[1]):
                    if wc < 0 or wc >= len(arr):
                        continue
                    p = arr[wc]
                    rows = np.where(p[:, 0] != 0)[0]
                    mc = wc & 63
                    c1, a1 = code[rows, mc], attr[rows, mc]
                    c0, a0 = p[rows, 0], p[rows, 1]
                    ok = (c1 == c0) & ((a1 & 0x1ff) == (a0 & 0x1ff))
                    eq += int(ok.sum()); ne += len(rows); eqa += int((ok & (a1 == a0)).sum())
                if ne and (best is None or eq / ne > best[0] / best[1]):
                    best = (eq, ne, eqa, y)
            if best:
                tot[(st, L, "eq")] += best[0]; tot[(st, L, "n")] += best[1]; tot[(st, L, "dumps")] += 1
                tot[(st, L, "eqattr")] += best[2]
                if "-v" in sys.argv:
                    print("%-45s stage %d area %d scroll %d cam %04x page y%04x: %d of %d (%.1f%%), with the whole attribute %d" % (
                        d["name"][-45:], st, d["area"], L, cam, best[3], best[0], best[1], 100.0 * best[0] / best[1], best[2]))
    for (st, L) in sorted({(k[0], k[1]) for k in tot}):
        print("stage %d scroll %d: %d dumps, %d of %d tile entries equal (%.2f%%); whole attribute word incl. terrain bits %d" % (
            st, L, tot[(st, L, "dumps")], tot[(st, L, "eq")], tot[(st, L, "n")], 100.0 * tot[(st, L, "eq")] / max(1, tot[(st, L, "n")]),
            tot[(st, L, "eqattr")]))
    e = sum(v for k, v in tot.items() if k[2] == "eq")
    n = sum(v for k, v in tot.items() if k[2] == "n")
    print("TOTAL %d of %d tile entries equal (%.2f%%)" % (e, n, 100.0 * e / n))


if __name__ == "__main__":
    main()
