#!/usr/bin/env python3
"""
pm_render_ref.py -- a pure-Python reference renderer for PowerMonger's iso terrain.

Consumes ONLY reversing/powermonger/port/assets/ (terrain.bin, tables.json,
palette.json) -- no emulator, no RAM image -- and reproduces one isometric frame
by re-implementing the projection + triangle rasterisation from graphics.md.

The point of this file is verification: if a frame rebuilt from the exported
assets matches the exported reference/isoframe.png over the terrain region, the
export is complete and the projection maths in SPEC.md is right.

What is faithful here (77th pass)
  - grid corner projection: rotate by yaw, then the real perspective divide
    ($ff7c: sx = x*eye/(eye-depth); sy = (z-horizon)*eye/(eye-depth) + horizon).
    Verified byte-exact against the game's own $3f364 corner buffer (81/81).
  - far -> near walk, 2 triangles per cell, quad split on the packed-corner test
  - colour byte = the terrain byte itself (height byte on one triangle, type
    byte on the other); water (< 0x0c) += [$4bb3e]&3 (== 2 in this frame)
  - dither fill: A5(y) = colourByte*128 + ((8*y) mod 128) into dither.bin; one
    16-px pattern per scanline, planes {0,1}=long@A5, {2,3}=long@A5+4, tiled
    screen-X-aligned (see dither_index -- live-traced from $e420, exact)
78th pass: `--ram <settled.ram>` renders the FAITHFUL quadrant-3 grid walk
($fccc) + the $ef62 colour/winding rules from the game's own $3f364 corner
buffer (+ the +64 px iso-window inset), and byte-diffs vs the compose buffer in
the same RAM. See the "faithful terrain layer" section below and SPEC.md 4/7/9.

79th pass: there is NO "sea fill inside the iso diamond". The composed frame
($1c700) differs from the $78000 master ONLY in the island terrain blob
(idx 6/7/11/12/13, ~14.4k px) + a few sprites; the sea (idx 14/15, ~2460 px in
the viewport) is byte-identical between the two -- it is baked into the master,
which $13b9a builds once at mission load. walk_q3 covers 96% of the game's real
terrain layer.

80th pass: ported the $e420 16.16 DDA span walker (_fixed_slope, _dda_walk)
in place of the float+floor()'d spans, and live-traced the dither phase: A5
wraps modulo 128 inside the colour's 128-byte slot (the $e44a roll's `addq.b`
byte-overflows), so the phase is just colourByte*128 + ((8*y) mod 128) -- the
topY term drops out. That kills the 79th's empirical DITHER_COLOUR_BIAS -1
(which was compensating for the missing wrap). exact-palette-index 78% -> 94%,
within-1 93% -> 95%, across pm78_settle / pm74_late / pm70_iso.

What the --assets (no --ram) path approximates
  - the grid walk uses only the quadrant-0 corner assignment (the --ram path
    ports the real $fccc). --out also writes render_flat.png (a clean
    height-ramp fill) for the shape.
  - the yaw rotation basis is a true 2D rotate by yaw * 1.40625 deg (verified:
    at yaw 0xf0 the $13f8a table entry == 32768*sin(337.5 deg))

Usage:
  tools/pm_render_ref.py [--assets DIR] [--out PNG]
  tools/pm_render_ref.py --ram scratchpad/pm78_settle.ram        # faithful + diff
"""

import argparse
import json
import math
import struct
import zlib
from pathlib import Path

W, H = 320, 200


# ---------------------------------------------------------------------------


def load_assets(d: Path):
    terr = (d / "terrain.bin").read_bytes()
    tables = json.loads((d / "tables.json").read_text())
    pal = json.loads((d / "palette.json").read_text())
    dom = pal["palettes"][0]["rgb"]
    dith = (d / "dither.bin").read_bytes()
    return terr, tables, dom, dith


def cell(terr, x, y, plane):
    """plane: 0 type, 1 height, 2 flag, 3 control"""
    i = (y * 64 + x) * 4 + plane
    return terr[i]


def write_png(path, w, h, rgb):
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            raw += bytes(rgb[y * w + x])
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" +
                     chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) +
                     chunk(b"IDAT", zlib.compress(bytes(raw), 9)) +
                     chunk(b"IEND", b""))


# ---------------------------------------------------------------------------
# projection
# ---------------------------------------------------------------------------


def project(tables, terr, cam_x, cam_y, half, tick=0, sx_sign=1, sy_sign=1,
            deg=None):
    p = tables["projection"]
    eye = p["eye_distance_ff98"]           # 320
    horizon = p["horizon_ff96"]            # 130
    zoom = p["zoom_scale_ff9c"]            # 21
    yaw = p["yaw_ff9a"]                    # 0xf0

    theta = math.radians(deg if deg is not None else yaw * 1.40625)
    A = math.sin(theta)                    # $13f8a "sin" half
    B = math.cos(theta)                    # $13f8a "cos" half

    # dynamic height bias = min control-plane height over the visible window
    hs = [cell(terr, cam_x + c, cam_y + r, 3)
          for r in range(2 * half + 1) for c in range(2 * half + 1)]
    bias = min(hs)

    corners = {}
    heights = {}
    for gr in range(2 * half + 1):
        for gc in range(2 * half + 1):
            col = gc - half
            row = gr - half
            h = cell(terr, cam_x + gc, cam_y + gr, 3)
            z = ((h - bias) * zoom) >> 4
            wx = sx_sign * col * zoom
            wy = sy_sign * row * zoom
            rx = wx * B - wy * A
            ry = wy * B + wx * A
            depth = eye - ry
            if depth <= 1:
                depth = 1
            sx = rx * eye / depth
            sy = (z - horizon) * eye / depth + horizon
            corners[(gr, gc)] = (sx + 128, 124 - sy)
            heights[(gr, gc)] = h
    return corners, bias


# ---------------------------------------------------------------------------
# rasteriser
# ---------------------------------------------------------------------------


# 80th pass: DITHER_COLOUR_BIAS is GONE. It was compensating for a missing
# modulo-128 wrap in the dither phase -- the 79th narrowed it to "the roll/topY
# term" and that was right. Live single-step of $e420 (cell topY 75, colour
# 0x26): A5 = 2f358 2f360 2f368 2f370 2f378 -> 2f300 2f308 ... it WRAPS back to
# the start of the colour's 128-byte slot, it never advances into slot cb+1.
# The $e44a roll does `move.l A5,D6 ; add.l D6,D6 ; addq.b #8,D6 ; lsr.l #1,D6`:
# the `addq.b` is a BYTE add on the low byte of 2*A5, so it overflows (mod 256,
# no carry) exactly when A5 & 0x7f reaches 124 -- pinning A5 inside
# [slotBase, slotBase + 128).  (My 79th analysis wrongly assumed the phase never
# lands on 124..127; with the fill's own `and.l (A5)+` +4 it lands on 124 every
# 16th scanline.)  So:
#
#   A5 offset = colourByte*128 + (( (topY&15)*8 + 8*(y - topY) ) mod 128)
#             = colourByte*128 + ((8*y) mod 128)      [ 128*(topY>>4) drops out ]
#
# i.e. the phase depends only on colourByte and the absolute scanline y.
# DITHER_COLOUR_BIAS -1 == a5 - 128 was right only for 16..32px-tall triangles
# (where the port had over-run by exactly one slot); it over-corrected the many
# ~13px cells and under-corrected the tall coast slopes -- hence the residual.


def dither_index(dith, colour_byte, y, x):
    """The 4bpp pattern fill, from the aligned disasm + live trace of the span
    walker ($e3e6 setup, $e420..$e5a6 walker).

    Within one scanline the ENTIRE span is one 16-px pattern: planes 0/1 = the
    long at A5, planes 2/3 = the long at A5+4, tiled screen-X-aligned across the
    whole span (left/right edges only AND a partial-word coverage mask,
    $ec62/$eca2 -- they do not change the pattern; and that mask reduces exactly
    to "pixel x drawn iff ixL <= x <= ixR", see _dda_walk).  The $e44a roll wraps
    A5 modulo 128 inside the colour's slot, so:

        A5 = $2e000 + colourByte*128 + ((8*y) mod 128)        (y = absolute scanline)

    long0 @ A5   -> plane0 = hi16, plane1 = lo16
    long1 @ A5+4 -> plane2 = hi16, plane3 = lo16
    index = p0 | p1<<1 | p2<<2 | p3<<3 ,  bit = 15 - (screenX & 15)
    """
    colour_byte = max(0, colour_byte)
    a5 = colour_byte * 128 + ((8 * y) & 0x7F)
    if a5 + 8 > len(dith):
        a5 = (len(dith) - 8) & ~1
    l0 = struct.unpack_from(">I", dith, a5)[0]
    l1 = struct.unpack_from(">I", dith, a5 + 4)[0]
    b = 15 - (x & 15)
    p0 = (l0 >> (16 + b)) & 1
    p1 = (l0 >> b) & 1
    p2 = (l1 >> (16 + b)) & 1
    p3 = (l1 >> b) & 1
    return p0 | (p1 << 1) | (p2 << 2) | (p3 << 3)


def flat_index(colour_byte):
    """Documented stand-in for the dither fill for the SHAPE proof: map the raw
    terrain byte to one palette index. Water bytes (< 0x0c) -> blue (14/15),
    land -> the green ramp 11..13 keyed on the byte. A faithful port keeps the
    dither.bin stipple; a modern port replaces it with a height-ramp shader
    (SPEC.md 'What a modern port replaces')."""
    if colour_byte < 0x0c:
        return 14 + (colour_byte & 1)
    lo, hi = 0x1c, 0x40                       # observed land-byte range on map 1
    t = max(0.0, min(1.0, (colour_byte - lo) / (hi - lo)))
    return [13, 12, 12, 11, 11, 3, 2, 1][min(7, int(t * 8))]


def fill_tri(idxbuf, cov, dith, a, b, c, colour_byte, flat=False):
    pts = sorted([a, b, c], key=lambda q: q[1])
    (x0, y0), (x1, y1), (x2, y2) = pts
    if y2 == y0:
        return
    top_y = int(math.floor(y0))

    def edge(pa, pb, y):
        (xa, ya), (xb, yb) = pa, pb
        if yb == ya:
            return xa
        return xa + (xb - xa) * (y - ya) / (yb - ya)

    ymin = max(0, int(math.floor(y0)))
    ymax = min(H - 1, int(math.ceil(y2)))
    for y in range(ymin, ymax + 1):
        if y < y1:
            xa = edge(pts[0], pts[2], y)
            xb = edge(pts[0], pts[1], y)
        else:
            xa = edge(pts[0], pts[2], y)
            xb = edge(pts[1], pts[2], y)
        if xa > xb:
            xa, xb = xb, xa
        xs = max(0, int(math.floor(xa)))
        xe = min(W - 1, int(math.ceil(xb)))
        base = y * W
        for x in range(xs, xe + 1):
            idxbuf[base + x] = (flat_index(colour_byte) if flat else
                                dither_index(dith, colour_byte, y, x))
            cov[base + x] = 1


WATER_ADD = 2   # [$4bb3e] & 3 in the reference frame ($f95e/$f964)


def render(terr, tables, dith, cam_x, cam_y, half, tick=WATER_ADD, flat=False,
           sx_sign=1, sy_sign=1, deg=None):
    corners, bias = project(tables, terr, cam_x, cam_y, half,
                            sx_sign=sx_sign, sy_sign=sy_sign, deg=deg)
    idxbuf = bytearray(W * H)
    cov = bytearray(W * H)

    # far -> near: increasing gr (row) is nearer; walk so nearer cells overwrite
    # farther ones (painter's order -- $f898 walks the grid far->near).
    N = 2 * half
    order = sorted(((gr, gc) for gr in range(N) for gc in range(N)),
                   key=lambda rc: (rc[0] + rc[1]))
    for (gr, gc) in order:
        tl = corners[(gr, gc)]
        tr = corners[(gr, gc + 1)]
        bl = corners[(gr + 1, gc)]
        br = corners[(gr + 1, gc + 1)]
        hb = cell(terr, cam_x + gc, cam_y + gr, 1)       # height plane ($438ee-8257)
        tb = cell(terr, cam_x + gc, cam_y + gr, 0)       # type plane   ($438ee+0)
        # $f898 colour: if byte < 0x0c add [$4bb3e]&3 (water shimmer)
        ch = hb + tick if hb < 0x0c else hb
        ct = tb + tick if tb < 0x0c else tb
        # packed-corner split test ($f9a6: cmp.l TL, BR ; bgt)
        def packed(q):
            return (int(round(q[0])) << 16) | (int(round(q[1])) & 0xFFFF)
        if packed(br) > packed(tl):
            fill_tri(idxbuf, cov, dith, tl, tr, bl, ch, flat)
            fill_tri(idxbuf, cov, dith, tr, bl, br, ct, flat)
        else:
            fill_tri(idxbuf, cov, dith, tl, tr, br, ch, flat)
            fill_tri(idxbuf, cov, dith, tl, bl, br, ct, flat)
    return idxbuf, cov


# ---------------------------------------------------------------------------
# faithful terrain layer (78th - 80th pass)
#
# The naive render() above walks the grid in the quadrant-0 corner assignment
# and fills triangles with a float scanline rasteriser. This section ports the
# real thing for yaw 0xf0 (quadrant 3):
#
#   * pm_grid_walk_q3 ($fccc)   -- the exact cell iteration + corner->vertex
#                                  assignment + flag-plane diagonal selector
#   * pm_tri_raster   ($ef62)   -- the cyclic-rotate Y sort, the edge-slope
#                                  compare and the "force colourByte 0x1c when
#                                  vertex 1 is already the left edge" rule
#   * _fixed_slope ($f000) + _dda_walk ($e420) -- 80th: the real 16.16 DDA span
#     walker, two edge accumulators stepped one slope/scanline, the shorter edge
#     bending toward the far vertex at its own scanline. The $ec62/$eca2
#     partial-word masks reduce to "pixel x drawn iff ixL <= x <= ixR" (ixL/ixR
#     = the accumulators truncated >>16), so no planar masking is needed.
#   * the dither phase (dither_index) -- 80th: live-traced, A5 wraps mod 128
#     inside the colour's slot: colourByte*128 + ((8*y) mod 128).
#
# Corner buffer is read straight from the RAM image ($3f364) + the +64 px iso
# window inset (SPEC.md 3), so there is zero projection error here -- this
# isolates the rasteriser. Against a freshly-settled snapshot
# (scratchpad/pm78_settle.ram) this scores ~94% exact / ~95% within +-1 palette
# index over the drawn terrain.
#
# Residual: unit sprites (walk_q3 is terrain-only, so units on the hill diff),
# the tall 0x1c coast slopes (the game spreads idx 1-7, we land nearer flat),
# and a ~1px NE island edge. The "sea fill inside the diamond" does NOT exist --
# it is baked into the $78000 master (79th, SPEC.md 7).
# ---------------------------------------------------------------------------


def load_ram(ram_path: Path):
    b = ram_path.read_bytes()

    def u16(a):
        return (b[a] << 8) | b[a + 1]

    def u32(a):
        return struct.unpack_from(">I", b, a)[0]

    # the $e420 draw pointer ($e3e2, runtime-patched) is buffer + 0x20 BYTES =
    # +64 screen pixels: the iso window starts 64 px in (the left HUD strip).
    # $fecc emits screenX relative to the window origin, so add 64 here. Verified
    # by sweep against $1c700: dx=+64 dy=0 -> 65.8% exact / 93.2% within-1 index
    # (any other offset is strictly worse). See SPEC.md 3/7.
    x_inset = (u32(0xE3E2) & 0x3F) * 2 or 64     # 0x20 bytes -> 64 px

    cam_x = u16(0x4BB3A) - u16(0x57FFC)          # 40 - 4 = 36
    cam_y = u16(0x4BB3C) - u16(0x57FFC)          # 51 - 4 = 47
    half = u16(0xFDEC)                            # 4
    n = 2 * half + 1                              # 9 corners/axis
    # $3f364 corner buffer: packed (sx<<16)|sy, row stride 64 bytes
    corners = {}
    for r in range(n):
        for c in range(n):
            p = u32(0x3F364 + r * 64 + c * 4)
            corners[(r, c)] = ((p >> 16) + x_inset, p & 0xFFFF)
    # terrain planes
    TER, CTL = 0x438EE, 0x3F86C

    def plane(base, x, y):
        return b[base + y * 64 + x]

    planes = dict(
        typ=lambda x, y: plane(TER, x, y),
        hgt=lambda x, y: plane(TER - 8257, x, y),
        flg=lambda x, y: plane(TER + 8257, x, y),
        ctl=lambda x, y: plane(CTL, x, y),
    )
    # dither pattern table. $e3e6 reads [$ffa2] (= $5c000 = 2 * [$ff9e]) and does
    # (2*base + colourByte*256 + rowbits) >> 1, which lands in the [$ff9e] = $2e000
    # data at colourByte*128 + (topY&15)*8 -- so this $2e000 dump is the right
    # bytes. ($5c000 itself is a different, small-int table -- NOT the patterns.)
    dith = b[u32(0xFF9E):u32(0xFF9E) + 0x4000]    # $2e000, 16 KB
    tick = u32(0x4BB3E) & 3
    yaw = u16(0xFF9A)
    # reference: the COMPLETE compose buffer -- the one $e3e2 (the runtime-patched
    # $e420 draw pointer) is NOT currently rendering into. $2df78/$2df7c hold the
    # two buffers ($1c700 / $24400); pick whichever e3e2 is outside.
    draw_ptr = u32(0xE3E2)
    b0, b1 = 0x1C700, 0x24400
    ref_base = b1 if b0 <= draw_ptr < b0 + 32000 else b0
    ref = decode_screen_indices(b, ref_base)
    return dict(corners=corners, planes=planes, dith=dith, tick=tick,
               cam=(cam_x, cam_y), half=half, yaw=yaw, ref=ref, ram=b,
               x_inset=x_inset)


def decode_screen_indices(ram: bytes, base: int):
    out = bytearray(W * H)
    for y in range(H):
        row = ram[base + y * 160: base + y * 160 + 160]
        for xw in range(20):
            pl = struct.unpack_from(">4H", row, xw * 8)
            for bit in range(16):
                idx = 0
                for p in range(4):
                    if pl[p] & (1 << (15 - bit)):
                        idx |= 1 << p
                out[y * W + xw * 16 + bit] = idx
    return out


def _cyclic_ysort(v):
    """$ef62 $efbe..$efd4: rotate the min-Y vertex to the front, keeping the
    other two in their original cyclic order (it is NOT a full sort -- b and c
    are never swapped independently)."""
    sy = [q[1] for q in v]
    if sy[0] <= sy[1] and sy[0] <= sy[2]:
        return [v[0], v[1], v[2]]
    if sy[1] < sy[0] and sy[1] <= sy[2]:
        return [v[1], v[2], v[0]]
    return [v[2], v[0], v[1]]


def _fixed_slope(dx, dy):
    """port of $f000 -- the 16.16 fixed-point edge slope magnitude, sign of dx.
    dy is the (positive) run in scanlines.

      steep  (dy <= |dx|, |slope| >= 1):  ((|dx| << 8) // dy) << 8   ($f01a: the
             two-stage divide -- lsl.l #8, divu, then <<8; overflow -> exactly
             $10000 = 1.0)
      shallow(dy >  |dx|, |slope| <  1):  (|dx| << 16) // dy         ($f00e)

    The steep path truncates at the //dy step *before* the final <<8, so it is
    NOT the same as (|dx|<<16)//dy -- this exact rounding matters for the span
    endpoints.  Result is a signed 32-bit 16.16 value.
    """
    adx = abs(dx)
    if dy <= adx:                                  # steep
        q = (adx << 8) // dy
        val = 0x10000 if q > 0xFFFF else (q & 0xFFFF) << 8
    else:                                          # shallow
        val = ((adx << 16) // dy) & 0xFFFF
    return -val if dx < 0 else val


def ef62_raster(idxbuf, cov, dith, p0, p1, p2, colour, tick, x_inset=0):
    """port of pm_tri_raster ($ef62) -> the $e420 DDA span walker.

    $ef62 ($efbe..$f1de): cyclic-rotate Y sort, then build a span record and
    fall into $e3e6/$e420.  This ports the whole thing:
      * cyclic-rotate Y sort ($efbe..$efd4)
      * general vs flat-top split ($efe0..$f13c)
      * per-edge 16.16 slope via _fixed_slope ($f000)
      * the "force colourByte 0x1c" rule ($f072/$f154): general -> when
        slope(top->bot) > slope(top->mid) i.e. the mid vertex is a LEFT vertex;
        flat-top -> when the right apex X < the left apex X
      * the mid-vertex slope switch: the edge on the mid vertex's side reloads
        its slope to slope(mid->bot) at scanline (mid.y - top.y) ($e42a/$e43e
        run-counter expiry consuming record[20]/[22])
      * water shimmer: colour += tick if colour < 0x0c  ($fccc adds this before
        the call; kept here since walk_q3 passes the raw plane byte)

    The $e420 partial-word edge masks ($ec62 clears the leftmost k bits, $eca2
    keeps the leftmost k+1) reduce -- for a per-pixel index buffer -- to exactly
    "pixel x is drawn iff ixL <= x <= ixR", where ixL/ixR are the 16.16 edge
    accumulators truncated to integer (>>16).  So _dda_walk needs only the DDA;
    no planar masking.

    `x_inset` (85th pass): $ef62's own clip (screenX <= 255, SPEC.md 4) is
    checked against the RAW $3f364 vertex -- p0/p1/p2 here are ALREADY +64
    px inset (load_ram adds it before building the corners dict, SPEC.md 3,
    "Draw inset") when called from the --ram path, so the window in THIS
    coordinate space is [x_inset, x_inset+0xFF], not [0, 0xFF]. Callers on
    raw (non-inset) coordinates -- the synthetic cross-checks -- pass the
    default 0 and get the old [0, 0xFF] behaviour unchanged.
    """
    v = _cyclic_ysort([p0, p1, p2])
    v = [(int(round(x)), int(round(y))) for (x, y) in v]
    (x0, y0), (x1, y1), (x2, y2) = v
    if y0 == y2 and y0 == y1:
        return                                     # degenerate ($f13c rts)

    if colour < 0x0C:
        colour = (colour + tick) & 0xFF

    # ---- flat-top ($f138), incl. the $f134 reorder when bot.y == top.y ----
    if y1 == y0 or y2 == y0:
        if y2 == y0 and y1 != y0:                   # $f134: (top,mid,bot)->(bot,top,mid)
            (x0, y0), (x1, y1), (x2, y2) = (x2, y2), (x0, y0), (x1, y1)
        if y1 != y0:
            return
        h = y2 - y0
        if h <= 0:
            return
        xl, xr = x0, x1
        if xr < xl:                                 # $f154
            xl, xr = xr, xl
            colour = 0x1C
        _dda_walk(idxbuf, cov, dith, colour, y0, h,
                  xl, _fixed_slope(x2 - xl, h), None, 0,
                  xr, _fixed_slope(x2 - xr, h), None, 0,
                  x_inset=x_inset)
        return

    # ---- general: apex v0, other two = v1 (cyclic 2nd), v2 (cyclic 3rd) ----
    # $ef62 does NOT fully sort -- the cyclic Y sort only rotates the min-Y
    # vertex to the front, so y2 >= y1 is NOT guaranteed. Both non-apex edges
    # are walked from the apex ($f000 for v1 -> D4, $f036 for v2 -> D5) and the
    # run counters record[8]=dy1 / record[14]=dy2 decide (via $e42a/$e43e) which
    # edge reloads its slope first -- i.e. the shorter edge bends toward the
    # farther vertex at its own scanline. Triangle height = max(dy1, dy2).
    dy1 = y1 - y0
    dy2 = y2 - y0
    s1 = _fixed_slope(x1 - x0, dy1)                 # apex -> v1  ($f000 -> D4)
    s2 = _fixed_slope(x2 - x0, dy2)                 # apex -> v2  ($f036 -> D5)
    if s1 == s2:
        return                                     # $f06e beq $f13c

    # $f072 bgt $f07a: D5 > D4 i.e. s2 > s1 -> v1 is the LEFT vertex, force 0x1c,
    # no exg. else -> exg (v2 is the left vertex).
    #   edge = (startX, slope, run, nearVertex, farVertex)
    if s2 > s1:
        colour = 0x1C
        left = (x0, s1, dy1, (x1, y1), (x2, y2))
        right = (x0, s2, dy2, (x2, y2), (x1, y1))
    else:
        left = (x0, s2, dy2, (x2, y2), (x1, y1))
        right = (x0, s1, dy1, (x1, y1), (x2, y2))

    total_rows = max(dy1, dy2)

    def edge(e):
        xs, sl, run, (ax, ay), (bx, by) = e
        if run < total_rows and by > ay:           # bends at its own scanline
            return xs, sl, run, _fixed_slope(bx - ax, by - ay)
        return xs, sl, None, 0

    xLs, sL, swL, sL2 = edge(left)
    xRs, sR, swR, sR2 = edge(right)
    _dda_walk(idxbuf, cov, dith, colour, y0, total_rows,
              xLs, sL, swL, sL2, xRs, sR, swR, sR2,
              x_inset=x_inset)


def _dda_walk(idxbuf, cov, dith, colour, top_y, total_rows,
              xL, sL, switchL, sL2, xR, sR, switchR, sR2, x_inset=0):
    """port of $e420. Two 16.16 X accumulators stepped one slope per scanline;
    the switching edge reloads its slope at row `switch`.  Row 0 (top_y) uses
    the initial X with no step ($e41a `bra $e456`).  Per scanline fill the
    integer span [ixL, ixR]; abort the whole triangle if ixR < ixL
    ($e466 sub / $e468 bra $e41e).

    $ef62's clip window is [0, 0xFF] in RAW $3f364 space; if the caller's
    coordinates are already +x_inset (--ram path, see ef62_raster's doc),
    the window shifts to [x_inset, x_inset+0xFF] (85th pass -- previously
    this clipped at the wrong, un-shifted bound, truncating the iso window's
    right ~x_inset px on every --ram score)."""
    win_lo, win_hi = x_inset, x_inset + 0xFF
    pL = xL << 16
    pR = xR << 16
    for row in range(total_rows + 1):
        if row:
            pL += sL
            pR += sR
        if switchL is not None and row == switchL:
            sL = sL2
        if switchR is not None and row == switchR:
            sR = sR2
        y = top_y + row
        if not (0 <= y < H):
            continue
        ixL = pL >> 16
        ixR = pR >> 16
        if ixR < ixL:
            return
        if ixL > win_hi:                            # $ef62 clip: screenX <= 255
            continue                               # wholly past the iso window
        xs = max(0, win_lo, ixL)
        xe = min(W - 1, win_hi, ixR)                # clamp to the iso window edge
        base = y * W
        for x in range(xs, xe + 1):
            idxbuf[base + x] = dither_index(dith, colour, y, x)
            cov[base + x] = 1


def walk_q3(idxbuf, cov, R):
    """port of pm_grid_walk_q3 ($fccc), yaw 0xf0.

    outer k = 0..7 (D7 loop, 8 iters): cell column, EAST -> WEST
    inner j = 0..7 (D6 loop, 8 iters): cell row,    NORTH -> SOUTH  (nearer last)
    cell (cx, cy) = (camCellX + 7 - k, camCellY + j)
    corner (row, col) = (j, 7 - k)
      C00 = (A0)      = corner(col,   row)
      C10 = 4(A0)     = corner(col+1, row)
      C01 = 64(A0)    = corner(col,   row+1)
      C11 = 68(A0)    = corner(col+1, row+1)
    flag plane bit 7 CLEAR ($fcea): split on the C00-C11 diagonal
        tri(C10,C11,C00, type) ; tri(C01,C00,C11, height)
    flag plane bit 7 SET ($fd2e): split on the C10-C01 diagonal, sub-order by
        packed(C01) vs packed(C10)
    """
    cx0, cy0 = R["cam"]
    cn = R["corners"]
    P = R["planes"]
    dith, tick = R["dith"], R["tick"]
    xi = R.get("x_inset", 0)

    def packed(q):
        return (q[0] << 16) | (q[1] & 0xFFFF)

    for k in range(8):                      # EAST -> WEST  (far -> near)
        col = 7 - k
        cx = cx0 + col
        for j in range(8):                  # NORTH -> SOUTH (far -> near)
            row = j
            cy = cy0 + row
            C00 = cn[(row, col)]
            C10 = cn[(row, col + 1)]
            C01 = cn[(row + 1, col)]
            C11 = cn[(row + 1, col + 1)]
            typ = P["typ"](cx, cy)
            hgt = P["hgt"](cx, cy)
            if not (P["flg"](cx, cy) & 0x80):
                ef62_raster(idxbuf, cov, dith, C10, C11, C00, typ, tick, x_inset=xi)
                ef62_raster(idxbuf, cov, dith, C01, C00, C11, hgt, tick, x_inset=xi)
            else:
                if packed(C01) <= packed(C10):
                    ef62_raster(idxbuf, cov, dith, C00, C10, C01, hgt, tick, x_inset=xi)
                    ef62_raster(idxbuf, cov, dith, C11, C01, C10, typ, tick, x_inset=xi)
                else:
                    ef62_raster(idxbuf, cov, dith, C11, C01, C10, typ, tick, x_inset=xi)
                    ef62_raster(idxbuf, cov, dith, C00, C10, C01, hgt, tick, x_inset=xi)


def walk_q0(idxbuf, cov, R):
    """port of pm_grid_walk_q0 ($f98e -- NOT $f98c, see note below), yaw in
    {0x00,0x10,0x20,0x30}.

    $f986's jump table holds *offsets from itself* ($8/$114/$22e/$346 for
    q0..q3), so the real handler entry points are $f986+offset =
    $f98e/$fa9a/$fbb4/$fccc -- the powermonger.sym addresses $f98c/$fa98/
    $fbb2 (2 bytes low) were the RTS of the *previous* handler (or, for
    $f98c, a byte inside the jump table itself), not an entry point. Fixed
    83rd pass, disasm of scratchpad/pm78_settle.ram $f95e..$fdea.

    outer m = 0..7 (D7 loop): cell row,    NORTH -> SOUTH (far -> near)
    inner n = 0..7 (D6 loop): cell column, WEST  -> EAST  (far -> near)
    cell (cx, cy) = (camCellX + n, camCellY + m)      (no start offset --
      A0/A1/A2 are already at the camCell base when $f898 dispatches here)
    corner (row, col) = (m, n)
      C00 = (A0)  C10 = 4(A0)  C01 = 64(A0)  C11 = 68(A0)   (same layout as q3)
    flag plane bit 7 CLEAR ($f9a0): split on the C00-C11 diagonal, sub-order
        by packed(C00) vs packed(C11) (opposite of q3, which sub-orders the
        SET branch and leaves CLEAR unconditional):
        if packed(C11) <= packed(C00): tri(C00,C11,C01,height); tri(C00,C10,C11,type)
        else:                          tri(C11,C00,C10,type);   tri(C11,C01,C00,height)
    flag plane bit 7 SET ($fa26): unconditional, split on the C10-C01 diagonal
        tri(C00,C10,C01,height); tri(C11,C01,C10,type)
    """
    cx0, cy0 = R["cam"]
    cn = R["corners"]
    P = R["planes"]
    dith, tick = R["dith"], R["tick"]
    xi = R.get("x_inset", 0)

    def packed(q):
        return (q[0] << 16) | (q[1] & 0xFFFF)

    for m in range(8):                       # NORTH -> SOUTH (far -> near)
        row = m
        cy = cy0 + row
        for n in range(8):                   # WEST -> EAST (far -> near)
            col = n
            cx = cx0 + col
            C00 = cn[(row, col)]
            C10 = cn[(row, col + 1)]
            C01 = cn[(row + 1, col)]
            C11 = cn[(row + 1, col + 1)]
            typ = P["typ"](cx, cy)
            hgt = P["hgt"](cx, cy)
            if not (P["flg"](cx, cy) & 0x80):
                if packed(C11) <= packed(C00):
                    ef62_raster(idxbuf, cov, dith, C00, C11, C01, hgt, tick, x_inset=xi)
                    ef62_raster(idxbuf, cov, dith, C00, C10, C11, typ, tick, x_inset=xi)
                else:
                    ef62_raster(idxbuf, cov, dith, C11, C00, C10, typ, tick, x_inset=xi)
                    ef62_raster(idxbuf, cov, dith, C11, C01, C00, hgt, tick, x_inset=xi)
            else:
                ef62_raster(idxbuf, cov, dith, C00, C10, C01, hgt, tick, x_inset=xi)
                ef62_raster(idxbuf, cov, dith, C11, C01, C10, typ, tick, x_inset=xi)


def walk_q1(idxbuf, cov, R):
    """port of pm_grid_walk_q1 ($fa9a), yaw in {0x40,0x50,0x60,0x70}.

    outer m = 0..7 (D7 loop): cell column, WEST  -> EAST  (far -> near)
    inner n = 0..7 (D6 loop): cell row,    SOUTH -> NORTH (far -> near)
    cell (cx, cy) = (camCellX + m, camCellY + (7 - n))
      start offset $fdf8/$fdf6 = 448 = 7*64+0 -> A0/A1/A2 start at row 7, col 0
    corner (row, col) = (7 - n, m)
      C00 = (A0)  C10 = 4(A0)  C01 = 64(A0)  C11 = 68(A0)
    flag plane bit 7 CLEAR ($fab8): unconditional, split on the C00-C11 diagonal
        tri(C01,C00,C11, height); tri(C10,C11,C00, type)
    flag plane bit 7 SET ($fafc): split on the C10-C01 diagonal, sub-order by
        packed(C01) vs packed(C10) (same diagonal/condition as q3's SET branch)
        if packed(C01) < packed(C10): tri(C00,C10,C01,height); tri(C11,C01,C10,type)
        else:                         tri(C11,C01,C10,type);   tri(C00,C10,C01,height)
    """
    cx0, cy0 = R["cam"]
    cn = R["corners"]
    P = R["planes"]
    dith, tick = R["dith"], R["tick"]
    xi = R.get("x_inset", 0)

    def packed(q):
        return (q[0] << 16) | (q[1] & 0xFFFF)

    for m in range(8):                       # WEST -> EAST (far -> near)
        col = m
        cx = cx0 + col
        for n in range(8):                   # SOUTH -> NORTH (far -> near)
            row = 7 - n
            cy = cy0 + row
            C00 = cn[(row, col)]
            C10 = cn[(row, col + 1)]
            C01 = cn[(row + 1, col)]
            C11 = cn[(row + 1, col + 1)]
            typ = P["typ"](cx, cy)
            hgt = P["hgt"](cx, cy)
            if not (P["flg"](cx, cy) & 0x80):
                ef62_raster(idxbuf, cov, dith, C01, C00, C11, hgt, tick, x_inset=xi)
                ef62_raster(idxbuf, cov, dith, C10, C11, C00, typ, tick, x_inset=xi)
            else:
                if packed(C01) < packed(C10):
                    ef62_raster(idxbuf, cov, dith, C00, C10, C01, hgt, tick, x_inset=xi)
                    ef62_raster(idxbuf, cov, dith, C11, C01, C10, typ, tick, x_inset=xi)
                else:
                    ef62_raster(idxbuf, cov, dith, C11, C01, C10, typ, tick, x_inset=xi)
                    ef62_raster(idxbuf, cov, dith, C00, C10, C01, hgt, tick, x_inset=xi)


def walk_q2(idxbuf, cov, R):
    """port of pm_grid_walk_q2 ($fbb4), yaw in {0x80,0x90,0xa0,0xb0}.

    outer m = 0..7 (D7 loop): cell row,    SOUTH -> NORTH (far -> near)
    inner n = 0..7 (D6 loop): cell column, EAST  -> WEST  (far -> near)
    cell (cx, cy) = (camCellX + (7 - n), camCellY + (7 - m))
      start offset $fe00/$fdfe = 476 = 7*64+28 -> A0/A1/A2 start at row 7, col 7
    corner (row, col) = (7 - m, 7 - n)
      C00 = (A0)  C10 = 4(A0)  C01 = 64(A0)  C11 = 68(A0)
    flag plane bit 7 CLEAR ($fbd4): split on the C00-C11 diagonal, sub-order by
        packed(C00) vs packed(C11) (mirrors q0's CLEAR branch)
        if packed(C11) <= packed(C00): tri(C01,C00,C11,height); tri(C10,C11,C00,type)
        else:                          tri(C10,C11,C00,type);   tri(C01,C00,C11,height)
    flag plane bit 7 SET ($fc5a): unconditional, split on the C10-C01 diagonal
        tri(C11,C01,C10,type); tri(C00,C10,C01,height)
    """
    cx0, cy0 = R["cam"]
    cn = R["corners"]
    P = R["planes"]
    dith, tick = R["dith"], R["tick"]
    xi = R.get("x_inset", 0)

    def packed(q):
        return (q[0] << 16) | (q[1] & 0xFFFF)

    for m in range(8):                       # SOUTH -> NORTH (far -> near)
        row = 7 - m
        cy = cy0 + row
        for n in range(8):                   # EAST -> WEST (far -> near)
            col = 7 - n
            cx = cx0 + col
            C00 = cn[(row, col)]
            C10 = cn[(row, col + 1)]
            C01 = cn[(row + 1, col)]
            C11 = cn[(row + 1, col + 1)]
            typ = P["typ"](cx, cy)
            hgt = P["hgt"](cx, cy)
            if not (P["flg"](cx, cy) & 0x80):
                if packed(C11) <= packed(C00):
                    ef62_raster(idxbuf, cov, dith, C01, C00, C11, hgt, tick, x_inset=xi)
                    ef62_raster(idxbuf, cov, dith, C10, C11, C00, typ, tick, x_inset=xi)
                else:
                    ef62_raster(idxbuf, cov, dith, C10, C11, C00, typ, tick, x_inset=xi)
                    ef62_raster(idxbuf, cov, dith, C01, C00, C11, hgt, tick, x_inset=xi)
            else:
                ef62_raster(idxbuf, cov, dith, C11, C01, C10, typ, tick, x_inset=xi)
                ef62_raster(idxbuf, cov, dith, C00, C10, C01, hgt, tick, x_inset=xi)


def walk_by_yaw(idxbuf, cov, R):
    """port of $f97e/$f982's dispatch: q = ((yaw+8)>>5)&6, handler = q>>1."""
    q = ((R["yaw"] + 8) >> 5) & 6
    [walk_q0, walk_q1, walk_q2, walk_q3][q >> 1](idxbuf, cov, R)


def _score(idxbuf, cov, ref):
    from collections import Counter
    exact = near = tot = 0
    mine_h, ref_h = Counter(), Counter()
    for i in range(W * H):
        if not cov[i]:
            continue
        tot += 1
        mine_h[idxbuf[i]] += 1
        ref_h[ref[i]] += 1
        if idxbuf[i] == ref[i]:
            exact += 1
        elif abs(idxbuf[i] - ref[i]) <= 1:
            near += 1
    return exact, near, tot, mine_h, ref_h


def render_faithful(ram_path: Path, dom):
    R = load_ram(ram_path)
    ref = R["ref"]
    idxbuf = bytearray(W * H)
    cov = bytearray(W * H)
    q = ((R["yaw"] + 8) >> 5) & 6
    handler = [walk_q0, walk_q1, walk_q2, walk_q3][q >> 1]
    handler(idxbuf, cov, R)
    exact, near, tot, mine_h, ref_h = _score(idxbuf, cov, ref)

    print(f"  faithful {handler.__name__} (yaw ${R['yaw']:02x}) + ef62 + $e420 DDA "
          f"(corners from RAM $3f364, +{R['x_inset']}px inset)")
    print(f"    terrain pixels drawn : {tot}")
    print(f"    exact palette index  : {exact} ({100*exact/max(tot,1):.1f}%)")
    print(f"    within +-1 index     : {exact+near} "
          f"({100*(exact+near)/max(tot,1):.1f}%)")
    print(f"    mine idx dist : {dict(sorted(mine_h.items()))}")
    print(f"    ref  idx dist : {dict(sorted(ref_h.items()))}")
    print(f"    80th: $e420 DDA span walker + the mod-128 dither wrap ported; "
          f"DITHER_COLOUR_BIAS removed.")
    print(f"    residual: unit sprites (walk_q3 is terrain-only) + the tall "
          f"0x1c coast slopes (game spreads idx 1-7) + a ~1px NE edge.")
    return idxbuf, cov, ref, R


# ---------------------------------------------------------------------------
# diff
# ---------------------------------------------------------------------------


def terrain_mask(ref_idx):
    """rough terrain region: the projected grid lands in x ~ 45..250, y ~ 15..180.
    exclude the left HUD panel (x < 44) and the very bottom rows."""
    m = bytearray(W * H)
    for y in range(12, 185):
        for x in range(44, 256):
            m[y * W + x] = 1
    return m


# Geometry as reverse-engineered from $fecc/$ff7c (SPEC.md "Projection"):
#   rX = (c*Q - r*P) >> 15 ,  rY = (r*Q + c*P) >> 15
#   with c = col*zoom, r = row*zoom, P = $13f8a[yaw*2] = 32768*sin(337.5 deg),
#   Q = $13f8a[yaw*2 + 0x80] = 32768*cos(337.5 deg).
# So deg = 337.5 (== -22.5). cam0 = $4bb3a/$4bb3c minus the command-select index.
# This reproduces the island silhouette; the vertical scale / camera origin are
# still ~1 cell off (the pixel diff is not closed -- see SPEC.md).
FIT = dict(cam=(0x28 - 4, 0x33 - 4), deg=337.5, sx_sign=1, sy_sign=1)


def block_means(idx, dom, covmask):
    out = {}
    for by in range(0, H, 8):
        for bx in range(0, W, 8):
            acc = [0, 0, 0]
            n = 0
            for y in range(by, min(by + 8, H)):
                for x in range(bx, min(bx + 8, W)):
                    i = y * W + x
                    if covmask(i):
                        c = dom[idx[i]]
                        acc[0] += c[0]; acc[1] += c[1]; acc[2] += c[2]
                        n += 1
            if n >= 24:
                out[(bx, by)] = (acc[0] / n, acc[1] / n, acc[2] / n)
    return out


def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent.parent
    ap.add_argument("--assets",
                    default=str(here / "reversing/powermonger/port/assets"))
    ap.add_argument("--out", default=str(
        here / "reversing/powermonger/port/assets/reference/render_from_assets.png"))
    ap.add_argument("--sweep", action="store_true",
                    help="grid-search camera / angle against the block-mean metric")
    ap.add_argument("--ram", default=None,
                    help="RAM image (e.g. scratchpad/pm74_late.ram): render the "
                         "faithful walk_q3 + ef62 port, diff vs the $24400 buffer")
    args = ap.parse_args()

    d = Path(args.assets)
    terr, tables, dom, dith = load_assets(d)

    if args.ram:
        buf, cov, ref, R = render_faithful(Path(args.ram), dom)
        fp = Path(args.out).with_name("render_faithful.png")
        rgb = [tuple(dom[buf[i]]) if cov[i] else (255, 0, 255) for i in range(W * H)]
        write_png(fp, W, H, rgb)

        # composite: the $78000 master (HUD + border + sea + island hole) with
        # our terrain layer drawn over the hole -- a full from-scratch frame
        # (79th: the game does exactly this; nothing else fills the diamond).
        master = decode_screen_indices(R["ram"], 0x78000)
        composite = [tuple(dom[buf[i]]) if cov[i] else tuple(dom[master[i]])
                     for i in range(W * H)]
        write_png(fp.with_name("render_faithful_composite.png"), W, H, composite)

        box = (44, 10, 262, 188)
        bw, bh = box[2] - box[0], box[3] - box[1]
        gap = 4
        comp = [(255, 0, 255)] * (bw * (bh * 3 + gap * 2))
        for y in range(bh):
            for x in range(bw):
                si = (box[1] + y) * W + box[0] + x
                comp[y * bw + x] = tuple(dom[ref[si]])                 # reference
                comp[(y + bh + gap) * bw + x] = composite[si]          # our composite
                if not cov[si]:
                    d = (25, 25, 25)
                elif buf[si] == ref[si]:
                    d = (0, 150, 0)
                elif abs(buf[si] - ref[si]) <= 1:
                    d = (150, 150, 0)
                else:
                    d = (200, 0, 0)
                comp[(y + 2 * (bh + gap)) * bw + x] = d                # exact-index diff
        write_png(fp.with_name("render_faithful_compare.png"), bw, bh * 3 + gap * 2, comp)
        print(f"wrote {fp.name} + render_faithful_composite.png + "
              f"render_faithful_compare.png\n"
              f"(compare panels: reference $1c700 / our composite / exact-index "
              f"diff green=match yellow=+-1 red=wrong)")
        return
    half = tables["zoom_geometry"]["derived_constants_fdea_fe02"]["$fdec"]

    ref_idx = (d / "reference/isoframe_indices.bin").read_bytes()
    mask = terrain_mask(ref_idx)
    theirs = block_means(ref_idx, dom, lambda i: mask[i])

    def score(cam, deg, sxs, sys_, flat=True):
        buf, cov = render(terr, tables, dith, cam[0], cam[1], half,
                          flat=flat, sx_sign=sxs, sy_sign=sys_, deg=deg)
        mine = block_means(buf, dom, lambda i: cov[i] and mask[i])
        common = set(mine) & set(theirs)
        exact = tot = 0
        for i in range(W * H):
            if mask[i] and cov[i]:
                tot += 1
                exact += (buf[i] == ref_idx[i])
        de = (sum(math.dist(mine[k], theirs[k]) for k in common) / len(common)
              if common else 1e9)
        return de, len(common), (exact / tot if tot else 0), tot, buf, cov

    cfg = FIT
    if args.sweep:
        best = None
        for cx in range(35, 45):
            for cy in range(45, 55):
                for deg in (337.5, 202.5, 22.5, 157.5, 26.57, -26.57):
                    de, nc, _, _, _, _ = score((cx, cy), deg, 1, 1)
                    if best is None or (de, -nc) < (best[0], -best[1]):
                        best = (de, nc, cx, cy, deg)
        print("best:", best)
        cfg = dict(cam=(best[2], best[3]), deg=best[4], sx_sign=1, sy_sign=1)

    de, nc, exact, tot, buf, cov = score(cfg["cam"], cfg["deg"],
                                         cfg["sx_sign"], cfg["sy_sign"], flat=True)
    ded, _, exd, _, bufd, covd = score(cfg["cam"], cfg["deg"],
                                       cfg["sx_sign"], cfg["sy_sign"], flat=False)
    print(f"config: {cfg}")
    print(f"  terrain pixels drawn          : {tot}")
    print(f"  FLAT fill  (shape proof)      : block-mean dE {de:.1f} over {nc} 8x8 blocks")
    print(f"  DITHER fill (dither.bin)      : block-mean dE {ded:.1f}, "
          f"exact-index {exd*100:.1f}%")
    # per-index distribution over the common terrain pixels -- the honest metric
    from collections import Counter
    mine_h = Counter(bufd[i] for i in range(W * H) if covd[i] and mask[i])
    ref_h = Counter(ref_idx[i] for i in range(W * H) if covd[i] and mask[i])
    print(f"  dither idx dist  mine: {dict(sorted(mine_h.items()))}")
    print(f"  dither idx dist  ref : {dict(sorted(ref_h.items()))}")
    print(f"  verdict: this --assets path uses the NAIVE quadrant-0 walk + a\n"
          f"           float scanline fill -- a shape proof only. Use --ram for\n"
          f"           the faithful quadrant-3 port + the $e420 DDA span walker\n"
          f"           (~94%% exact-index, 92%% terrain coverage). The dither\n"
          f"           phase is A5 = $2e000 + colourByte*128 + ((8*y) mod 128),\n"
          f"           live-traced from $e420 (the roll wraps inside the\n"
          f"           colour's 128-byte slot). SPEC.md 4/7/9.")

    rgb = [tuple(dom[bufd[i]]) if covd[i] else (255, 0, 255) for i in range(W * H)]
    fp = Path(args.out)
    write_png(fp, W, H, rgb)
    write_png(fp.with_name("render_flat.png"), W, H,
              [tuple(dom[buf[i]]) if cov[i] else (255, 0, 255) for i in range(W * H)])

    # side-by-side comparison strip (reference terrain crop over ours)
    pal = json.loads((d / "palette.json").read_text())["palettes"][0]["rgb"]
    box = (40, 12, 258, 185)
    bw, bh = box[2] - box[0], box[3] - box[1]

    def crop(getpx):
        return [getpx(box[0] + x, box[1] + y) for y in range(bh) for x in range(bw)]
    top = crop(lambda x, y: tuple(pal[ref_idx[y * W + x]]))
    bot = crop(lambda x, y: rgb[y * W + x])
    comp = [(255, 0, 255)] * (bw * (bh * 2 + 4))
    for y in range(bh):
        for x in range(bw):
            comp[y * bw + x] = top[y * bw + x]
            comp[(y + bh + 4) * bw + x] = bot[y * bw + x]
    write_png(fp.with_name("render_compare.png"), bw, bh * 2 + 4, comp)
    print(f"wrote {fp.name} + render_compare.png + render_flat.png in {fp.parent}\n"
          f"(compare: top = reference $24400 back buffer, bottom = rebuilt from assets/)")


if __name__ == "__main__":
    main()
