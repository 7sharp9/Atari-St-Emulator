"""carcar_trace.py - live car-to-car contact. Cars 1 (human, poked) and 0 (drone, poked, stunned so that it does not snap back onto its waypoint rail) are put 4 px apart on the top straight with
(a) headings that differ by < 5 (shove; identical headings pass through each other) and (b) opposite headings at speed >= 60 (head-on spin). Logs per frame: X, HEAD, SPD, BUMP, TURN, F1, VX.
usage: carcar_trace.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pl import *
import ssport as P

def run(label, pokes, frames=34):
    h = Harness(sscfg.SNAP_RACE)
    h.cmd('kbd fe 80'); h.cmd('s 300')
    h.run_to(0xdf18, 1)
    for off, vals in pokes.items():
        poke_arr(h, off, vals)
    print('==', label)
    print('frame |  car0: X  HEAD SPD BUMP TURN  F1   VX |  car1: X  HEAD SPD BUMP TURN  F1   VX')
    for f in range(frames):
        h.run_to(0xdf18, 1)
        m = P.Mem(h.snap_ram().b)
        print('%5d | %11d %4d %3d %4d %4d %4x %4d | %11d %4d %3d %4d %4d %4x %4d' % (
            f, m.a(P.X, 0), m.a(P.HEAD, 0), m.a(P.SPD, 0), m.a(P.BUMP, 0), m.a(P.TURN, 0), m.au(P.F1, 0), m.a(P.VX, 0),
            m.a(P.X, 1), m.a(P.HEAD, 1), m.a(P.SPD, 1), m.a(P.BUMP, 1), m.a(P.TURN, 1), m.au(P.F1, 1), m.a(P.VX, 1)))
    h.close()

def place(x0, x1, h0, h1, s0, s1, y=40):
    base = {P.X: [x0, x1, 200, 250], P.Y: [y, y + 2, 120, 150], P.HEAD: [h0, h1, 4, 4], P.TGT: [h0, h1, 4, 4], P.SPD: [s0, s1, 68, 72],
            P.QX: [8 * x0, 8 * x1, 1600, 2000], P.QY: [8 * y, 8 * (y + 2), 960, 1200], P.PX: [8 * x0, 8 * x1, 1600, 2000], P.PY: [8 * y, 8 * (y + 2), 960, 1200],
            P.VX: [0, 0, 0, 0], P.VY: [0, 0, 0, 0], P.STUN: [60, 0, 60, 60], P.TURN: [0] * 4, P.F1: [0] * 4, P.BUMP: [0] * 4, P.FLAG: [0] * 4, P.WP: [34, 0, 48, 52]}
    return base

run('headings differ by 1 (car0 east, car1 south-east): shove', place(100, 104, 4, 5, 50, 40), 40)
run('opposite headings (east vs west) at speed >= 60: head-on spin', place(100, 106, 4, 12, 62, 70), 40)
