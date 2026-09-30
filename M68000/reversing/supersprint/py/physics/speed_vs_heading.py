"""speed_vs_heading.py - live measurement: distance travelled per frame at the speed cap for each of the 16 headings.
Human car (car 1), fire held, poked to cap speed + steady velocity on open road; displacement of the fixed-point position Q over frames 3..8.
Prediction: |V|/D = speed * |(dirX,dirY)| / 40 (1/8 px per frame)."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pl import *
import ssport as P
import numpy as np

h = Harness(sscfg.SNAP_RACE)
h.cmd('kbd fe 80')
h.run_to(0xdf18, 1)
ram = h.snap_ram()
raw = np.frombuffer(ram.bytes(ram.gl(-94) + 8000, 8000), dtype=np.uint8).reshape(200, 40)
road = np.unpackbits(raw, axis=1) == 0
dirx, diry = ram.arr(P.DIRX, 16), ram.arr(P.DIRY, 16)
CAP = 110


def clear_path(x, y, hd, frames=10):
    px, py = x, y
    for f in range(frames + 2):
        for dx in range(-2, 19):
            for dy in range(-2, 13):
                xx, yy = int(px) + dx, int(py) + dy
                if not (0 <= xx < 320 and 0 <= yy < 200) or not road[yy, xx]:
                    return False
        px += dirx[hd] * CAP / 40 / 8
        py += diry[hd] * CAP / 40 / 8
    return True


res = []
for hd in range(16):
    start = None
    for y in range(20, 60, 3):
        for x in range(30, 280, 5):
            if clear_path(x, y, hd):
                start = (x, y)
                break
        if start:
            break
    if not start:
        print('no clear start for heading', hd)
        continue
    x, y = start
    poke_arr(h, P.X, [0, x, 0, 0]); poke_arr(h, P.Y, [0, y, 0, 0])
    poke_arr(h, P.QX, [0, 8 * x, 0, 0]); poke_arr(h, P.QY, [0, 8 * y, 0, 0])
    poke_arr(h, P.PX, [0, 8 * x, 0, 0]); poke_arr(h, P.PY, [0, 8 * y, 0, 0])
    poke_arr(h, P.HEAD, [8, hd, 8, 8]); poke_arr(h, P.TGT, [8, hd, 8, 8])
    poke_arr(h, P.SPD, [0, CAP, 0, 0])
    vx, vy = CAP * dirx[hd], CAP * diry[hd]
    poke_arr(h, P.VX, [0, vx, 0, 0]); poke_arr(h, P.VY, [0, vy, 0, 0])
    poke_arr(h, P.VTX, [0, vx, 0, 0]); poke_arr(h, P.VTY, [0, vy, 0, 0])
    poke_arr(h, P.STUN, [0, 0, 0, 0]); poke_arr(h, P.TURN, [0, 0, 0, 0]); poke_arr(h, P.FLAG, [0, 0, 0, 0])
    poke_arr(h, P.F1, [0, 0, 0, 0]); poke_arr(h, P.TURNCNT, [0, 0, 0, 0])
    qs = []
    for f in range(9):
        h.run_to(0xdf18, 1)
        r = h.snap_ram()
        m = P.Mem(r.b)
        qs.append((m.a(P.QX, 1), m.a(P.QY, 1), m.a(P.SPD, 1), m.a(P.HEAD, 1), m.a(P.FLAG, 1), m.a(P.STUN, 1)))
    d = [math.hypot(qs[i + 1][0] - qs[i][0], qs[i + 1][1] - qs[i][1]) for i in range(2, 8)]
    pred = math.hypot(P.divs(CAP * dirx[hd], 40), P.divs(CAP * diry[hd], 40))     # per-axis DIVS truncation
    match = abs(sum(d) / len(d) - pred) < 0.01
    res.append(match)
    print('heading %2d start %s  measured %.2f  predicted %.2f  (1/8 px per frame)  state(spd,head,flag,stun) %s' % (hd, start, sum(d) / len(d), pred, qs[-1][2:]))
h.close()
print('heading speeds matching the integer model: %d/%d' % (sum(1 for x in res if x is True), 16))
