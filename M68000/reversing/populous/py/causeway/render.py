"""render.py - one PNG per gap: map before | causeway cells | map after (emulator map for gated gaps, model otherwise)."""
import os, sys, json
from PIL import Image, ImageDraw
from causelib import *
from planner import replay
S = 14
def shade(hv, walk):
    if not walk: return (40, 90, 170)
    g = 90 + min(hv, 8) * 18
    return (60, g, 60)
def panel(h, shp, box, marks=None, corners=(), path=(), sg=None):
    x0, y0, x1, y1 = box
    im = Image.new('RGB', ((x1-x0+1)*S, (y1-y0+1)*S)); d = ImageDraw.Draw(im)
    for y in range(y0, y1+1):
        for x in range(x0, x1+1):
            walk = cell_walkable(h, x, y, shp)
            hv = max(h[yy*N+xx] for xx, yy in corners_of(x, y))
            col = shade(hv, walk)
            if shp[y*64+x] == 0x2f: col = (120, 120, 120)
            d.rectangle([(x-x0)*S, (y-y0)*S, (x-x0+1)*S-1, (y-y0+1)*S-1], fill=col)
    for (x, y) in marks or []:
        d.rectangle([(x-x0)*S+3, (y-y0)*S+3, (x-x0+1)*S-4, (y-y0+1)*S-4], outline=(255, 160, 0), width=2)
    for (x, y) in corners:
        cx, cy = (x-x0)*S, (y-y0)*S
        d.ellipse([cx-4, cy-4, cx+4, cy+4], fill=(255, 40, 40), outline=(255, 255, 255))
    if sg:
        for (x, y), c in zip(sg, ((255, 255, 0), (0, 255, 255))):
            d.rectangle([(x-x0)*S+4, (y-y0)*S+4, (x-x0+1)*S-5, (y-y0+1)*S-5], fill=c)
    return im
def render(name, snap_path, clicks, start, goal, after_snap=None):
    m = ram(snap_path); h = heights(m); shp = shapes(m)
    ha, _, _ = replay(h, clicks)
    ma = after_snap and ram(after_snap)
    if ma: ha = heights(ma); shp_a = shapes(ma)
    else: shp_a = shp
    xs = [c[0] for c in clicks] + [start[0], goal[0]]; ys = [c[1] for c in clicks] + [start[1], goal[1]]
    box = (max(0, min(xs)-5), max(0, min(ys)-5), min(63, max(xs)+5), min(63, max(ys)+5))
    cells = sorted({q for c in clicks for q in corners_of(*c) if 0 <= q[0] < 64 and 0 <= q[1] < 64})
    p1 = panel(h, shp, box, sg=(start, goal))
    p2 = panel(h, shp, box, marks=cells, corners=clicks, sg=(start, goal))
    p3 = panel(ha, shp_a, box, sg=(start, goal))
    W = p1.width; im = Image.new('RGB', (3*W+20, p1.height), (20, 20, 20))
    for i, p in enumerate((p1, p2, p3)): im.paste(p, (i*(W+10), 0))
    im.save(os.path.join(DATA, name))
if __name__ == '__main__':
    rows = json.load(open(os.path.join(DATA, 'table.json')))
    def get(snap, comps):
        return next(r for r in rows if r['snap'] == snap and tuple(r['comps']) == comps)
    jobs = [('gap_g1_game_start_1-3.png', 'game_start', (1, 3), 'g1'), ('gap_g2_game_start_2-5.png', 'game_start', (2, 5), 'g2'),
            ('gap_g3_late4_2-3.png', 'late4', (2, 3), 'g3'),
            ('gap_g4_late4_1-2.png', 'late4', (1, 2), 'g4'),
            ('gap_game_start_0-3.png', 'game_start', (0, 3), None), ('gap_game_start_1-4.png', 'game_start', (1, 4), None),
            ('gap_late4_0-1.png', 'late4', (0, 1), None)]
    for fn, snap, comps, tag in jobs:
        r = get(snap, comps)
        after = os.path.join(DATA, 'snaps', tag, 'final_act.snap') if tag else None
        if after and not os.path.exists(after): after = None   # gate not run: model map
        render(fn, os.path.join(WORK, snap + '.snap'), [tuple(c) for c in r['planner']['clicks']], tuple(r['start']), tuple(r['goal']), after)
        print(fn)
