"""Static level background maps from the program ROM.
Format (read from the 68000 streaming code $8e18/$8d26/$98xx/$a090 and checked against live playfield RAM by levelcheck.py):
  a map block is 16 x 16 tile words (512 bytes, row-major, 16 words per row = 256 x 256 pixels of 16x16 tiles);
  layer A  = chip0 playfield 2 ($0a2000): blocks at $41000 + 0x200 * i, per-level screen table at $8c94 (pointer per level, one word per screen)
  layer B  = chip1 playfield 1 ($0a8000): blocks at $4ba00 + 0x200 * i, per-level table at $98fe (word per screen of the layer's own counter)
  layer C  = chip1 playfield 2 ($0aa000): blocks at $4da00 + 0x200 * i, per-level table at $9d20
  screen word: low byte = block for the top 16 rows (0..255 px), high byte = block for the bottom 16 rows (256..511 px); 0xff = none.
The tilemap RAM is a ring: logical column c of the strip (c = 16 * screen + col) lives in tilemap column c mod 64 (scan_rows layout).
Tiles are drawn with the chips' own rules (colour bank, 16x16 gfx: tiles1 for chip0, tiles2 for chip1, no flips: control1 bits 0/1 are 0).
Levels that load blocks directly at init (water, snow, ...: routines $82a8 $83f8 $8516 ...) are listed in STATIC below (page = 1024 x 512)."""
import os, sys, struct
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cbrender as R
import palsets as P

ROM = P.ROM
W = P.W
L = P.L
BASE_A, BASE_B, BASE_C = 0x41000, 0x4ba00, 0x4da00
TBL_A, TBL_B, TBL_C = 0x8c94, 0x98fe, 0x9d20


def block(base, i):
    if i == 0xff:
        return None
    off = base + 0x200 * i
    return np.frombuffer(ROM[off:off + 0x200], dtype=">u2").astype(np.uint16).reshape(16, 16)


def level_table(tbl, level, maxn=40):
    p = L(tbl + 4 * level)
    nxt = [L(tbl + 4 * k) for k in range(6) if L(tbl + 4 * k) > p]
    n = ((min(nxt) - p) // 2) if nxt else maxn
    return [W(p + 2 * k) for k in range(min(n, maxn))]


def strip(base, words):
    """tile-word array [32 rows, 16 * nscreens cols] of the layer for a screen table."""
    n = len(words)
    out = np.zeros((32, 16 * n), np.uint16)
    for s, w in enumerate(words):
        if w == 0xffff:
            continue
        top, bot = block(base, w & 0xff), block(base, w >> 8)
        if top is not None: out[0:16, 16 * s:16 * s + 16] = top
        if bot is not None: out[16:32, 16 * s:16 * s + 16] = bot
    return out


def draw_tiles(words, chip, pf, pal_rgb, transparent=False):
    """render a tile-word array (rows, cols) like deco16ic with 16x16 tiles: returns RGB (or RGBA with transparency)."""
    g = R.gfx()
    tiles = g.tiles1 if chip == 0 else g.tiles2
    rows, cols = words.shape
    v = words.astype(np.int64)
    code = (v & 0xfff) % len(tiles)
    colour = ((v >> 12) & 0xf) + R.COL_BANK[chip][pf]
    t = tiles[code]                                    # rows, cols, 16, 16
    pens = (colour[:, :, None, None] * 16 + t)
    rgb = pal_rgb[pens]
    img = rgb.transpose(0, 2, 1, 3, 4).reshape(rows * 16, cols * 16, 3)
    if transparent:
        a = (t != 0).transpose(0, 2, 1, 3).reshape(rows * 16, cols * 16)
        return np.dstack([img, (a * 255).astype(np.uint8)])
    return img


def level_palette(level):
    """256-entry blocks selected by the level-init mailbox values ($708c / $70b6) -> a 2048-entry RGB table."""
    S = P.sets()
    pal = np.zeros((2048, 3), np.uint8)
    a = W(0x708c + 2 * level); b = W(0x70b6 + 2 * level)
    for pen, nib, bi in ((0x000, a & 15, 0), (0x200, (a >> 4) & 15, 1), (0x300, (a >> 8) & 15, 2), (0x400, (a >> 12) & 15, 3)):
        if nib in (0, 15): continue
        pal[pen:pen + 256] = S[(bi, nib)][0]
    lo, hi, _, _ = S[(4, b)]
    pal[0x100:0x200] = lo; pal[0x500:0x600] = hi
    return pal
