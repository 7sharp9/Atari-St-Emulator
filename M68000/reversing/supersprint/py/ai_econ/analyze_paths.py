"""analyze_paths.py [paths.json]  - overlay the sampled drone positions on the waypoint polyline of Track 1.

Reads data/paths_idle.json (record_paths.py) and the waypoint table + direction tables from data/prerace_k.snap's RAM
(tools/disassemble.ram_from_snap).  For each drone sample not in a stun/spin, computes the perpendicular distance
from the car's world position (x8 units) to the segment of the waypoint it is currently steering to
(rec(wp).XY -> XY + d*dir(h)), and the along-segment fraction.  Also lists the wp sequence each drone slot visits
(lane usage by car parity) and writes data/paths_overlay.png (world/8 = screen pixels, x2 scale).
"""
import json, math
from aiutil import *
sys.path.insert(0, os.path.join(sscfg.R, 'tools'))
from disassemble import ram_from_snap

rows = json.load(open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(DATA, 'paths_idle.json')))
ram = ram_from_snap(os.path.join(DATA, 'prerace_k.snap'))
W = lambda a: struct.unpack('>h', ram[a:a + 2])[0]
tbl = struct.unpack('>I', ram[A4 - 4084:A4 - 4080])[0]
cnt = W(A4 - 4076)
dx = [W(A4 - 4118 + 2 * i) for i in range(16)]
dy = [W(A4 - 4150 + 2 * i) for i in range(16)]
rec = lambda i: [W(tbl + 8 * i + 2 * k) for k in range(4)]
print('table $%x, %d slots' % (tbl, cnt))


def seg(i):
    x, y, d, h = rec(i)
    h &= 15
    return (x, y, x + d * dx[h], y + d * dy[h])


def dist(px, py, s):
    x0, y0, x1, y1 = s
    vx, vy = x1 - x0, y1 - y0
    L2 = vx * vx + vy * vy
    if L2 == 0:
        return math.hypot(px - x0, py - y0), 0.0
    t = ((px - x0) * vx + (py - y0) * vy) / L2
    cx, cy = x0 + t * vx, y0 + t * vy
    return math.hypot(px - cx, py - cy), t


stats = {}
for car in (0, 2, 3):
    ds = []
    for r in rows:
        if r['stun'][car] > 0 or r['acc'][car] > 0 or r['spd'][car] == 0:
            continue
        i = r['wp'][car]
        if rec(i) == [0, 0, 0, 0] or rec(i)[3] & ~0xF:
            continue
        d, t = dist(r['px'][car], r['py'][car], seg(i))
        ds.append((d, t, r['t']))
    n = len(ds)
    within = sum(1 for d, t, _ in ds if d <= 8)      # 8 world units = 1 screen pixel
    within3 = sum(1 for d, t, _ in ds if d <= 3)
    # samples with -0.05 <= t <= 1.05 (car really is on its segment)
    on = sum(1 for d, t, _ in ds if -0.1 <= t <= 1.1)
    stats[car] = (n, within, within3, on, max(d for d, _, _ in ds))
    print('car %d: %d samples on rails-check; perp <= 8u (1px): %d; <=3u: %d; along-segment in [-0.1,1.1]: %d; max perp %.1f u' % ((car,) + stats[car]))

# lane usage
for car in range(4):
    seq = []
    for r in rows:
        w = r['wp'][car]
        if not seq or seq[-1] != w:
            seq.append(w)
    print('car %d (%s) wp sequence, first 64 changes: %s' % (car, 'human/idle' if car == 1 else 'drone', seq[:64]))
    lanes = {'odd-lane-13': 13 in seq, 'even-lane-12': 12 in seq, 'odd-lane-65': 65 in seq, 'even-lane-64': 64 in seq}
    print('   lane markers seen', lanes)
json.dump(stats, open(os.path.join(DATA, 'paths_stats.json'), 'w'))

# overlay png
try:
    from PIL import Image, ImageDraw
    S = 3
    im = Image.new('RGB', (2400 // 8 * S + 20, 1500 // 8 * S + 20), (20, 20, 20))
    dr = ImageDraw.Draw(im)
    for i in range(cnt):
        if rec(i) != [0, 0, 0, 0] and not rec(i)[3] & ~0xF:
            x0, y0, x1, y1 = seg(i)
            col = (90, 160, 255) if i % 2 == 0 else (90, 255, 160)
            dr.line([x0 / 8 * S, y0 / 8 * S, x1 / 8 * S, y1 / 8 * S], fill=col, width=1)
    cols = {0: (255, 80, 80), 2: (255, 255, 80), 3: (255, 160, 60), 1: (255, 255, 255)}
    for r in rows:
        for car in (0, 2, 3):
            dr.point((r['px'][car] / 8 * S, r['py'][car] / 8 * S), fill=cols[car])
    im.save(os.path.join(DATA, 'paths_overlay.png'))
    print('wrote paths_overlay.png')
except Exception as e:
    print('overlay skipped', e)
