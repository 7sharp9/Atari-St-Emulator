"""Check the palette-load model against live palette RAM: for each dumped level-gameplay frame, the 256-entry blocks of palette RAM
at pens 0x000, 0x200, 0x300, 0x400 (mailbox A nibbles) and 0x100, 0x500 (mailbox B) are compared with the ROM sets the level's
$708c/$70b6 mailbox values select.  Prints, per level, how many of the 256 entries match in the best frame, and in how many frames."""
import os, sys, glob, re
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cbrender as R
import palsets as P

ROOT = P.ROOT
S = P.sets()
mbA = [P.W(0x708c + 2 * i) for i in range(6)]
mbB = [P.W(0x70b6 + 2 * i) for i in range(6)]


def raw_of(lo, ext, n=256):
    return np.array([P.W(lo + 2 * i) | (P.W(ext + 2 * i) << 16) for i in range(n)], np.uint32)


def expected(level):
    a = mbA[level]
    exp = {}
    for pen, nib, bi in ((0x000, a & 15, 0), (0x200, (a >> 4) & 15, 1), (0x300, (a >> 8) & 15, 2), (0x400, (a >> 12) & 15, 3)):
        if nib in (0, 15): continue
        _, _, lo, ext = S[(bi, nib)]
        exp[pen] = raw_of(lo, ext)
    k = mbB[level]
    _, _, lo, ext = S[(4, k)]
    exp[0x100] = raw_of(lo, ext); exp[0x500] = raw_of(lo + 0x200, ext + 0x200)
    return exp


if __name__ == "__main__":
    for lv in range(1, 6):
        d = os.path.join(ROOT, "dumps", "lv%d" % lv)
        exp = expected(lv)
        res = {pen: [] for pen in exp}
        nfr = 0
        for b in sorted(glob.glob(os.path.join(d, "f*.bin"))):
            f = int(re.search(r"f(\d+)", b).group(1))
            if f < 2000: continue            # after the level is up
            st = R.State.load(b, f); nfr += 1
            for pen, e in exp.items():
                res[pen].append(int((st.palraw[pen:pen + 256] == e).sum()))
        print("level %d (%d frames after f2000): " % (lv, nfr) + "  ".join("pen %03x best %3d/256 median %3d" % (pen, max(v), sorted(v)[len(v) // 2]) for pen, v in res.items()))
