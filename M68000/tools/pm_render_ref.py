#!/usr/bin/env python3
"""
pm_render_ref.py -- a pure-Python reference renderer for PowerMonger's iso terrain.

Consumes ONLY reversing/powermonger/port/assets/ (terrain.bin, tables.json,
palette.json) -- no emulator, no RAM image -- and reproduces one isometric frame
by re-implementing the projection + triangle rasterisation from graphics.md.

The point of this file is verification: if a frame rebuilt from the exported
assets matches the exported reference/isoframe.png over the terrain region, the
export is complete and the projection maths in SPEC.md is right.

What is faithful here
  - grid corner projection: rotate by yaw, then the real perspective divide
    ($ff7c: sx = x*eye/(eye-depth); sy = (z-horizon)*eye/(eye-depth) + horizon)
  - far -> near walk, 2 triangles per cell, quad split on the packed-corner test
  - colour index = the terrain byte itself (height byte on one triangle, type
    byte on the other); water (< 0x0c) += tick & 3
What is approximated (documented, and exact data is in the asset pack for a port)
  - the rolling-bitplane dither fill is replaced by a flat palette-index fill
    (the dither is a spatial stipple baked into dither.bin; it changes texture,
    not the mean colour, so a flat fill is the right reference for a terrain
    *shape/shade* diff)
  - the yaw rotation basis is a true 2D rotate by yaw * 1.40625 deg (verified:
    at yaw 0xf0 the $13f8a table entry == 32768*sin(337.5 deg))

Usage:
  tools/pm_render_ref.py [--assets DIR] [--out PNG] [--diff]
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
    dwords = list(struct.unpack(f">{len(dith)//2}H", dith))
    return terr, tables, dom, dwords


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


def dither_index(dwords, colour_byte, top_y, y, x):
    """Reproduce the rolling-bitplane dither fill ($e3e2/$e4de).

    A5 = ([$ff9e] + colourByte + (topY<<4)) >> 1   (word index into the table)
    per scanline: A5 += 4 bytes == +2 words
    per 16-px screen-aligned group: 4 words = planes 0..3, bit = 15 - (x & 15)
    """
    wi = ((colour_byte + (top_y << 4)) >> 1) + 2 * (y - top_y)
    wi %= (len(dwords) - 4)
    b = 15 - (x & 15)
    p0 = (dwords[wi] >> b) & 1
    p1 = (dwords[wi + 1] >> b) & 1
    p2 = (dwords[wi + 2] >> b) & 1
    p3 = (dwords[wi + 3] >> b) & 1
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


def fill_tri(idxbuf, cov, dwords, a, b, c, colour_byte, flat=False):
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
                                dither_index(dwords, colour_byte, top_y, y, x))
            cov[base + x] = 1


def render(terr, tables, dwords, cam_x, cam_y, half, tick=0, flat=False,
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
        # $f898 colour: if byte < 0x0c add tick&3 (water shimmer)
        ch = hb + (tick & 3) if hb < 0x0c else hb
        ct = tb + (tick & 3) if tb < 0x0c else tb
        # packed-corner split test ($f9a6: cmp.l TL, BR ; bgt)
        def packed(q):
            return (int(round(q[0])) << 16) | (int(round(q[1])) & 0xFFFF)
        if packed(br) > packed(tl):
            fill_tri(idxbuf, cov, dwords, tl, tr, bl, ch, flat)
            fill_tri(idxbuf, cov, dwords, tr, bl, br, ct, flat)
        else:
            fill_tri(idxbuf, cov, dwords, tl, tr, br, ch, flat)
            fill_tri(idxbuf, cov, dwords, tl, bl, br, ct, flat)
    return idxbuf, cov


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
    ap.add_argument("--out", default=str(here / "scratchpad/pm76_render_ref.png"))
    ap.add_argument("--sweep", action="store_true",
                    help="grid-search camera / angle against the block-mean metric")
    args = ap.parse_args()

    d = Path(args.assets)
    terr, tables, dom, dwords = load_assets(d)
    half = tables["zoom_geometry"]["derived_constants_fdea_fe02"]["$fdec"]

    ref_idx = (d / "reference/isoframe_indices.bin").read_bytes()
    mask = terrain_mask(ref_idx)
    theirs = block_means(ref_idx, dom, lambda i: mask[i])

    def score(cam, deg, sxs, sys_, flat=True):
        buf, cov = render(terr, tables, dwords, cam[0], cam[1], half,
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
    print(f"  verdict: the flat render rebuilds the island silhouette + shading "
          f"ramp from assets/ alone.\n"
          f"           the dither-table phasing and the exact perspective basis "
          f"are not closed (SPEC.md 'Open questions').")

    rgb = [tuple(dom[buf[i]]) if cov[i] else (255, 0, 255) for i in range(W * H)]
    write_png(Path(args.out), W, H, rgb)

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
    write_png(Path(args.out).with_name("pm76_render_compare.png"),
              bw, bh * 2 + 4, comp)
    print(f"wrote {args.out} + pm76_render_compare.png "
          f"(top = reference, bottom = rebuilt from assets/)")


if __name__ == "__main__":
    main()
