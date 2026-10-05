"""render_pristine.py: draw the pristine maps of bgmaps.py (npy per stage/layer/camera-y page) as strips.
Rows: the map rows on screen for that camera y (scroll 2 rows 48..63 for y 0 and every y that is a multiple of $400; the
streaming routine fills 34 rows, repeating the chunk, but only these are ever on screen), plus one row of margin.  Palette per column: the palette RAM of the gameplay dump of the same stage whose
camera is nearest to that column (palettes change between areas); stages without a gameplay dump (4, 6) use a grey
ramp per palette line.  Output: scratchpad/finalfight/gfx/out/pristine/png/stage<N>_scroll<L>_y<Y>.png and a _half.png
(50 %) next to each; prints sizes."""
import glob, os, sys, collections
import numpy as np
from PIL import Image, ImageDraw
from cpsgfx import *
import sheetlib as S
import backgrounds as B
from census import dumps

OUTD = os.path.join(OUT, "pristine")
PNG = os.path.join(OUTD, "png")
os.makedirs(PNG, exist_ok=True)


def main():
    G = Gfx()
    pals = collections.defaultdict(list)          # stage -> [(cam2 col, cam3 col, palette)]
    for gp, rp in dumps():
        d = B.info(gp, rp)
        g = np.fromfile(gp, dtype=">u2")
        r = d["regs"]
        if B.is_map_screen(G, g, r):
            continue
        pal = build_palette(g[cps_base(r.a[A_PAL], 0x400) // 2:][:0xc00], 0x3f)
        pals[d["stage"]].append((d["cam2x"] // 16, d["cam3x"] // 32, pal))
    grey = np.zeros((0xc00, 3), np.uint8)
    for i in range(0xc00):
        grey[i] = [min(255, 17 * (i & 15))] * 3
    for p in sorted(glob.glob(os.path.join(OUTD, "stage*_s*_y*.npy"))):
        b = os.path.basename(p)[:-4]
        st, l, y = b.split("_")
        st, L, y = int(st[5:]), int(l[1:]), int(y[1:], 16)
        arr = np.load(p)
        ts = 16 if L == 2 else 32
        rows = np.where((arr[:, :, 0] != 0).any(axis=0))[0]
        # the rows on screen: scroll register y = $300 - camera y (scroll 2) or $700 - camera y (scroll 3) (VBL `$5e8`),
        # the picture starts at bitmap line 16: first visible map row = (reg y + 16) / tile size; one row of margin each side
        regy = (0x300 if L == 2 else 0x700) - y
        top = ((regy + 16) // ts) % 64
        nvis = 224 // ts + (1 if 224 % ts else 0)
        order = [(top - 1 + k) % 64 for k in range(nvis + 2)]
        ncol = arr.shape[0]
        W = ncol * ts
        out = np.zeros((len(order) * ts, W, 4), dtype=np.uint8)
        src = pals.get(st)
        for wc in range(ncol):
            if src:
                key = 0 if L == 2 else 1
                pal = min(src, key=lambda t: abs(t[key] - (wc - (12 if L == 2 else 6))))[2]
            else:
                pal = grey
            code = arr[wc][order, 0][:, None]
            attr = arr[wc][order, 1][:, None]
            out[:, wc * ts:(wc + 1) * ts] = render_tiles(G, L, code, attr, pal)
        bg = Image.new("RGB", (W, out.shape[0] + 14), S.BG)
        top = Image.fromarray(out, "RGBA")
        base = Image.new("RGB", top.size, (20, 20, 28))
        base.paste(top, (0, 0), top)
        bg.paste(base, (0, 14))
        dr = ImageDraw.Draw(bg)
        dr.text((2, 1), "stage %d scroll %d camera y $%04x pristine map, visible rows %s..%s (+1 margin), world x 0..$%x%s" % (
            st, L, y, order[1], order[-2], W, "" if src else "   (grey ramp: no gameplay dump of this stage)"), font=S.FONT_S, fill=S.FG)
        for c in range(0, W, 256):
            dr.line([(c, 12), (c, 18)], fill=(255, 200, 60))
            dr.text((c + 2, 1 if c else 14), "$%x" % c, font=S.FONT_S, fill=(255, 200, 60))
        fn = os.path.join(PNG, "stage%d_scroll%d_y%04x.png" % (st, L, y))
        bg.save(fn, optimize=True)
        half = bg.resize((max(1, bg.width // 2), max(1, bg.height // 2)), Image.LANCZOS)
        half.save(fn[:-4] + "_half.png", optimize=True)
        print("%s %dx%d %d B (half %d B)" % (os.path.basename(fn), bg.width, bg.height, os.path.getsize(fn), os.path.getsize(fn[:-4] + "_half.png")))


if __name__ == "__main__":
    main()
