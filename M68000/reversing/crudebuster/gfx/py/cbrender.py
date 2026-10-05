"""Pure Python renderer for Crude Buster (MAME `cbuster`), from the renderer state dumped by lua/dumpframes.lua.
Implements, from deco16ic.cpp / decospr.cpp / cbuster.cpp (the sources of MAME 0.289):
  * the two DECO55 tilemap chips (two 64x32 playfields each, 8x8 or 16x16 tiles, rowscroll / colscroll, banking),
  * the DECO52 sprite chip (256 entries x 4 words, 1/2/4/8 tile high stacks, flips, flash),
  * the palette (xbgr_888, white level 0x8e),
  * cbuster_state::screen_update layer order including the m_pri flag.
"""
import os, sys, struct
import numpy as np
from PIL import Image
import gfxlib

VIS_Y0, VIS_Y1, W = 8, 247, 256        # visarea x 0-255, y 8-247  (cbuster.cpp set_visarea(0*8, 32*8-1, 1*8, 31*8-1))
H = VIS_Y1 - VIS_Y0 + 1

# --- file layout of dumpframes.lua -----------------------------------------------------------------------------
OFF_CTL, OFF_RAM, OFF_SPR, OFF_PAL, OFF_PALX, OFF_WRAM = 0, 0x20, 0xe820, 0xf020, 0x10020, 0x11020
OFF_TRAIL = 0x15020
SIZE = 0x15020 + 8


class State:
    def __init__(self, data, frame=0):
        assert len(data) == SIZE, len(data)
        self.frame = frame
        be = np.frombuffer(data, dtype=">u2")
        self.ctl = [list(be[0:8]), list(be[8:16])]
        ram = data[OFF_RAM:OFF_RAM + 0xe800]
        r16 = lambda base, n: np.frombuffer(ram, dtype=">u2", count=n, offset=base - 0xa0000).astype(np.uint16)
        # per chip: playfield 1, playfield 2 (0x800 entries used each), rowscroll 1, rowscroll 2 (0x400 words)
        self.vram = [[r16(0xa0000, 0x800), r16(0xa2000, 0x800)], [r16(0xa8000, 0x800), r16(0xaa000, 0x800)]]
        self.rscr = [[r16(0xa4000, 0x400), r16(0xa6000, 0x400)], [r16(0xac000, 0x400), r16(0xae000, 0x400)]]
        self.spr = np.frombuffer(data[OFF_SPR:OFF_SPR + 0x800], dtype=">u2").astype(np.uint16)
        lo = np.frombuffer(data[OFF_PAL:OFF_PAL + 0x1000], dtype=">u2").astype(np.uint32)
        hi = np.frombuffer(data[OFF_PALX:OFF_PALX + 0x1000], dtype=">u2").astype(np.uint32)
        self.palraw = lo | (hi << 16)
        self.wram = data[OFF_WRAM:OFF_WRAM + 0x4000]
        tr = data[OFF_TRAIL:OFF_TRAIL + 8]
        self.pri, self.prot, self.lastw, self.fodd, self.flo = tr[0], (tr[2] << 8) | tr[3], (tr[4] << 8) | tr[5], tr[6], tr[7]

    @classmethod
    def load(cls, path, frame=0):
        return cls(open(path, "rb").read(), frame)


def palette_rgb(raw):
    """palette_device format (4 bytes/entry, xbgr_888): R = bits 0-7, G = 8-15, B = 16-23 of the 32-bit entry (low word at
    $b8000, high word at $b9000); cbuster_state::xbgr_888 clamps each channel to 0x8e and scales (c * 255) / 0x8e."""
    out = np.zeros((len(raw), 3), np.uint8)
    for i, sh in enumerate((0, 8, 16)):
        c = np.minimum((raw >> sh) & 0xff, 0x8e).astype(np.uint32)
        out[:, i] = (c * 255) // 0x8e
    return out


class Gfx:
    def __init__(self):
        r = gfxlib.assemble()
        self.chars = gfxlib.decode(r["tiles1"], "char")      # 32768 8x8
        self.tiles1 = gfxlib.decode(r["tiles1"], "tile")     # 8192 16x16 (the last 4096 are the char ROM read as tiles)
        self.tiles2 = gfxlib.decode(r["tiles2"], "tile")     # 4096
        self.sprites = gfxlib.decode(r["sprites"], "tile")   # 10240


_G = None
def gfx():
    global _G
    if _G is None:
        _G = Gfx()
    return _G


# tilegen setup from cbuster.cpp twocrude(): colour bank per playfield, colour mask 0x0f, 16x16 gfx
COL_BANK = [[0x00, 0x20], [0x30, 0x40]]
TILES16 = ["tiles1", "tiles2"]


def tilemap_bitmap(st, chip, pf):
    """Whole playfield as palette indices (uint16) + opaque mask, the way MAME's tilemap pixmap would hold it.
    Returns (pens[h, w], opaque[h, w], is8x8).  16x16: 1024x512; 8x8: 512x256."""
    g = gfx()
    ctl = st.ctl[chip]
    c1 = (ctl[6] >> (8 * pf)) & 0xff            # control1 of this playfield: word 6, low byte pf1, high byte pf2
    bank = ((ctl[7] >> (8 * pf)) & 0xff) & 0x70
    bank <<= 8                                   # cbuster_state::bank_callback: (bank & 0x70) << 8
    small = bool(c1 & 0x80)
    v = st.vram[chip][pf].astype(np.int64)
    colour = (v >> 12) & 0xf
    fx = np.zeros(len(v), bool); fy = np.zeros(len(v), bool)
    top = (v & 0x8000) != 0
    if c1 & 1:
        fx = top.copy(); colour = np.where(top, colour & 7, colour)
    if c1 & 2:
        fy = top.copy(); colour = np.where(top, colour & 7, colour)
    code = (v & 0xfff) + bank
    colour = (colour & 0x0f) + COL_BANK[chip][pf]
    if small:
        src = g.chars; tw = 8; cols, rows = 64, 32
        idx = np.arange(0x800).reshape(32, 64)                         # TILEMAP_SCAN_ROWS, 64 columns
    else:
        src = g.tiles1 if chip == 0 else g.tiles2; tw = 16; cols, rows = 64, 32
        r_, c_ = np.mgrid[0:32, 0:64]
        idx = (c_ & 0x1f) + ((r_ & 0x1f) << 5) + ((c_ & 0x20) << 5)     # deco16ic scan_rows
    code = code[idx] % len(src); col = colour[idx]; fxx = fx[idx]; fyy = fy[idx]
    t = src[code]                                                      # (rows, cols, tw, tw)
    t = np.where(fxx[:, :, None, None], t[:, :, :, ::-1], t)
    t = np.where(fyy[:, :, None, None], t[:, :, ::-1, :], t)
    pens = (col[:, :, None, None].astype(np.uint16) * 16 + t)
    opaque = t != 0
    pens = pens.transpose(0, 2, 1, 3).reshape(rows * tw, cols * tw)
    opaque = opaque.transpose(0, 2, 1, 3).reshape(rows * tw, cols * tw)
    return pens, opaque, small


def pf_scroll_map(st, chip, pf, pens, opaque, small):
    """Apply the chip's scroll: returns (pens[H, W], opaque[H, W]) over the visible lines y = 8..247.
    control0 (word 5 low/high byte): bit 7 enable, bits 3-6 rowscroll style, bits 0-2 colscroll style.
    control1 (word 6): bit 7 8x8 mode, bit 6 rowscroll, bit 5 colscroll."""
    ctl = st.ctl[chip]
    c0 = (ctl[5] >> (8 * pf)) & 0xff
    c1 = (ctl[6] >> (8 * pf)) & 0xff
    sx = int(ctl[1 + 2 * pf]); sy = int(ctl[2 + 2 * pf])
    rs = st.rscr[chip][pf]
    h, w = pens.shape
    if not (c0 & 0x80):
        return None
    ys = (np.arange(VIS_Y0, VIS_Y1 + 1) + sy) & (h - 1)
    style = (c0 >> 3) & 0xf
    row_on, col_on = bool(c1 & 0x40), bool(c1 & 0x20)
    xs = np.arange(W)[None, :]
    if row_on:
        # row index = map y >> style  (16x16: 512 >> style rows of 1<<style lines; 8x8: 256 >> style rows)
        rowoff = rs[np.minimum(ys >> min(style, 8), 0x3ff)].astype(np.int64) if style <= 8 else np.zeros(len(ys), np.int64)
        sxrow = sx + rowoff
    else:
        sxrow = np.full(len(ys), sx, np.int64)
    X = (xs + sxrow[:, None]) & (w - 1)
    Y = np.repeat(ys[:, None], W, 1)
    if col_on:
        cstyle = c0 & 7
        colw = 8 << cstyle
        # custom renderer (deco16ic custom_tilemap_draw): column offset from rowscroll[0x200 + ((src_x & 0x1ff) / colw)],
        # applied to the y of the source.  The tilemap-core path (colscroll only) indexes the same table by map column.
        off = rs[0x200 + ((X & 0x1ff) // colw)].astype(np.int64)
        Y = (Y + off) & (h - 1)
    return pens[Y, X], opaque[Y, X]


def sprite_bitmap(st, frame_odd):
    """decospr draw_sprites_common into the raw sprite bitmap (value = colour<<4 | pen, colour up to 0xff).
    Entry (4 words): +0 y/flags, +1 tile, +2 x/colour/pri.  Later entries overwrite earlier ones."""
    g = gfx().sprites
    n = len(g)
    bmp = np.zeros((256 + 32, 256 + 32), np.uint16)    # origin shifted by (16, 16) so partly off-screen sprites clip by slicing
    s = st.spr
    for offs in range(0, 0x400, 4):
        y = int(s[offs]); sprite = int(s[offs + 1]); x = int(s[offs + 2])
        flash = (y >> 12) & 1
        if flash and frame_odd:
            continue
        colour = (x >> 9) & 0x7f
        if (y >> 15) & 1:
            colour |= 0x80
        fx = (y >> 13) & 1; fy = (y >> 14) & 1
        t = ((y >> 10) & 1) << 1 | ((y >> 9) & 1)       # bitswap<2>(y, 10, 9)
        multi = (1 << t) - 1
        x &= 0x1ff; y &= 0x1ff
        if x >= 256: x -= 512
        if y >= 256: y -= 512
        y = 240 - y; x = 240 - x
        sprite &= ~multi
        if fy:
            inc = -1
        else:
            sprite += multi; inc = 1
        mult = -16
        while multi >= 0:
            ypos = y + mult * multi
            if ypos <= VIS_Y1 and ypos >= VIS_Y0 - 16:
                tile = g[(sprite - multi * inc) % n]
                if fx: tile = tile[:, ::-1]
                if fy: tile = tile[::-1, :]
                # clip to x 0..255, y 8..247
                for ty in range(16):
                    yy = ypos + ty
                    if yy < VIS_Y0 or yy > VIS_Y1:
                        continue
                    row = tile[ty]
                    for tx in range(16):
                        xx = x + tx
                        if 0 <= xx < 256 and row[tx] != 0:
                            bmp[yy, xx] = (colour << 4) + row[tx]
            multi -= 1
    return bmp[:256, :256]


def sprite_bitmap_fast(st, frame_odd):
    """Same as sprite_bitmap, numpy-sliced."""
    g = gfx().sprites
    n = len(g)
    bmp = np.zeros((256, 256), np.uint16)
    s = st.spr
    for offs in range(0, 0x400, 4):
        y = int(s[offs]); sprite = int(s[offs + 1]); x = int(s[offs + 2])
        if ((y >> 12) & 1) and frame_odd:
            continue
        colour = (x >> 9) & 0x7f
        if (y >> 15) & 1:
            colour |= 0x80
        fx = (y >> 13) & 1; fy = (y >> 14) & 1
        t = ((y >> 10) & 1) << 1 | ((y >> 9) & 1)
        multi = (1 << t) - 1
        x &= 0x1ff; y &= 0x1ff
        if x >= 256: x -= 512
        if y >= 256: y -= 512
        y = 240 - y; x = 240 - x
        sprite &= ~multi
        if fy:
            inc = -1
        else:
            sprite += multi; inc = 1
        while multi >= 0:
            ypos = y - 16 * multi
            if ypos <= VIS_Y1 and ypos >= VIS_Y0 - 16:
                tile = g[(sprite - multi * inc) % n]
                if fx: tile = tile[:, ::-1]
                if fy: tile = tile[::-1, :]
                y0, y1 = max(ypos, VIS_Y0), min(ypos + 16, VIS_Y1 + 1)
                x0, x1 = max(x, 0), min(x + 16, 256)
                if y0 < y1 and x0 < x1:
                    sub = tile[y0 - ypos:y1 - ypos, x0 - x:x1 - x]
                    m = sub != 0
                    dst = bmp[y0:y1, x0:x1]
                    dst[m] = (colour << 4) + sub[m].astype(np.uint16)
            multi -= 1
    return bmp


def render_indexed(st, frame_odd, pri_override=None, layers=None):
    """cbuster_state::screen_update.  Returns uint16 palette indices [H, W] for y = 8..247, plus a dict of intermediates.
    m_pri comes from the 68000's last write to $bc004 (see prot_w); it is not on the bus, pass it as pri_override
    or let it be read from the work RAM (see layer_pri)."""
    pri = layer_pri(st) if pri_override is None else pri_override
    sb = sprite_bitmap_fast(st, frame_odd)[VIS_Y0:VIS_Y1 + 1]
    buf = np.zeros((H, W), np.uint16)

    def pf(chip, which, opaque_all=False):
        pens, opq, small = tilemap_bitmap(st, chip, which)
        r = pf_scroll_map(st, chip, which, pens, opq, small)
        if r is None:
            return
        p, o = r
        m = np.ones_like(o) if opaque_all else o
        buf[m] = p[m]

    def spr(pri_val, colbase):
        # inefficient_copy_sprite_bitmap(bitmap, cliprect, pri, 0x0900, colbase, 0x0ff)
        m = ((sb & 0xf) != 0) & ((sb & 0x900) == pri_val)
        buf[m] = ((sb[m] & 0xff) + colbase).astype(np.uint16)

    pf(1, 1, opaque_all=True)                     # tilegen[1] playfield 2, TILEMAP_DRAW_OPAQUE
    spr(0x800, 0x100); spr(0x900, 0x500)
    if pri:
        pf(0, 1); pf(1, 0)
    else:
        pf(1, 0); pf(0, 1)
    spr(0x000, 0x100); spr(0x100, 0x500)
    pf(0, 0)
    return buf, pri


def layer_pri(st):
    return st.pri


def render_rgb(st, frame_odd, pri=None):
    buf, _ = render_indexed(st, frame_odd, pri_override=pri)
    pal = palette_rgb(st.palraw)
    return pal[buf]


def render_rgb_segments(st, frame_odd, pri, segs):
    """Frame rendered in row bands with different control-register states (see ctllog.py).  Everything else (RAM, palette,
    sprite buffer) is taken from the end-of-frame dump."""
    import copy
    out = None
    for y0, y1, ctl in segs:
        s2 = copy.copy(st); s2.ctl = ctl
        img = render_rgb(s2, frame_odd, pri)
        if out is None:
            out = img.copy()
        out[y0 - VIS_Y0:y1 - VIS_Y0] = img[y0 - VIS_Y0:y1 - VIS_Y0]
    return out


if __name__ == "__main__":
    pass
