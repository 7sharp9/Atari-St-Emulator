"""overlay_shot.py - draw the Track 1 waypoint polylines (two lanes) and the sampled drone positions on a real race frame.

Needs data/race_frame.png (tools/snap_render.py ss_prep.snap) and data/paths_idle.json (record_paths.py).  World units / 8 = screen
pixels of the 320x200 playfield.  Output data/track1_waypoints_overlay.png (x3): lane A (even records, used by odd slots 1,3)
cyan, lane B (odd records 13,15,17,19 / 65,67,69,71,73, used by even slots 0,2) green, flagged pseudo-records omitted;
waypoint vertices white; drone samples red/yellow/orange for slots 0/2/3.
"""
import json
from PIL import Image, ImageDraw
from aiutil import *
sys.path.insert(0, os.path.join(sscfg.R, 'tools'))
from disassemble import ram_from_snap
ram = ram_from_snap(os.path.join(DATA, 'prerace_k.snap'))
W = lambda a: struct.unpack('>h', ram[a:a + 2])[0]
tbl = struct.unpack('>I', ram[A4 - 4084:A4 - 4080])[0]
cnt = W(A4 - 4076)
dx = [W(A4 - 4118 + 2 * i) for i in range(16)]
dy = [W(A4 - 4150 + 2 * i) for i in range(16)]
rec = lambda i: [W(tbl + 8 * i + 2 * k) for k in range(4)]
S = 3
im = Image.open(os.path.join(DATA, 'race_frame.png')).convert('RGB').resize((320 * S, 200 * S), Image.NEAREST)
dr = ImageDraw.Draw(im)
for i in range(cnt):
    x, y, d, h = rec(i)
    if (x, y, d, h) == (0, 0, 0, 0) or h & ~0xF:
        continue
    h &= 15
    ex, ey = x + d * dx[h], y + d * dy[h]
    col = (0, 255, 255) if i % 2 == 0 else (0, 255, 0)
    dr.line([x / 8 * S, y / 8 * S, ex / 8 * S, ey / 8 * S], fill=col, width=1)
    dr.ellipse([x / 8 * S - 2, y / 8 * S - 2, x / 8 * S + 2, y / 8 * S + 2], outline=(255, 255, 255))
rows = json.load(open(os.path.join(DATA, 'paths_idle.json')))
cols = {0: (255, 60, 60), 2: (255, 255, 0), 3: (255, 150, 0)}
for r in rows[::2]:
    for car in (0, 2, 3):
        if r['spd'][car]:
            dr.point((r['px'][car] / 8 * S, r['py'][car] / 8 * S), fill=cols[car])
im.save(os.path.join(DATA, 'track1_waypoints_overlay.png'))
print('ok')
