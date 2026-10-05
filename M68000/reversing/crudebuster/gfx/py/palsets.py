"""ROM palette sets: tables read by the palette mailbox routines $70f0 (mailbox $80008), $7324 ($8000a), per-level mailbox values from
$708c / $70b6.  A set is 256 entries; low halves at the table address, extension (blue) halves at the paired table address.
Writes assets/palette_sets.png (every set of every block) and assets/palettes_by_level.png (the sets level init loads)."""
import os, sys, struct
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cbrender as R

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
CBS = os.path.abspath(os.path.join(ROOT, "..", "..", "..", "scratchpad", "crudebuster"))          # scratchpad/crudebuster
ROM = open(os.path.join(CBS, "rom", "cbuster_main.bin"), "rb").read()
L = lambda a: struct.unpack(">I", ROM[a:a + 4])[0]
W = lambda a: struct.unpack(">H", ROM[a:a + 2])[0]

# (name, pens base, low table, ext table, count)   count = number of table entries (set index 1..count)
BLOCKS = [
    ("pf chip0/pf1 (pens 000-0ff)", 0x000, 0x73da, 0x7456, 2),
    ("pf chip0/pf2 (pens 200-2ff)", 0x200, 0x73e2, 0x745e, 8),
    ("pf chip1/pf1 (pens 300-3ff)", 0x300, 0x7402, 0x747e, 4),
    ("pf chip1/pf2 (pens 400-4ff)", 0x400, 0x7412, 0x748e, 8),
    ("sprites low+high (pens 100-1ff and 500-5ff)", 0x100, 0x73be, 0x743a, 7),
]


def entries(lo, ext, n=256):
    raw = np.array([W(lo + 2 * i) | (W(ext + 2 * i) << 16) for i in range(n)], np.uint32)
    return R.palette_rgb(raw)


def sets():
    out = {}
    for bi, (name, base, tlo, text, cnt) in enumerate(BLOCKS):
        for k in range(cnt):
            lo, ext = L(tlo + 4 * k), L(text + 4 * k)
            if bi == 4:
                out[(bi, k + 1)] = (entries(lo, ext, 256), entries(lo + 0x200, ext + 0x200, 256), lo, ext)
            else:
                out[(bi, k + 1)] = (entries(lo, ext, 256), None, lo, ext)
    return out


def swatch(pal, sz=6):
    a = pal.reshape(16, 16, 3)
    return Image.fromarray(a).resize((16 * sz, 16 * sz), Image.NEAREST)


def main():
    S = sets()
    # all sets
    sz = 5; cell = 16 * sz + 4
    maxk = max(c for _, _, _, _, c in BLOCKS)
    img = Image.new("RGB", (cell * 2 * maxk + 220, cell * len(BLOCKS) + 10), (30, 30, 30))
    d = ImageDraw.Draw(img)
    for bi, (name, base, tlo, text, cnt) in enumerate(BLOCKS):
        d.text((4, bi * cell + 30), name[:28], fill=(230, 230, 230))
        for k in range(cnt):
            lo, hi, a, b = S[(bi, k + 1)]
            img.paste(swatch(lo, sz), (220 + k * cell * 2 if False else 220 + k * cell, bi * cell + 5))
    img.save(os.path.join(ROOT, "assets", "palette_sets.png"))
    # by level
    mbA = [W(0x708c + 2 * i) for i in range(6)]
    mbB = [W(0x70b6 + 2 * i) for i in range(6)]
    sz = 6; cell = 16 * sz + 6
    img = Image.new("RGB", (cell * 6 + 70, cell * 6 + 20), (30, 30, 30))
    d = ImageDraw.Draw(img)
    cols = ["pf c0/pf1", "spr", "pf c0/pf2", "pf c1/pf1", "pf c1/pf2", "spr hi"]
    for c, t in enumerate(cols):
        d.text((70 + c * cell, 4), t, fill=(230, 230, 230))
    for lv in range(6):
        d.text((4, 20 + lv * cell + 40), "level %d" % lv, fill=(230, 230, 230))
        a = mbA[lv]
        nib = [a & 15, (a >> 4) & 15, (a >> 8) & 15, (a >> 12) & 15]       # blocks 0, 2, 3, 4
        order = [(0, nib[0]), ("s", mbB[lv]), (1, nib[1]), (2, nib[2]), (3, nib[3])]
        x = 0
        for col, (b, k) in enumerate(order):
            if b == "s":
                lo, hi, _, _ = S[(4, k)]
                img.paste(swatch(lo, sz), (70 + 1 * cell, 20 + lv * cell)); img.paste(swatch(hi, sz), (70 + 5 * cell, 20 + lv * cell))
                continue
            if k in (0, 15):
                continue
            lo, _, _, _ = S[(b, k)]
            pos = {0: 0, 1: 2, 2: 3, 3: 4}[b]
            img.paste(swatch(lo, sz), (70 + pos * cell, 20 + lv * cell))
    img.save(os.path.join(ROOT, "assets", "palettes_by_level.png"))
    for (bi, k), (lo, hi, a, b) in sorted(S.items()):
        print("block %d set %d low $%05x ext $%05x" % (bi, k, a, b))
    print("mailbox A per level", ["%04x" % x for x in mbA], "mailbox B", mbB)


if __name__ == "__main__":
    main()
