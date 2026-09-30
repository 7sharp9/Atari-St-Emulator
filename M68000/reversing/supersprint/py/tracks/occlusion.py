"""$15182: per-track 'foreground' rectangles from INIT.DAT -1154(A4) build a 1bpp plane (-94(A4)+16000) that is 0 where the
   background colour is in the rectangle's colour set (the pixels cars must be drawn BEHIND).  Verified against the live plane."""
import sys; sys.path.insert(0,'.')
from tkcommon import *
import trackrender as TR, numpy as np, initmap

EDGE = [0, 0x8000, 0xc000, 0xe000, 0xf000, 0xf800, 0xfc00, 0xfe00, 0xff00, 0xff80, 0xffc0, 0xffe0, 0xfff0, 0xfff8, 0xfffc, 0xfffe]

def rects(g, track):
    h = g.init[-1154]; cnt, start = h[2*track], h[2*track+1]
    return [tuple(h[16 + 6*(start+k): 16 + 6*(start+k) + 6]) for k in range(cnt)]

def occlusion(g, track, idx):
    """idx = 200x320 colour indexes of the finished background; returns bool plane (True = 1)"""
    m = np.ones((200, 320), bool)
    for x16, y, ws, hh, l0, l1 in rects(g, track):
        lut = (l1 << 8) | l0; groups = ws >> 4; edge = EDGE[ws & 15]
        def clear(gx, rows, emask):
            for r in range(rows):
                G = gx + 20 * (y + r)              # linear 16-px group number: a rect running off the right edge wraps to the next row
                yy, xg = divmod(G, 20)
                if yy >= 200: break
                x0 = xg * 16
                row = idx[yy, x0:x0+16]
                hit = np.array([(lut >> int(c)) & 1 for c in row], bool)
                if emask is not None:
                    hit &= np.array([(emask >> (15 - i)) & 1 for i in range(16)], bool)
                m[yy, x0:x0+16] = ~hit                # $15220 move.w #$ffff,(A2): each rect REPLACES the words it touches
        for gi in range(groups): clear(x16 + gi, hh, None)
        if edge: clear(x16 + groups, hh, edge)
    return m

if __name__ == '__main__':
    from collision import plane_from_ram
    g = TR.Gfx()
    for t in map(int, sys.argv[1:] or range(8)):
        idx = planar_to_idx(g.tiles(t))      # $15182 runs after $152d2 and before the scenery sprites $157ee
        m = occlusion(g, t, idx)
        ram = load_snap(out('snaps', 'race_%d.snap' % t))
        live = plane_from_ram(ram, 0x61436 + 16000)
        print('track %d: %d rects; occlusion plane vs live (-94+16000): %d/64000 equal, cleared px py=%d live=%d' %
              (t, len(rects(g, t)), int((m == live).sum()), int((~m).sum()), int((~live).sum())))
