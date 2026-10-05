"""layers_full.py: for one dump per stage (the fresh dumps that have CPS registers, preferring gameplay frames with
the camera mid-stage) write the on-screen composite, the whole 64 x 64 scroll-2 map (1024 x 1024 px) and the whole
scroll-3 map (2048 x 2048 px, written at half size) with the trusted streamed window (backgrounds.py docstring) marked.
Output: scratchpad/finalfight/gfx/out/layers/stage<N>_<dump>_{screen,scroll2,scroll3}.png and a table on stdout.
The composite is drawn from that dump alone (sprites of its own object RAM, so a few sprite pixels can differ from
MAME's screen, which shows the previous frame's list; prove.py proves the exact rule on frame pairs)."""
import glob, os, collections
import numpy as np
from PIL import Image, ImageDraw
from cpsgfx import *
import sheetlib as S
import backgrounds as B

OUTD = os.path.join(OUT, "layers")
os.makedirs(OUTD, exist_ok=True)


def main():
    G = Gfx()
    cands = collections.defaultdict(list)
    from census import dumps
    for gp, rp in dumps():
        rg = gp[:-len("_gfxram.bin")] + "_regs.bin"
        d = B.info(gp, rp)
        gg = np.fromfile(gp, dtype=">u2")
        if B.is_map_screen(G, gg, Regs.from_bytes(open(rg, "rb").read()) if os.path.exists(rg) else d["regs"]):
            continue
        d["gp"], d["rg"] = gp, rg
        cands[d["stage"]].append(d)
    for st in sorted(cands):
        ds = sorted(cands[st], key=lambda d: d["cam2x"])
        # screens with a real camera are mid-list; prefer dumps with the HUD up (health bar tiles) - just take the median
        d = ds[len(ds) // 2]
        g = np.fromfile(d["gp"], dtype=">u2")
        regs = Regs.from_bytes(open(d["rg"], "rb").read()) if os.path.exists(d["rg"]) else d["regs"]
        name = "stage%d_%s" % (st, os.path.basename(d["gp"])[:-len("_gfxram.bin")])
        img, _ = compose(G, g, regs)
        Image.fromarray(img).resize((768, 448), Image.NEAREST).save(os.path.join(OUTD, name + "_screen.png"), optimize=True)
        pal = build_palette(g[cps_base(regs.a[A_PAL], 0x400) // 2:][:0xc00], regs.b[B_PALCTRL // 2])
        for L, ts, bkey, camx, sy, win in ((2, 16, A_S2B, d["cam2x"], s16(regs.a[A_S2Y]), (-9, 33)),
                                           (3, 32, A_S3B, d["cam3x"], s16(regs.a[A_S3Y]), (-5, 17))):
            pens, raw, grp = render_tilemap(G, L, g, cps_base(regs.a[bkey], 0x4000))
            rgb = np.zeros(pens.shape + (3,), np.uint8)
            rgb[:] = (20, 20, 28)
            m = pens != 0xffff
            rgb[m] = pal[pens[m]]
            im = Image.fromarray(rgb)
            dr = ImageDraw.Draw(im)
            cc = camx // ts
            # window in map columns (modulo 64) and the visible screen
            for k in range(win[0], win[1]):
                x0 = ((cc + k) & 63) * ts
                dr.line([(x0, 0), (x0, 6)], fill=(255, 200, 60))
            ytop = ((sy + 16) % (64 * ts))
            for k in range(0, 384 // ts + 1):
                x0 = ((cc + k) & 63) * ts
            vis_x0 = ((camx - 0) % (64 * ts))
            dr.rectangle([vis_x0 % (64 * ts), ytop, vis_x0 % (64 * ts) + 383, ytop + 223], outline=(255, 60, 60))
            if L == 3:
                im = im.resize((1024, 1024), Image.NEAREST)
            im.save(os.path.join(OUTD, name + "_scroll%d.png" % L), optimize=True)
        print("stage %d  %s  camera x %04x/%04x  scroll 2 reg y %d  files %s_*" % (st, d["name"], d["cam2x"], d["cam3x"], s16(regs.a[A_S2Y]), name))


if __name__ == "__main__":
    main()
