"""Collision-mask source: outline polylines ($14e3e Bresenham into a 1bpp plane) + seed fill ($14fdc), from SUPER.DAT only.
   Verified against the live plane at -94(A4)+8000 after the game's own $15884 ran."""
import sys; sys.path.insert(0,'.')
from tkcommon import *
import trackdata as TD
import numpy as np

def line1(pl, x0, y0, x1, y1):
    """$14e3e: y-major if |dy| >= |dx| else x-major; sets bit (0x8000>>(x&15)) in a 40 B/row 1bpp plane (here a 200x320 bool array)"""
    dx, dy = abs(x0 - x1), abs(y0 - y1)
    if dy >= dx:
        if y0 > y1: x0, y0, x1, y1 = x1, y1, x0, y0
        right = (x0 - x1) < 0; err = dy >> 1; x = x0
        for y in range(y0, y1 + 1):
            if 0 <= x < 320 and 0 <= y < 200: pl[y, x] = True
            err += dx
            if err >= dy:
                err -= dy; x += 1 if right else -1
    else:
        if x0 > x1: x0, y0, x1, y1 = x1, y1, x0, y0
        down = (y0 - y1) < 0; err = dx >> 1; y = y0
        for x in range(x0, x1 + 1):
            if 0 <= x < 320 and 0 <= y < 200: pl[y, x] = True
            err += dy
            if err >= dx:
                err -= dx; y += 1 if down else -1

def outline_plane(track):
    pl = np.zeros((200, 320), bool)
    lines, seeds = TD.outline(track)
    for ln in lines:
        for a, b in zip(ln, ln[1:]): line1(pl, a[0], a[1], b[0], b[1])
    return pl, seeds

def fill(pl, seeds):
    pl = pl.copy()
    for sx, sy in seeds:
        st = [(sx, sy)]
        while st:
            x, y = st.pop()
            if not (0 <= x < 320 and 0 <= y < 200) or pl[y, x]: continue
            x0 = x
            while x0 > 0 and not pl[y, x0 - 1]: x0 -= 1
            x1 = x
            while x1 < 319 and not pl[y, x1 + 1]: x1 += 1
            pl[y, x0:x1 + 1] = True
            for yy in (y - 1, y + 1):
                if 0 <= yy < 200:
                    for xx in range(x0, x1 + 1):
                        if not pl[yy, xx]: st.append((xx, yy))
    return pl

def plane_from_ram(ram, addr):
    b = np.frombuffer(bytes(ram[addr:addr + 8000]), dtype='u1').reshape(200, 40)
    return np.unpackbits(b, axis=1).astype(bool)

if __name__ == '__main__':
    for t in map(int, sys.argv[1:] or [0]):
        ram = load_snap(out('snaps', 'race_%d.snap' % t))
        pl, seeds = outline_plane(t)
        full = fill(pl, seeds)
        live = plane_from_ram(ram, 0x61436 + 8000)
        print('track %d: outline+fill vs live plane(-94+8000): %d/%d equal; set px py=%d live=%d' %
              (t, int((full == live).sum()), full.size, int(full.sum()), int(live.sum())))
