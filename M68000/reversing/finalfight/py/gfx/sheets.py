"""sheets.py: the whole tile ROM, per layer type, as labelled sheets.

Index labels are the codes the game itself stores (the code word of a map entry, the code word of an object entry),
through the gfx mapper `mapper_S224B` (cps1_v.cpp:790-793):
  sprites  16x16 codes $0000-$21ff   (ROM $000000-$10ffff)   64 per row, 4 files of 34 rows
  scroll 1  8x8   codes $4400-$4bff  (ROM $110000-$12ffff)   64 per row; two files: left half set (gfx 0, even map
            columns) and right half set (gfx 1, odd map columns), see hardware.md
  scroll 2 16x16 codes $3000-$3fff   (ROM $180000-$1fffff)   64 per row
  scroll 3 32x32 codes $0980-$0bff   (ROM $130000-$17ffff)   32 per row
Colour: each tile uses the palette line (and the palette RAM of the dump) with which it is drawn most often in the
dumps (census.py); tiles never seen drawn are shown in a grey ramp (pen n -> 17n) and their label cell is dim.
Pen 15 (transparent) is drawn in the sheet background colour.
Usage: python sheets.py   -> scratchpad/finalfight/gfx/out/sheets/*.png (needs usage.pkl from census.py)"""
import os, pickle
import numpy as np
from PIL import Image, ImageDraw
from cpsgfx import *
import sheetlib as S
import ffframes as F
import chars

OUTD = os.path.join(OUT, "sheets")
os.makedirs(OUTD, exist_ok=True)
TRANSP = np.array([30, 30, 40], dtype=np.uint8)
GREY = np.array([[min(255, 17 * i)] * 3 for i in range(16)], dtype=np.uint8)


def sheet(tiles, codes, per_row, usage, pals, pal_base, title, path, scale=1, label_every=1):
    """tiles: (n, h, w) uint8 pens; codes: label code of tile i; usage: {code: (count, line, dump)}."""
    n, h, w = tiles.shape
    rows = (n + per_row - 1) // per_row
    lm, tm = 40, 24
    cell_w, cell_h = w * scale, h * scale
    W = lm + per_row * cell_w + 2
    H = tm + rows * cell_h + 2
    img = np.zeros((H, W, 3), dtype=np.uint8)
    img[:] = S.BG
    seen = 0
    for i in range(n):
        r, c = divmod(i, per_row)
        t = tiles[i]
        u = usage.get(int(codes[i]))
        if u is not None:
            _, line, di = u
            rgb = pals[di][pal_base + line * 16 + t.astype(np.int32)]
            seen += 1
        else:
            rgb = GREY[t]
        rgb = np.where((t == 15)[..., None], TRANSP, rgb)
        if scale != 1:
            rgb = np.repeat(np.repeat(rgb, scale, axis=0), scale, axis=1)
        img[tm + r * cell_h:tm + (r + 1) * cell_h, lm + c * cell_w:lm + (c + 1) * cell_w] = rgb
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    d.text((4, 3), "%s   %d tiles, %d coloured (drawn in a dump, or used by a live owner's animation), %d grey" % (title, n, seen, n - seen),
           font=S.FONT, fill=S.FG)
    for c in range(per_row):
        if c % 4 == 0:
            d.text((lm + c * cell_w + 2, tm - 11), "%x" % (c & 0xf if per_row <= 16 else c), font=S.FONT_S, fill=S.DIM)
    for r in range(rows):
        if r % label_every == 0:
            d.text((2, tm + r * cell_h + cell_h // 2 - 5), "%04x" % int(codes[r * per_row]), font=S.FONT_S, fill=S.DIM)
    im.save(path, optimize=True)
    return im.size, seen


def augment_sprites(spr):
    """Add the palette line of every sprite tile the animation scripts of a live owner use (frame block attribute word),
    paired with a dump in which that owner is live, for tiles no dump draws.  Returns the number of tiles added."""
    owners = chars.collect()
    ds, cen = chars.live_census()
    cache = {}
    added = 0
    for key, rows in owners.items():
        pal, di, src = chars.owner_palette(key, cen, ds, cache)
        if not src.startswith("live"):
            continue
        for label, a in rows:
            frames, loop = F.script(a)
            for (e, b, d, fl) in frames:
                for ent in F.build(b, 0, 0x80, 0x40, 0, False, 0, 0):
                    for (c, col, fx, fy, sx, sy) in sprite_tiles(ent[0], ent[1], ent[2], ent[3], wrap=False):
                        if c not in spr:
                            spr[c] = (0, col, di)
                            added += 1
    return added


def main():
    G = Gfx()
    u = pickle.load(open(os.path.join(OUT, "usage.pkl"), "rb"))
    use, pals = u["use"], u["pals"]
    out = []
    print('sprite tiles coloured from scripts of live owners:', augment_sprites(use['spr']))
    # sprites: 16x16, palette page 0
    per = 2176
    for k in range(4):
        idx = np.arange(k * per, min((k + 1) * per, 0x2200))
        sz, seen = sheet(G.t16[idx], idx, 64, use["spr"], pals, 0,
                         "sprites $%04x-$%04x (16x16)" % (idx[0], idx[-1]), os.path.join(OUTD, "sprites_%d.png" % k), scale=1)
        out.append(("sprites_%d.png" % k, sz, seen))
    # scroll 2: map code c -> 16x16 tile c (code range $3000-$3fff in the layer's own units); page 2 (pens 0x400)
    idx = np.arange(0x3000, 0x4000)
    sz, seen = sheet(G.t16[idx], idx, 64, use["s2"], pals, 0x400, "scroll 2 $3000-$3fff (16x16)",
                     os.path.join(OUTD, "scroll2.png"))
    out.append(("scroll2.png", sz, seen))
    # scroll 3: 32x32, page 3 (pens 0x600)
    idx = np.arange(0x980, 0xc00)
    sz, seen = sheet(G.t32[idx], idx, 32, use["s3"], pals, 0x600, "scroll 3 $0980-$0bff (32x32)",
                     os.path.join(OUTD, "scroll3.png"))
    out.append(("scroll3.png", sz, seen))
    # scroll 1: 8x8, page 1 (pens 0x200); left and right half sets, 2x magnified
    idx = np.arange(0x4400, 0x4c00)
    for nm, t in (("left", G.t8l), ("right", G.t8r)):
        sz, seen = sheet(t[idx], idx, 64, use["s1"], pals, 0x200, "scroll 1 $4400-$4bff (8x8, %s half set)" % nm,
                         os.path.join(OUTD, "scroll1_%s.png" % nm), scale=2)
        out.append(("scroll1_%s.png" % nm, sz, seen))
    for o in out:
        print(o, os.path.getsize(os.path.join(OUTD, o[0])))


if __name__ == "__main__":
    main()
