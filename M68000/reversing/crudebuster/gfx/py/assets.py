"""Write the graphics asset sheets under assets/: 8x8 chars, 16x16 tiles1 / tiles2, sprites, palette sample, recomposed frames.
Colouring: each tile/sprite code is drawn with the 16-colour palette it was seen using in the dumped frames (brightest instance, so a
fade does not win), grey ramp for codes never seen.   usage: assets.py [name ...]  (dump dirs, default: all under dumps/)"""
import os, sys, glob, re, collections
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cbrender as R
import ctllog as CL
import gfxlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "assets")
GREY = np.array([[i * 17] * 3 for i in range(16)], np.uint8)


def lum(rgb):
    return int(rgb.astype(np.int32).sum())


def collect(names):
    """best[(kind, code)] = (luminance, 16x3 rgb)   kind: 'char', 't1', 't2', 'spr'"""
    best = {}
    def note(kind, code, base, pal):
        rgb = pal[base:base + 16]
        l = lum(rgb)
        k = (kind, code)
        if k not in best or l > best[k][0]:
            best[k] = (l, rgb.copy())
    for name in names:
        for b in sorted(glob.glob(os.path.join(ROOT, "dumps", name, "f*.bin"))):
            st = R.State.load(b)
            pal = R.palette_rgb(st.palraw)
            for chip in (0, 1):
                for pf in (0, 1):
                    ctl = st.ctl[chip]
                    c1 = (ctl[6] >> (8 * pf)) & 0xff
                    bank = (((ctl[7] >> (8 * pf)) & 0xff) & 0x70) << 8
                    v = st.vram[chip][pf].astype(np.int64)
                    colour = (v >> 12) & 0xf
                    top = (v & 0x8000) != 0
                    if c1 & 3:
                        colour = np.where(top & ((c1 & 3) != 0), colour & 7, colour)
                    code = (v & 0xfff) + bank
                    pen = ((colour & 0xf) + R.COL_BANK[chip][pf]) * 16
                    kind = "char" if c1 & 0x80 else ("t1" if chip == 0 else "t2")
                    for c, p in zip(code, pen):
                        note(kind, int(c), int(p), pal)
            s = st.spr
            for offs in range(0, 0x400, 4):
                y = int(s[offs]); sp = int(s[offs + 1]); x = int(s[offs + 2])
                if y == 0x100 and sp == 0:
                    continue
                col = (x >> 9) & 0x1f
                base = (0x500 if col >= 16 else 0x100) + (col & 15) * 16
                multi = (1 << (((y >> 10) & 1) << 1 | ((y >> 9) & 1))) - 1
                for m in range(multi + 1):
                    note("spr", (sp & ~multi) + m, base, pal)
    return best


def sheet(tiles, kind, best, first, count, cols, tw, scale=1):
    rows = (count + cols - 1) // cols
    img = np.zeros((rows * tw, cols * tw, 3), np.uint8)
    for i in range(count):
        code = first + i
        if code >= len(tiles):
            break
        pal = best[(kind, code)][1] if (kind, code) in best else GREY
        t = tiles[code]
        r, c = divmod(i, cols)
        px = pal[t]
        px[t == 0] = (0, 0, 0) if (kind, code) not in best else px[t == 0]
        img[r * tw:(r + 1) * tw, c * tw:(c + 1) * tw] = px
    im = Image.fromarray(img)
    if scale != 1:
        im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    return im


def main(names):
    os.makedirs(OUT, exist_ok=True)
    g = R.gfx()
    best = collect(names)
    seen = collections.Counter(k[0] for k in best)
    print("codes seen", dict(seen))
    # 8x8 chars: the char ROM half (codes 0x4000..0x4fff, bank 0x40 << 8) 4096 chars as 64 x 64
    sheet(g.chars, "char", best, 0x4000, 4096, 64, 8, 2).save(os.path.join(OUT, "chars_4000-4fff.png"))
    # first 0x80000 bytes of tiles1 read as chars (0..0x3fff): not used by the game (bank 0x40 only); not written
    for i in range(4):
        sheet(g.tiles1, "t1", best, i * 1024, 1024, 32, 16).save(os.path.join(OUT, "tiles1_%04x-%04x.png" % (i * 1024, i * 1024 + 1023)))
        sheet(g.tiles2, "t2", best, i * 1024, 1024, 32, 16).save(os.path.join(OUT, "tiles2_%04x-%04x.png" % (i * 1024, i * 1024 + 1023)))
    for i in range(10):
        sheet(g.sprites, "spr", best, i * 1024, 1024, 32, 16).save(os.path.join(OUT, "sprites_%04x-%04x.png" % (i * 1024, i * 1024 + 1023)))
    return best


if __name__ == "__main__":
    names = sys.argv[1:] or sorted(os.path.basename(d) for d in glob.glob(os.path.join(ROOT, "dumps", "*")) if os.path.exists(os.path.join(d, "f00000.bin")) or glob.glob(os.path.join(d, "f*.bin")))
    main(names)
