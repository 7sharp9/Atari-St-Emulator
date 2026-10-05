"""Render each level's layer-A strip (chip0 playfield 2, the walkway layer) from the ROM screen tables, with the level's palette
(mailbox values $708c/$70b6), and a composite over the other two layers.  Layer A is proven against live tilemap RAM (levelcheck.py);
layers B/C in the composite come from the live tilemap RAM of the dumped level (they are parallax layers loaded by per-level code;
their static decode is open).  Writes assets/levels/level<N>_A.png and level<N>_composite.png.
usage: levelstrips.py"""
import os, sys, glob
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cbrender as R
import levelmaps as M
import levelcheck as C

ROOT = M.P.ROOT
DUMP = {0: ("a1", 1500), 1: ("lv1", 2400), 2: ("lv2", 2400), 3: ("lv3", 2400), 4: ("lv4", 2400), 5: ("lv5", 2400)}
PRI = {0: 0, 1: 1, 2: 1, 3: 1, 4: 0, 5: 1}      # m_pri per level: the byte the level routine writes to $bc004 (prot_w), checked in the dumps


def main():
    os.makedirs(os.path.join(ROOT, "assets", "levels"), exist_ok=True)
    for lv in range(6):
        pal = M.level_palette(lv)
        words = M.level_table(M.TBL_A, lv)
        words = [w for w in words] if lv != 5 else words[:15]      # level 5's table runs on into code after the 0xffff terminator
        S = M.strip(M.BASE_A, words)
        a = M.draw_tiles(S, 0, 1, pal, transparent=True)             # RGBA, pen 0 transparent
        bg = np.zeros(a.shape[:2] + (3,), np.uint8)
        # backdrop: live chip1 pages at the level's gameplay frames, tiled horizontally
        name, f = DUMP[lv]
        st = R.State.load(os.path.join(ROOT, "dumps", name, "f%05d.bin" % f), f)
        img_w = a.shape[1]
        pages = {}
        for pf in (1, 0):
            live = C.live_page(st, 1, pf)
            pg = M.draw_tiles(live, 1, pf, pal, transparent=True)
            reps = (img_w + pg.shape[1] - 1) // pg.shape[1]
            pages[pf] = np.tile(pg, (1, reps, 1))[:, :img_w]
        comp = np.zeros(a.shape[:2] + (3,), np.uint8)
        def over(dst, src, opaque=False):
            m = np.ones(src.shape[:2], bool) if opaque else src[:, :, 3] > 0
            dst[m] = src[:, :, :3][m]
        over(comp, pages[1], opaque=True)
        if PRI[lv]:
            pass
        over(comp, pages[0])                       # chip1 pf1 above chip1 pf2 (sprites ignored)
        over(comp, a)                              # layer A (chip0 pf2) above
        Image.fromarray(a[:, :, :3] * (a[:, :, 3:4] > 0)).save(os.path.join(ROOT, "assets", "levels", "level%d_A.png" % lv))
        Image.fromarray(comp).save(os.path.join(ROOT, "assets", "levels", "level%d_composite.png" % lv))
        print("level", lv, "screens", len(words), "strip", a.shape[1], "x", a.shape[0], "palette sets mailbox A %04x B %d" % (M.W(0x708c + 2 * lv), M.W(0x70b6 + 2 * lv)))


if __name__ == "__main__":
    main()
