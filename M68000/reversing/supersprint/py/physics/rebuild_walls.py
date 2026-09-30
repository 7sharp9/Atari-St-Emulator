"""rebuild_walls.py - rebuild the collision 'wall' plane ([-94(A4)]+8000, 1 bpp, 320x200) from the track's vector data and compare
it pixel-for-pixel with the RAM image. Pipeline ($15884 -> $14cd4):
   polylines (Bresenham, $14e3e, OR into the plane)  +  flood-fill seeds ($14fdc)  ->  plane 1 (1 = solid: wall / infield / outside).
Track vector data: word list at [-8076(A4)]; word k = start index (in words) of track k; at that index: n (vertex count),
then n (x,y) vertices with (-1,-1) pairs separating polylines, then the seed count and (x,y) seeds.
usage: rebuild_walls.py [snap] [track]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pl import *
import numpy as np
from PIL import Image


def decode(r, track):
    base = r.gl(-8076)
    pos = r.u16(base + 2 * track)
    w = lambda i: r.s16(base + 2 * i)
    n = w(pos); pos += 1
    cnt = n - 1
    polys, cur = [], []
    x0, y0 = w(pos), w(pos + 1); pos += 2
    cur.append((x0, y0))
    lines = []
    # mirror $14cd4's loop
    count = cnt
    while count > 0:
        x1, y1 = w(pos), w(pos + 1)
        lines.append(((x0, y0), (x1, y1)))
        cur.append((x1, y1))
        x0, y0 = x1, y1
        pos += 2
        count -= 1
        if w(pos) == -1:
            count -= 2
            polys.append(cur)
            pos += 2
            x0, y0 = w(pos), w(pos + 1)
            pos += 2
            cur = [(x0, y0)]
    polys.append(cur)
    pos -= 2
    nseeds = w(pos); pos += 1
    seeds = []
    for _ in range(nseeds):
        seeds.append((w(pos), w(pos + 1))); pos += 2
    return polys, lines, seeds, nseeds


def bresenham(plane, x0, y0, x1, y1):
    """exact port of $14e3e onto a [200][320] bool array"""
    dx = abs(x0 - x1)
    dy = abs(y0 - y1)
    if not (dy < dx):          # y-major (also |dx|==|dy|)
        if not (y0 < y1):
            y0, y1 = y1, y0
            x0, x1 = x1, x0
        d3 = x0 - x1
        x, y = x0, y0
        err = dy >> 1
        while True:
            plane[y][x] = True
            err += dx
            if not (err < dy):
                err -= dy
                x += -1 if d3 >= 0 else 1
            y += 1
            if y > y1:
                break
    else:
        if not (x0 < x1):
            x0, x1 = x1, x0
            y0, y1 = y1, y0
        d3 = y0 - y1
        x, y = x0, y0
        err = dx >> 1
        while True:
            plane[y][x] = True
            err += dy
            if not (err < dx):
                err -= dx
                y += 1 if d3 < 0 else -1
            x += 1
            if x > x1:
                break


def flood(plane, sx, sy):
    st = [(sx, sy)]
    while st:
        x, y = st.pop()
        if not (0 <= x < 320 and 0 <= y < 200) or plane[y][x]:
            continue
        x1 = x
        while x1 >= 0 and not plane[y][x1]:
            x1 -= 1
        x2 = x + 1
        while x2 < 320 and not plane[y][x2]:
            x2 += 1
        plane[y][x1 + 1:x2] = True
        for yy in (y - 1, y + 1):
            if 0 <= yy < 200:
                for xx in range(x1 + 1, x2):
                    if not plane[yy][xx]:
                        st.append((xx, yy))


def ram_plane(r, k):
    base = r.gl(-94) + 8000 * k
    raw = np.frombuffer(r.bytes(base, 8000), dtype=np.uint8).reshape(200, 40)
    return np.unpackbits(raw, axis=1).astype(bool)


if __name__ == '__main__':
    snap = sys.argv[1] if len(sys.argv) > 1 else sscfg.SNAP_RACE
    track = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    r = Ram(snap)
    polys, lines, seeds, ns = decode(r, track)
    print('polylines:', [len(p) for p in polys], 'line segments', len(lines), 'seeds', seeds)
    pl = np.zeros((200, 320), dtype=bool)
    for (a, b) in lines:
        bresenham(pl, a[0], a[1], b[0], b[1])
    lineonly = pl.copy()
    for (sx, sy) in seeds:
        flood(pl, sx, sy)
    ref = ram_plane(r, 1)
    diff = int((pl != ref).sum())
    print('plane1 rebuilt vs RAM: %d/64000 pixels equal (%d differ)' % (64000 - diff, diff))
    # the line pixels alone vs RAM-edge check: every drawn line pixel is set in RAM
    print('drawn line pixels set in RAM plane: %d/%d' % (int((lineonly & ref).sum()), int(lineonly.sum())))
    img = np.zeros((200, 320, 3), dtype=np.uint8) + 255
    img[ref] = (90, 90, 90)
    img[lineonly] = (220, 30, 30)
    for (sx, sy) in seeds:
        img[max(sy - 2, 0):sy + 3, max(sx - 2, 0):sx + 3] = (0, 120, 255)
    Image.fromarray(img).resize((640, 400), Image.NEAREST).save(os.path.join(OUT, 'walls_vector_track%d.png' % (track + 1)))
