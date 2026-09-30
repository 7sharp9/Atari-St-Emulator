"""Render every Super Sprint track (and the three non-race tilemaps) to PNG from SUPER.DAT + INIT.DAT only.

outputs (agents/tracks/png/):
    track_N.png            native 320x200, race palette (INIT.DAT -6078(A4)), no HUD text labels (rows 0-5 are painted by the HUD)
    track_N_overlay.png    2x with: racing-line lanes (even cars magenta, odd cars cyan), start grid (red), wrench/object
                           candidate cells (yellow), gate sprites (orange), tripwire cells (attribute bit 7, blue) and lap checkpoint cells 1-4 (white boxes)
    track_N_attr.png       2x with the 40x25 surface-attribute map coloured by value
    screen_title.png / screen_winners_circle.png / screen_select_wheel.png   tilemaps 8, 9, 10
    index_sheet.png        8 tracks + 3 screens
"""
import sys, struct
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from tkcommon import *
import trackrender as TR, trackdata as TD, trackpath as TP, attrmap as AM
import numpy as np
from PIL import ImageDraw

RACE_PAL = None
def race_pal(g):
    return struct.unpack('>16H', g.init[-6078])

def start_grid(g, t):
    w = struct.unpack('>32h', g.init[-1262])[4*t:4*t+4]      # X, Y0, dY, heading
    return [(w[0], w[1] + c * w[2], w[3]) for c in range(4)]

def spawn_cells(g, t):
    b = g.init[-1614][40*t:40*t+40]
    return [(b[2*k], b[2*k+1]) for k in range(20)]            # (col, row) in 8x8 cells

def gates(g, t):
    n = struct.unpack('>8H', g.init[-1294])[t]
    offs = struct.unpack('>8H', g.init[-1278])
    return [(offs[t + i] % 160 * 2, offs[t + i] // 160) for i in range(n)]   # (x px, y px) of the gate sprite, 160 B/row

def bg_image(g, t, pal):
    return idx_to_img(planar_to_idx(TR.build_bg(g, t)), pal)

def overlay(g, t, pal):
    im = bg_image(g, t, pal).resize((640, 400), Image.NEAREST).convert('RGB')
    d = ImageDraw.Draw(im, 'RGBA')
    m = AM.attr_map(t)
    for cy in range(25):
        for cx in range(40):
            v = m[cy * 40 + cx]
            if v & 0x80:
                d.rectangle([cx*16, cy*16, cx*16+15, cy*16+15], fill=(0, 80, 255, 70))      # tripwire strips (attr bit 7)
            if (v & 3) == 2 and (v & 0x7c):                                                  # lap checkpoint strips n=(v>>2)&7
                d.rectangle([cx*16, cy*16, cx*16+15, cy*16+15], outline=(255, 255, 255, 255))
                d.text((cx*16+5, cy*16+2), str((v >> 2) & 7), fill=(255, 255, 0, 255))
    for car, col in ((0, (255, 0, 255, 255)), (1, (0, 255, 255, 255))):
        for i, (a, b) in [(s[0], (s[1], s[2])) for s in TP.lane_segments(t, car)]:
            d.line([a[0] / 4, a[1] / 4, b[0] / 4, b[1] / 4], fill=col, width=2)   # world/8 = px, x2 for the 2x image
            d.ellipse([a[0]/4-2, a[1]/4-2, a[0]/4+2, a[1]/4+2], fill=(255, 255, 255, 255))
    for c, r in spawn_cells(g, t):
        d.rectangle([c*16+4, r*16+4, c*16+12, r*16+12], outline=(255, 255, 0, 255))
    for x, y, h in start_grid(g, t):
        d.rectangle([x*2-3, y*2-3, x*2+3, y*2+3], fill=(255, 0, 0, 255))
    for x, y in gates(g, t):
        d.rectangle([x*2, y*2, x*2+31, y*2+15], outline=(255, 140, 0, 255), width=2)
    return im

def attr_image(g, t, pal):
    import colorsys
    base = np.array(bg_image(g, t, pal)).astype(float)
    m = AM.attr_map(t); vals = sorted(set(m) - {0})
    cols = {v: tuple(int(255 * c) for c in colorsys.hsv_to_rgb(i / max(1, len(vals)), 1, 1)) for i, v in enumerate(vals)}
    for cy in range(25):
        for cx in range(40):
            v = m[cy * 40 + cx]
            if v: base[cy*8:cy*8+8, cx*8:cx*8+8] = 0.4 * base[cy*8:cy*8+8, cx*8:cx*8+8] + 0.6 * np.array(cols[v])
    im = Image.fromarray(base.astype('uint8')).resize((960, 600), Image.NEAREST)
    d = ImageDraw.Draw(im)
    for cy in range(25):
        for cx in range(40):
            v = m[cy * 40 + cx]
            if v and v != 128: d.text((cx*24+2, cy*24+6), '%x' % v, fill=(255, 255, 255))
    return im

if __name__ == '__main__':
    g = TR.Gfx(); pal = race_pal(g)
    thumbs = []
    for t in range(8):
        im = bg_image(g, t, pal); im.save(out('png', 'track_%d.png' % (t + 1)))
        overlay(g, t, pal).save(out('png', 'track_%d_overlay.png' % (t + 1)))
        attr_image(g, t, pal).save(out('png', 'track_%d_attr.png' % (t + 1)))
        thumbs.append(im)
    # non-race screens: palettes are the ones the game applies with its raster splits; the first band's palette is used
    screens = [('screen_title', 8, struct.unpack('>16H', g.init[-5492])),
               ('screen_winners_circle', 9, struct.unpack('>16H', g.init[-5918][:32])),
               ('screen_select_wheel', 10, pal)]
    for nm, m, p in screens:
        im = idx_to_img(planar_to_idx(g.tiles(m)), p); im.save(out('png', nm + '.png')); thumbs.append(im)
    W, H = 320, 200
    sheet = Image.new('RGB', (W * 4, H * 3), (0, 0, 0))
    d = ImageDraw.Draw(sheet)
    names = ['TRACK %d' % (i + 1) for i in range(8)] + ['tilemap 8 (title)', 'tilemap 9 (winners circle)', 'tilemap 10 (select wheel)']
    for i, im in enumerate(thumbs):
        sheet.paste(im, ((i % 4) * W, (i // 4) * H))
        d.text(((i % 4) * W + 150, (i // 4) * H + 1), names[i], fill=(255, 255, 0))
    sheet.save(out('png', 'index_sheet.png'))
    print('wrote', sorted(os.listdir(os.path.dirname(out('png', 'x')))))
