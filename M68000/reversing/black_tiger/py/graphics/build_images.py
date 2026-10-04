"""build_images.py - collect the committed images for reversing/black_tiger/img/graphics/ from the atlases
the other scripts write to $OUT/png and $OUT/screens, as palette-mode PNGs (the sources have <= 17 colours,
so the quantisation is exact).  Run after tiles.py level/atlas, sprite_atlas.py, boss_atlas.py, weapons.py,
pics_atlas.py and the *_check scripts.  Usage: python build_images.py [IMGDIR]   (default
M68000/reversing/black_tiger/img/graphics)."""
import glob
import os
import sys

from bt_common import *  # noqa


def save(im, name, imgdir, bg=(30, 0, 30)):
    if im.mode == "RGBA":
        base = Image.new("RGB", im.size, bg)
        base.paste(im, (0, 0), im)
        im = base
    im = im.convert("RGB")
    n = len(im.getcolors(1 << 24))
    q = im.quantize(colors=max(n, 2), method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    assert q.convert("RGB").tobytes() == im.tobytes(), name + ": quantisation not exact"
    p = os.path.join(imgdir, name)
    q.save(p, optimize=True)
    return os.path.getsize(p)


def stack(files, gap=4, bg=(30, 0, 30)):
    ims = [Image.open(f).convert("RGBA") for f in files]
    W = max(i.width for i in ims)
    H = sum(i.height for i in ims) + gap * (len(ims) - 1)
    m = Image.new("RGBA", (W, H), bg + (255,))
    y = 0
    for i in ims:
        m.paste(i, (0, y)); y += i.height + gap
    return m


def grid(files, cols, scale=1):
    ims = [Image.open(f).convert("RGB") for f in files]
    w, h = ims[0].size
    rows = (len(ims) + cols - 1) // cols
    m = Image.new("RGB", (cols * w, rows * h))
    for k, i in enumerate(ims):
        m.paste(i, ((k % cols) * w, (k // cols) * h))
    return m


def main():
    imgdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "reversing", "black_tiger", "img", "graphics")
    os.makedirs(imgdir, exist_ok=True)
    P = lambda n: os.path.join(PNG, n)
    S = lambda n: os.path.join(OUT, "screens", n)
    tot = 0
    out = {}
    for n in range(8):
        out["level_%d_map.png" % n] = Image.open(P("level_%d_map.png" % n))
    for t in (0, 2, 3, 4, 5, 6, 7):
        im = Image.open(P("tiles_T%d_palA.png" % t)).convert("RGB")
        out["tiles_T%d.png" % t] = im.resize((im.width // 2, im.height // 2), Image.NEAREST)
    banks = sorted(glob.glob(P("spr_BTSPR_bank*.png")))
    out["sprites_BTSPR_banks.png"] = stack(banks)
    out["sprites_BTMAN_hero.png"] = Image.open(P("spr_BTMAN_hero.png"))
    out["sprites_BTA_BTB_bosses.png"] = stack([P("spr_BTA_boss.png"), P("spr_BTB_boss.png")])
    out["sprites_weapon_overlays.png"] = Image.open(P("spr_weapon_overlays.png"))
    out["pics_BTCLIPS.png"] = Image.open(P("pics_BTCLIPS.png"))
    out["pics_BTOBJ.png"] = Image.open(P("pics_BTOBJ.png"))
    out["font_8x8.png"] = Image.open(P("font_8x8.png"))
    out["screens_title_intro.png"] = grid([P("pic_BT000.png"), S("intro_pic.png"), S("intro_text_before.png"), P("pic_BT001.png")][:3], 3)
    out["screen_ending.png"] = grid([S("end_pic.png"), S("end_text1.png"), S("end_text2.png"), S("end_text3.png"), S("end_text4.png"), P("pic_BT5_ending.png")][:5], 3)
    out["screen_shop.png"] = Image.open(S("shop_a.png"))
    out["proof_tiles_live_vs_render.png"] = Image.open(P("proof_tiles.png"))
    out["proof_bosses_live_vs_render.png"] = Image.open(P("proof_bosses.png"))
    for name, im in out.items():
        if im is None:
            continue
        s = save(im, name, imgdir)
        tot += s
        print("%-34s %7d B" % (name, s))
    print("TOTAL %d KB" % (tot // 1024))


main()
