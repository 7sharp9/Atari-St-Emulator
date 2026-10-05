"""Final Fight (CPS1, MAME ffightuc / CPS_B_05 / mapper_S224B) graphics library.

Everything here is a numpy transcription of MAME 0.289 (scratchpad/finalfight/src/cps1.cpp, cps1_v.cpp):
  - ROM load: ROM_LOAD64_WORD x4 (cps1.cpp:5749-5752)
  - gfx layouts (cps1.cpp:3837-3886)
  - bank mapper (cps1_v.cpp:2385-2425, table mapper_S224B_table cps1_v.cpp:790-793)
  - palette (cps1_v.cpp:2619-2650 cps1_build_palette)
  - tilemaps (cps1_v.cpp:2434-2512), sprites (cps1_v.cpp:2720-2866), layer order (cps1_v.cpp:2970-2999)

Repo root comes from __file__.  No MAME needed: the ROM is read from a zip (FF_ROMS or ~/mame-roms/ffight.zip).
"""
import os
import zipfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))   # M68000/
SCR = os.path.join(ROOT, "scratchpad", "finalfight")
OUT = os.path.join(SCR, "gfx", "out")

ROM_FILES = [("ff-5m.7a", 0), ("ff-7m.9a", 2), ("ff-1m.3a", 4), ("ff-3m.5a", 6)]   # cps1.cpp:5749-5752


def load_rom():
    """The 0x200000-byte 'gfx' region: 16-bit chunks, one per 8 bytes (ROM_LOAD64_WORD, no swap)."""
    z = os.path.join(os.environ.get("FF_ROMS", os.path.expanduser("~/mame-roms")), "ffight.zip")
    rom = np.zeros(0x200000, dtype=np.uint8)
    r8 = rom.reshape(-1, 8)
    with zipfile.ZipFile(z) as zf:
        for name, off in ROM_FILES:
            d = np.frombuffer(zf.read(name), dtype=np.uint8).reshape(-1, 2)
            r8[:, off] = d[:, 0]
            r8[:, off + 1] = d[:, 1]
    return rom


def _rows_to_pix(rowbytes):
    """rowbytes: (..., 4) uint8, the 4 bytes of one 8-pixel group.  Plane offsets {24,16,8,0} (bit offsets, bit 0 =
    MSB of a byte, MAME readbit): first plane (offset 24 = byte 3) is the pixel's bit 3, byte 0 is bit 0.
    Pixel x of the group = bit (7-x) of each byte.  Returns (..., 8) uint8 pixel values 0..15."""
    b = rowbytes.astype(np.uint8)
    sh = np.arange(7, -1, -1, dtype=np.uint8)
    p = np.zeros(b.shape[:-1] + (8,), dtype=np.uint8)
    for k in range(4):                       # byte k carries bit k of the pixel value
        p |= (((b[..., k, None] >> sh) & 1) << k).astype(np.uint8)
    return p


def decode16(rom):
    """16x16 tiles (gfx 2): 128 bytes per tile, row = 8 bytes (pixels 0-7 in bytes 0-3, 8-15 in bytes 4-7).
    Returns (n,16,16) uint8."""
    t = rom.reshape(-1, 16, 2, 4)            # tile, row, half, byte
    return _rows_to_pix(t).reshape(-1, 16, 16)


def decode8(rom, half):
    """8x8 tiles (gfx 0 left half, gfx 1 right half): 64 bytes per tile, row stride 8 bytes, 4 bytes used per row."""
    t = rom.reshape(-1, 8, 2, 4)[:, :, half, :]
    return _rows_to_pix(t)                    # (n,8,8)


def decode32(rom):
    """32x32 tiles (gfx 3): 512 bytes per tile, row = 16 bytes = 4 groups of 8 pixels."""
    t = rom.reshape(-1, 32, 4, 4)
    return _rows_to_pix(t).reshape(-1, 32, 32)


class Gfx:
    def __init__(self, rom=None):
        self.rom = load_rom() if rom is None else rom
        self.t16 = decode16(self.rom)             # n16 = 0x4000 (units of 16x16)
        self.t8l = decode8(self.rom, 0)           # n8  = 0x8000
        self.t8r = decode8(self.rom, 1)
        self.t32 = decode32(self.rom)             # n32 = 0x1000


# mapper_S224B_table, cps1_v.cpp:790-793.  (type, start, end) in 8x8 units; bank 0 only.
GFXTYPE_SPRITES, GFXTYPE_SCROLL1, GFXTYPE_SCROLL2, GFXTYPE_SCROLL3 = 1, 2, 4, 8
S224B = [(GFXTYPE_SPRITES, 0x0000, 0x43ff), (GFXTYPE_SCROLL1, 0x4400, 0x4bff),
         (GFXTYPE_SCROLL3, 0x4c00, 0x5fff), (GFXTYPE_SCROLL2, 0x6000, 0x7fff)]   # filled/checked in tests
BANK0_SIZE = 0x8000
SHIFT = {GFXTYPE_SPRITES: 1, GFXTYPE_SCROLL1: 0, GFXTYPE_SCROLL2: 1, GFXTYPE_SCROLL3: 3}


def bank_map(typ, code, table=None):
    """gfxrom_bank_mapper (cps1_v.cpp:2385-2425).  Returns the tile index in that layer's own unit or -1."""
    table = S224B if table is None else table
    sh = SHIFT[typ]
    c = code << sh
    for t, lo, hi in table:
        if lo <= c <= hi:
            if t & typ:
                return (c & (BANK0_SIZE - 1)) >> sh
    return -1


def build_palette(pal_words, ctrl=0x3f):
    """cps1_build_palette (cps1_v.cpp:2619-2650).  pal_words: uint16 array starting at the PALETTE_BASE source.
    Returns (0xc00, 3) uint8 RGB.  Integer arithmetic exactly as the C++ (int division truncating)."""
    out = np.zeros((0xc00, 3), dtype=np.int64)
    pos = 0
    for page in range(6):
        if (ctrl >> page) & 1:
            w = pal_words[pos:pos + 0x200].astype(np.int64)
            pos += 0x200
            bright = 0x0f + ((w >> 12) << 1)
            r = ((w >> 8) & 0xf) * 0x11 * bright // 0x2d
            g = ((w >> 4) & 0xf) * 0x11 * bright // 0x2d
            b = (w & 0xf) * 0x11 * bright // 0x2d
            out[0x200 * page:0x200 * (page + 1)] = np.stack([r, g, b], axis=1)
        else:
            if pos != 0:
                pos += 0x200
    return out.astype(np.uint8)


# ---------------------------------------------------------------- tilemaps
def _scan(layer, col, row):
    """tilemapN_scan (cps1_v.cpp:2434-2451): logical (col,row) -> tile index."""
    if layer == 1:
        return (row & 0x1f) + ((col & 0x3f) << 5) + ((row & 0x20) << 6)
    if layer == 2:
        return (row & 0x0f) + ((col & 0x3f) << 4) + ((row & 0x30) << 6)
    return (row & 0x07) + ((col & 0x3f) << 3) + ((row & 0x38) << 6)


_TS = {1: 8, 2: 16, 3: 32}


def tile_grid(layer, gfxram_words, base):
    """Return code, attr arrays shaped (64 rows, 64 cols) for a layer (1,2,3) whose map starts at byte `base`
    (already masked like cps1_base: base*256 & ~0x3fff & 0x3ffff)."""
    w = gfxram_words[(base // 2):(base // 2) + 0x2000]
    rows, cols = np.mgrid[0:64, 0:64]
    idx = np.vectorize(lambda c, r: _scan(layer, c, r))(cols, rows)
    code = w[2 * idx].astype(np.int64)
    attr = w[2 * idx + 1].astype(np.int64)
    return code, attr


def render_tilemap(G, layer, gfxram_words, base):
    """Full 64x64-tile layer as pen-index image: returns (pens uint16 (H,W) with 0xffff = transparent pixel (pen 15
    or unmapped code), raw uint8 pixel value (H,W), group uint8 (H,W))."""
    ts = _TS[layer]
    code, attr = tile_grid(layer, gfxram_words, base)
    H = 64 * ts
    pens = np.full((H, H), 0xffff, dtype=np.uint16)
    raw = np.full((H, H), 15, dtype=np.uint8)
    grp = np.zeros((H, H), dtype=np.uint8)
    typ = {1: GFXTYPE_SCROLL1, 2: GFXTYPE_SCROLL2, 3: GFXTYPE_SCROLL3}[layer]
    pal0 = {1: 0x20, 2: 0x40, 3: 0x60}[layer]
    for r in range(64):
        for c in range(64):
            cd = int(code[r, c])
            if layer == 3:
                cd &= 0x3fff
            m = bank_map(typ, cd)
            if m < 0:
                continue
            at = int(attr[r, c])
            if layer == 1:
                t = (G.t8r if (c & 1) else G.t8l)[m]          # gfxset = BIT(tile_index,5) = col bit 0
            elif layer == 2:
                t = G.t16[m]
            else:
                t = G.t32[m]
            if at & 0x20:
                t = t[:, ::-1]
            if at & 0x40:
                t = t[::-1, :]
            y0, x0 = r * ts, c * ts
            raw[y0:y0 + ts, x0:x0 + ts] = t
            pal = (at & 0x1f) + pal0
            p = (pal * 16 + t.astype(np.uint16)).astype(np.uint16)
            p[t == 15] = 0xffff
            pens[y0:y0 + ts, x0:x0 + ts] = p
            grp[y0:y0 + ts, x0:x0 + ts] = (at >> 7) & 3
    return pens, raw, grp


# ---------------------------------------------------------------- registers, compositor
# CPS-A register word indices (cps1.h:176-193) and CPS-B byte offsets for CPS_B_05 (cps1_v.cpp:490)
A_OBJ, A_S1B, A_S2B, A_S3B, A_OTHER, A_PAL = 0, 1, 2, 3, 4, 5
A_S1X, A_S1Y, A_S2X, A_S2Y, A_S3X, A_S3Y = 6, 7, 8, 9, 10, 11
A_ROWOFFS, A_VIDEO = 16, 17
B_LAYER, B_PRIO0, B_PALCTRL = 0x28, 0x2a, 0x32          # priority masks at 0x2a,0x2c,0x2e,0x30


def cps_base(reg, boundary):
    """cps1_base (cps1_v.cpp:2099-2111): byte offset into gfx RAM."""
    b = (reg * 256) & ~(boundary - 1)
    return b & 0x3ffff


class Regs:
    """Hardware register values at the instant the frame was drawn.  a: 32 words (CPS-A $800100..), b: 32 words
    (CPS-B $800140..)."""
    def __init__(self, a, b):
        self.a = [int(v) for v in a]
        self.b = [int(v) for v in b]

    def to_bytes(self):
        return np.array(self.a + self.b, dtype='>u2').tobytes()

    @classmethod
    def from_bytes(cls, d):
        w = np.frombuffer(d, dtype='>u2')
        return cls(w[:32], w[32:64])


def s16(v):
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v



def sprite_tiles(x, y, code, colour, wrap=True):
    """cps1_render_sprites (cps1_v.cpp:2756-2862): one object entry -> list of (16x16 tile code, palette line, flipx,
    flipy, sx, sy).  Blocked sprites (attr bits 8-15 = nx-1, ny-1) expand within a 16-wide code row."""
    col = colour & 0x1f
    fx, fy = bool(colour & 0x20), bool(colour & 0x40)
    mc = bank_map(GFXTYPE_SPRITES, code)
    if mc < 0:
        return []
    m = (lambda v: v & 0x1ff) if wrap else (lambda v: v)
    if not (colour & 0xff00):
        return [(mc, col, fx, fy, m(x), m(y))]
    nx, ny = ((colour >> 8) & 0xf) + 1, ((colour >> 12) & 0xf) + 1
    out = []
    for nys in range(ny):
        sy = m(y + nys * 16)
        for nxs in range(nx):
            sx = m(x + nxs * 16)
            cx = (mc + (nx - 1) - nxs) & 0xf if fx else (mc + nxs) & 0xf
            cy = (ny - 1 - nys) if fy else nys
            out.append(((mc & ~0xf) + cx + 0x10 * cy, col, fx, fy, sx, sy))
    return out


def compose(G, gfxram, regs, only=None, want_layers=False, rev=True, pri_all=False, pens=None, obj_base=None):
    """Render one frame the way screen_update_cps1 / render_layers do (cps1_v.cpp:2958-3040, 2970-2999).
    gfxram: big-endian uint16 array of the 0x30000-byte gfx RAM.  Returns a (224,384,3) uint8 image (visible area
    bitmap x 64..447, y 16..239).  only: None or a set of layer numbers (0 sprites, 1/2/3 scroll) to draw.
    want_layers: also return the dict of per-layer images drawn alone (with transparency as alpha-less black and a mask)."""
    a, b = regs.a, regs.b
    pal = build_palette(gfxram[cps_base(a[A_PAL], 0x400) // 2:][:0xc00], b[B_PALCTRL // 2]) if pens is None else pens
    layercontrol = b[B_LAYER // 2]
    video = a[A_VIDEO]
    sels = [(layercontrol >> s) & 3 for s in (6, 8, 10, 12)]
    enab = {1: bool(layercontrol & 0x02), 2: bool(layercontrol & 0x08) and bool(video & 4),
            3: bool(layercontrol & 0x20) and bool(video & 8)}
    prios = [b[(B_PRIO0 + 2 * i) // 2] for i in range(4)]
    bases = {1: cps_base(a[A_S1B], 0x4000), 2: cps_base(a[A_S2B], 0x4000), 3: cps_base(a[A_S3B], 0x4000)}
    scx = {1: s16(a[A_S1X]), 2: s16(a[A_S2X]), 3: s16(a[A_S3X])}
    scy = {1: s16(a[A_S1Y]), 2: s16(a[A_S2Y]), 3: s16(a[A_S3Y])}
    other = gfxram[cps_base(a[A_OTHER], 0x800) // 2:][:0x400]
    X = np.arange(512)
    Y = np.arange(256)
    screen = np.full((256, 512), 0xbff, dtype=np.int32)
    pri = np.zeros((256, 512), dtype=np.uint8)
    flip = bool(video & 0x8000)

    def tile_view(L):
        pens, raw, grp = render_tilemap(G, L, gfxram, bases[L])
        H = pens.shape[0]
        xs = np.broadcast_to(X, (256, 512))
        if L == 2 and (video & 1):                 # row scroll (cps1_v.cpp:3006-3017)
            rows = (Y + scy[2]) & 0x3ff
            off = other[(Y + a[A_ROWOFFS]) & 0x3ff].astype(np.int64)
            xi = (X[None, :] + scx[2] + off[:, None]) & (H - 1)
        else:
            xi = np.broadcast_to((X + scx[L]) & (H - 1), (256, 512))
        yi = ((Y + scy[L]) & (H - 1))[:, None]
        if L == 2 and (video & 1):
            yi = (Y + scy[2])[:, None] & (H - 1)
        return pens[yi, xi], raw[yi, xi], grp[yi, xi]

    views = {}

    def draw_tile_layer(L, mask_pri=False):
        if not enab[L]:
            return
        if L not in views:
            views[L] = tile_view(L)
        pens, raw, grp = views[L]
        m = pens != 0xffff
        screen[m] = pens[m]
        pri[m] = 0

    def high_layer(L):
        if L == 0 or not enab[L]:
            return
        if L not in views:
            views[L] = tile_view(L)
        pens, raw, grp = views[L]
        hit = np.zeros(pens.shape, bool)
        for g in range(4):
            mg = grp == g
            hit |= mg & (((prios[g] >> raw.astype(np.int64)) & 1) == 1)
        pri[hit] = 1

    def draw_sprites():
        base = (cps_base(a[A_OBJ], 0x800) if obj_base is None else obj_base) // 2
        ob = gfxram[base:base + 0x400].astype(np.int64).reshape(-1, 4)
        # end marker (cps1_v.cpp:2705): first entry whose attr high byte is 0xff; 'last' = entry before it
        last = len(ob) - 1
        for i in range(len(ob)):
            if (ob[i, 3] & 0xff00) == 0xff00:
                last = i - 1
                break
        for i in (range(last, -1, -1) if rev else range(0, last + 1)):
            x, y, code, colour = [int(v) for v in ob[i]]
            for (c, col, fx, fy, sx, sy) in sprite_tiles(x, y, code, colour):
                blit_sprite(c, col, fx, fy, sx, sy)

    def blit_sprite(code, col, fx, fy, sx, sy):
        if flip:
            fx, fy, sx, sy = (not fx), (not fy), 512 - 16 - sx, 256 - 16 - sy
        t = G.t16[code]
        if fx:
            t = t[:, ::-1]
        if fy:
            t = t[::-1, :]
        x0, y0 = sx, sy
        cx0, cx1 = max(x0, 64), min(x0 + 16, 448)          # cliprect = visible area
        cy0, cy1 = max(y0, 16), min(y0 + 16, 240)
        if cx0 >= cx1 or cy0 >= cy1:
            return
        sub = t[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0]
        opaque = sub != 15
        p = pri[cy0:cy1, cx0:cx1]
        ok = opaque & (p != 1)                              # pmask 0x02: blocked where priority value is 1
        sc = screen[cy0:cy1, cx0:cx1]
        sc[ok] = (col * 16 + sub[ok].astype(np.int32))
        p[opaque if pri_all else ok] = 31

    def render_layer(L):
        if only is not None and L not in only:
            return
        if L == 0:
            draw_sprites()
        else:
            draw_tile_layer(L)

    l0, l1, l2, l3 = sels
    render_layer(l0)
    if l1 == 0 and (only is None or l0 in only):
        high_layer(l0)
    render_layer(l1)
    if l2 == 0 and (only is None or l1 in only):
        high_layer(l1)
    render_layer(l2)
    if l3 == 0 and (only is None or l2 in only):
        high_layer(l2)
    render_layer(l3)
    img = pal[screen.clip(0, 0xbff)]
    return img[16:240, 64:448], screen[16:240, 64:448]


def regs_from_ram(ram, lag=0):
    """Derive the CPS registers from the game's copies in work RAM (A5 = $ff8000), following the VBL routine
    `$53e`/`$5e8` (ff_main.bin disassembly): hardware = the value the routine wrote at the last VBL.  The game keeps a
    two-stage pipeline (38(A5) <- 34(A5) etc.), so from a RAM dump alone the hardware value is the *older* stage:
    lag=0 uses the stage that is written to the hardware next (38,46,54,40,48,56), i.e. the dump taken after the
    handler ran would hold the value already written; this is only exact when the camera is still.  Use the real
    register dump (gfxdump.lua) when exactness matters."""
    def w(d):
        return int(ram[(0x8000 + d) // 2])
    def by(d):
        return int(ram[(0x8000 + d) // 2] >> (0 if d & 1 else 8)) & 0xff
    a = [0] * 32
    b = [0] * 32
    a[A_OBJ] = w(158)
    a[A_S1B], a[A_S2B], a[A_S3B], a[A_OTHER], a[A_PAL] = 0x9080, 0x90c0, 0x9100, 0x9100, 0x9140
    a[A_S1X] = w(38); a[A_S1Y] = w(40)
    a[A_S2X] = (w(46) + 0xffc0) & 0xffff; a[A_S2Y] = (0x300 - w(48)) & 0xffff
    a[A_S3X] = (w(54) + 0xffc0) & 0xffff; a[A_S3Y] = (0x700 - w(56)) & 0xffff
    a[A_ROWOFFS] = w(74)
    d0 = by(104) ^ by(131)
    a[A_VIDEO] = (((d0 & 0xff) >> 1) | ((d0 & 1) << 15) | w(108)) & 0xffff
    b[B_LAYER // 2] = w(112)
    for i in range(4):
        b[(B_PRIO0 + 2 * i) // 2] = w(114 + 2 * i)
    b[B_PALCTRL // 2] = 0x3f
    return Regs(a, b)


def render_entries(G, entries, pal, anchor=(0, 0)):
    """Draw object entries (x, y, code, attr) the way the chip does (first entry on top, pen 15 transparent) onto a
    private canvas.  x, y are 16-bit signed relative to `anchor`.  Returns (rgba uint8 (H, W, 4), (x0, y0)) with the
    canvas's top-left in anchor-relative pixels, or (None, None) when nothing is drawn.  pal: (0xc00, 3) RGB."""
    tiles = []
    for (x, y, code, attr) in entries:
        x = s16(x) - anchor[0]
        y = s16(y) - anchor[1]
        tiles.extend(sprite_tiles(x, y, code, attr, wrap=False))
    if not tiles:
        return None, None
    x0 = min(t[4] for t in tiles)
    y0 = min(t[5] for t in tiles)
    x1 = max(t[4] for t in tiles) + 16
    y1 = max(t[5] for t in tiles) + 16
    img = np.zeros((y1 - y0, x1 - x0, 4), dtype=np.uint8)
    for (c, col, fx, fy, sx, sy) in reversed(tiles):
        t = G.t16[c]
        if fx:
            t = t[:, ::-1]
        if fy:
            t = t[::-1, :]
        m = t != 15
        rgb = pal[col * 16 + t.astype(np.int32)]
        sub = img[sy - y0:sy - y0 + 16, sx - x0:sx - x0 + 16]
        sub[m, :3] = rgb[m]
        sub[m, 3] = 255
    return img, (x0, y0)


def render_tiles(G, layer, code, attr, pal):
    """Draw arbitrary arrays (rows, cols) of map entries (code word, attribute word) of layer 1/2/3 into an RGBA image
    (pen 15 and unmapped codes transparent).  Same decode as render_tilemap, palette pal (0xc00, 3)."""
    ts = _TS[layer]
    R, C = code.shape
    img = np.zeros((R * ts, C * ts, 4), dtype=np.uint8)
    typ = {1: GFXTYPE_SCROLL1, 2: GFXTYPE_SCROLL2, 3: GFXTYPE_SCROLL3}[layer]
    pal0 = {1: 0x20, 2: 0x40, 3: 0x60}[layer]
    for r in range(R):
        for c in range(C):
            cd = int(code[r, c])
            if layer == 3:
                cd &= 0x3fff
            m = bank_map(typ, cd)
            if m < 0:
                continue
            at = int(attr[r, c])
            t = (G.t8r if (c & 1) else G.t8l)[m] if layer == 1 else (G.t16[m] if layer == 2 else G.t32[m])
            if at & 0x20:
                t = t[:, ::-1]
            if at & 0x40:
                t = t[::-1, :]
            rgb = pal[((at & 0x1f) + pal0) * 16 + t.astype(np.int32)]
            sub = img[r * ts:(r + 1) * ts, c * ts:(c + 1) * ts]
            o = t != 15
            sub[o, :3] = rgb[o]
            sub[o, 3] = 255
    return img
