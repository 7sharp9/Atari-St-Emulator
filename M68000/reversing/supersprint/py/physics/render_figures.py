"""render_figures.py - figures for the physics write-up, all from a live-race snapshot (offline):
  world_geometry.png     clean track art | wall plane (+ vector polylines, seeds) | surface map cells coloured by kind | all overlaid
  car_footprints.png     the 16 headings of one car: opaque sprite mask, bda4 edge probes (N/S rows, W/E columns) and b798 surface probe points
  heading_vectors.png    the 16-heading direction table (-4118/-4150 (A4))
usage: render_figures.py [snap]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pl import *
from rebuild_walls import decode, ram_plane
import ssport as P
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import gfxview


def clean_art(r, snap):
    """the track art stash at [-90(A4)] (4 interleaved bitplanes, no cars) with the snapshot's live palette"""
    regs = gfxview.load_video_regs(snap)
    pal = []
    for wd in regs['palette_words']:
        pal.append((((wd >> 8) & 7) * 36, ((wd >> 4) & 7) * 36, (wd & 7) * 36))
    base = r.gl(-90)
    img = np.zeros((200, 320, 3), dtype=np.uint8)
    raw = r.bytes(base, 32000)
    for y in range(200):
        for g in range(20):
            o = y * 160 + g * 8
            w = [(raw[o + 2 * k] << 8) | raw[o + 2 * k + 1] for k in range(4)]
            for b in range(16):
                c = sum(((w[k] >> (15 - b)) & 1) << k for k in range(4))
                img[y, g * 16 + b] = pal[c]
    return img


def kind_colour(v):
    if v == 0:
        return None
    if v & 0x80 and (v & 0x7f) == 0:
        return (255, 255, 0)            # gate / checkpoint line
    k, p = (v & 3), (v & 0x7f) >> 2
    return {0: (255, 120, 0), 1: (0, 200, 255), 2: (80, 255, 80), 3: (255, 0, 255)}[k]


def world_geometry(r, snap):
    art = clean_art(r, snap)
    wall = ram_plane(r, 1)
    polys, lines, seeds, ns = decode(r, 0)
    sm = np.frombuffer(r.bytes(r.gl(-1910), 1000), dtype=np.uint8).reshape(25, 40)
    S = 3
    tiles = []
    # 1 art
    a = np.kron(art, np.ones((S, S, 1), dtype=np.uint8))
    tiles.append(a.copy())
    # 2 wall plane with polylines
    w = np.zeros((200, 320, 3), dtype=np.uint8) + 235
    w[wall] = (70, 70, 80)
    wa = np.kron(w, np.ones((S, S, 1), dtype=np.uint8))
    im = Image.fromarray(wa)
    d = ImageDraw.Draw(im)
    for poly in polys:
        if len(poly) > 1:
            d.line([(x * S + 1, y * S + 1) for x, y in poly], fill=(230, 30, 30), width=2)
    for sx, sy in seeds:
        d.ellipse([sx * S - 5, sy * S - 5, sx * S + 5, sy * S + 5], fill=(0, 120, 255))
    tiles.append(np.array(im))
    # 3 surface map over dim art
    b = (art * 0.45 + 0).astype(np.uint8)
    b = np.kron(b, np.ones((S, S, 1), dtype=np.uint8))
    im = Image.fromarray(b)
    d = ImageDraw.Draw(im)
    for cy in range(25):
        for cx in range(40):
            v = int(sm[cy, cx])
            col = kind_colour(v)
            if col:
                d.rectangle([cx * 8 * S + 1, cy * 8 * S + 1, (cx + 1) * 8 * S - 2, (cy + 1) * 8 * S - 2], outline=col, width=2)
                if v & 0x7f:
                    d.text((cx * 8 * S + 3, cy * 8 * S + 3), '%x' % (v & 0x7f), fill=col)
    tiles.append(np.array(im))
    # 4 overlay: art + red wall tint + surface cell boxes + cars
    o = (art * 0.8).astype(np.uint8)
    o = np.kron(o, np.ones((S, S, 1), dtype=np.uint8)).astype(np.float32)
    wm = np.kron(wall.astype(np.uint8), np.ones((S, S), dtype=np.uint8)).astype(bool)
    o[wm] = o[wm] * 0.55 + np.array([180, 30, 30]) * 0.45
    im = Image.fromarray(o.astype(np.uint8))
    d = ImageDraw.Draw(im)
    for cy in range(25):
        for cx in range(40):
            col = kind_colour(int(sm[cy, cx]))
            if col:
                d.rectangle([cx * 8 * S, cy * 8 * S, (cx + 1) * 8 * S - 1, (cy + 1) * 8 * S - 1], outline=col, width=1)
    m = P.Mem(r.b)
    for c in range(4):
        x, y, h = m.a(P.X, c), m.a(P.Y, c), m.a(P.HEAD, c)
        d.rectangle([x * S - 2, y * S - 2, (x + 16) * S + 2, (y + 11) * S + 2], outline=(255, 255, 255), width=1)
    tiles.append(np.array(im))
    H, W = tiles[0].shape[:2]
    sheet = Image.new('RGB', (W * 2 + 12, H * 2 + 12), (20, 20, 20))
    for i, t in enumerate(tiles):
        sheet.paste(Image.fromarray(t), ((i % 2) * (W + 12), (i // 2) * (H + 12)))
    d = ImageDraw.Draw(sheet)
    labels = ['track art (clean stash [-90(A4)])', 'wall plane [-94(A4)]+8000: 38 Bresenham segments (red) + 2 flood seeds (blue)',
              'surface map [-1910(A4)] 40x25 cells: orange k0, cyan k1, green k2 (sector/lap), magenta k3, yellow = gate bit7', 'overlay: wall (red) + cells + car footprint boxes']
    for i, t in enumerate(labels):
        d.text(((i % 2) * (W + 12) + 6, (i // 2) * (H + 12) + 4), t, fill=(255, 255, 255))
    sheet.save(os.path.join(OUT, 'world_geometry.png'))


def car_footprints(r):
    sp = r.gl(-3602)
    S = 12
    cw, ch = 34, 13
    sheet = Image.new('RGB', (4 * cw * S // 1 + 10, 4 * ch * S + 10), (25, 25, 25))
    d = ImageDraw.Draw(sheet)
    for h in range(16):
        ox, oy = (h % 4) * cw * S + 5, (h // 4) * ch * S + 5
        a = sp + ((1 * 16 + h) << 8)
        ops = []
        for row in range(12):
            p = [r.u32(a + 16 * row + 4 * k) for k in range(4)]
            ops.append(((~p[3]) | p[0] | p[1] | p[2]) & 0xffffffff)
        ent = A4 + P.MASKS + h * 16
        off1, off2, m1, m2 = (r.u32(ent + 4 * k) for k in range(4))
        for row in range(12):
            for col in range(32):
                if ops[row] >> (31 - col) & 1:
                    d.rectangle([ox + col * S, oy + row * S, ox + col * S + S - 2, oy + row * S + S - 2], fill=(150, 150, 160))
        r1, r2 = off1 // 4, off2 // 4
        for col in range(32):
            if m1 >> (31 - col) & 1:
                for row in range(r1, r2):
                    d.rectangle([ox + col * S, oy + row * S, ox + col * S + S - 2, oy + row * S + S - 2], outline=(255, 160, 0), width=2)
            if m2 >> (31 - col) & 1:
                for row in range(r1, r2):
                    d.rectangle([ox + col * S, oy + row * S, ox + col * S + S - 2, oy + row * S + S - 2], outline=(80, 200, 255), width=2)
        d.rectangle([ox, oy + r1 * S, ox + 32 * S - 2, oy + r1 * S + S - 2], outline=(255, 60, 60), width=2)
        d.rectangle([ox, oy + r2 * S, ox + 32 * S - 2, oy + r2 * S + S - 2], outline=(60, 255, 60), width=2)
        pr = A4 + P.PROBE + 8 * h
        dx1, dy1, dx2, dy2 = (r.s16(pr + 2 * k) for k in range(4))
        for (dx, dy, col) in ((dx1, dy1, (255, 255, 0)), (dx2, dy2, (255, 0, 255))):
            d.ellipse([ox + dx * S + 1, oy + (dy - 0) * S + 1, ox + dx * S + S - 3, oy + dy * S + S - 3], fill=col)
        d.text((ox + 2, oy + 1), 'heading %d  rows %d..%d  cols %d/%d' % (h, r1, r2, 31 - (m1.bit_length() - 1), 31 - (m2.bit_length() - 1)), fill=(255, 255, 255))
    d.text((8, sheet.size[1] - 14), 'grey = opaque sprite mask; red row = off1 (code bit0, N), green row = off2 (bit1, S); orange column m1 (bit2, W), blue column m2 (bit3, E); yellow/magenta = $b798 surface probes (x,y offsets)', fill=(255, 255, 255))
    sheet.save(os.path.join(OUT, 'car_footprints.png'))


def heading_vectors(r):
    dx = r.arr(P.DIRX, 16)
    dy = r.arr(P.DIRY, 16)
    S = 22
    W = 15 * S + 40
    im = Image.new('RGB', (W * 2, W + 40), (20, 20, 25))
    d = ImageDraw.Draw(im)
    cx, cy = W // 2, W // 2 + 10
    # ideal circle radius 8
    d.ellipse([cx - 8 * S, cy - 8 * S, cx + 8 * S, cy + 8 * S], outline=(70, 70, 90))
    pts = []
    for h in range(16):
        x, y = cx + dx[h] * S, cy + dy[h] * S
        pts.append((x, y))
        d.line([cx, cy, x, y], fill=(120, 200, 255), width=2)
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(255, 200, 0))
        d.text((x + (8 if dx[h] >= 0 else -28), y + (-14 if dy[h] < 0 else 4)), '%d(%d,%d)' % (h, dx[h], dy[h]), fill=(255, 255, 255))
    d.line(pts + [pts[0]], fill=(255, 200, 0), width=1)
    d.text((8, 8), 'heading -> (dirX, dirY) [-4118/-4150(A4)]; y down; grey circle = radius 8', fill=(255, 255, 255))
    # right panel: |v| per heading
    x0 = W + 30
    d.text((x0, 8), 'vector length |(dx,dy)| per heading (px of travel per unit speed)', fill=(255, 255, 255))
    for h in range(16):
        L = (dx[h] ** 2 + dy[h] ** 2) ** 0.5
        y = 40 + h * 20
        d.rectangle([x0 + 50, y, x0 + 50 + int(L * 30), y + 14], fill=(120, 200, 255))
        d.text((x0, y), 'h%02d' % h, fill=(255, 255, 255))
        d.text((x0 + 56 + int(L * 30), y), '%.2f' % L, fill=(255, 255, 255))
    im.save(os.path.join(OUT, 'heading_vectors.png'))


if __name__ == '__main__':
    snap = sys.argv[1] if len(sys.argv) > 1 else sscfg.SNAP_RACE
    r = Ram(snap)
    world_geometry(r, snap)
    car_footprints(r)
    heading_vectors(r)
    print('done')
