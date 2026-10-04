"""text.py - fn11 text ($afa0): render and locate strings.
Glyphs: 8 bytes per char, 1 bpp, from $bb9e + (c-$20)*8 (ST ROM 8x8 font).  D2 = (x/8) << 8 | y, pen colour = D1 & 15
(each plane of the glyph pixels is set or cleared by the matching D1 bit), D1 bit 31 clears the cell first, CR starts the
next line at the original x, 8 rows per line (+$5a0 bytes = 9 text rows of 160 B? see afde: add.w #$5a0 = 9*160... "
"8 px lines are 1280 B = 8 rows, $5a0 = 1440 B = 9 rows)."""
import numpy as np
from bt_common import *


def glyph_bits(ram, ch):
    g = ram[0xbb9e + (ch - 0x20) * 8: 0xbb9e + (ch - 0x20) * 8 + 8]
    return np.array([[(g[y] >> (7 - x)) & 1 for x in range(8)] for y in range(8)], dtype=np.uint8)


def string_mask(ram, s):
    cols = [glyph_bits(ram, ord(c)) for c in s]
    return np.concatenate(cols, axis=1)


def locate(scr, mask, bgcol=0):
    """positions (x cell*8, y) where every glyph pixel is one single non-background colour and every
    non-glyph pixel of the string box is background; returns [(x,y,colour)]"""
    H, W = mask.shape
    hits = []
    for y in range(0, 200 - H + 1):
        for x in range(0, 320 - W + 1, 8):
            win = scr[y:y + H, x:x + W]
            on = win[mask == 1]
            if len(on) and (on == on[0]).all() and on[0] != bgcol and (win[mask == 0] == bgcol).all():
                hits.append((x, y, int(on[0])))
    return hits
