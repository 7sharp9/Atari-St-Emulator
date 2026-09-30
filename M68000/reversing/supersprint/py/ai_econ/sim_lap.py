"""sim_lap.py - lap times of an undisturbed drone from the reconstructed per-car update (drone_model.eaea) alone, compared with the
frame stamps of a real race (data/pre_winner.log: slot 3 cap 72: 508/506/506/506; slot 0 cap 60: 620/612/612; slot 2 cap 68:
539/535/535; the stamp of lap 1 includes the start-grid transient).

The simulation uses only: the waypoint table + direction tables read from the snapshot RAM, the start values the initialiser
$be40 gives a drone (wp=0, speed=10*slot, div=40, cap=60-4T+4*slot+R, place() at wp 0) and eaea() once per frame.
"""
import drone_model as dm
from aiutil import *
sys.path.insert(0, os.path.join(sscfg.R, 'tools'))
from disassemble import ram_from_snap

ram = ram_from_snap(os.path.join(DATA, 'prerace_k.snap'))
LO, HI = A4 - 4200, A4 - 3600


def build(slot, cap):
    base = {a: 0 for a in range(LO, HI)}
    for a in range(A4 - 1840, A4 - 1816):
        base[a] = ram[a]
    tbl = int.from_bytes(ram[A4 - 4084:A4 - 4080], 'big')
    for a in range(A4 - 4118, A4 - 4086):
        base[a] = ram[a]
    for a in range(A4 - 4150, A4 - 4118):
        base[a] = ram[a]
    for a in range(A4 - 4084, A4 - 4074):
        base[a] = ram[a]
    for a in range(tbl, tbl + 84 * 8 + 16):
        base[a] = ram[a]
    m = dm.Mem(base)
    return m


def lap_frames(slot, cap, laps=4, maxframes=6000):
    m = build(slot, cap)
    A = lambda off: dm.arr(off, slot)
    m.ww(A(-3882), 40)
    m.ww(A(-3874), cap)
    m.ww(A(-3730), 10 * slot)
    m.ww(A(-3802), 0)
    dm.place(m, slot, 0)
    # carry the overlay forward: re-base memory each frame so Mem.delta stays small
    stamps, wp_prev, frame, nlap = [], 0, 0, 0
    while frame < maxframes and nlap < laps:
        dm.eaea(m, slot)
        m.base.update({a: v for a, v in m.w.items()})
        m.w.clear()
        frame += 1
        wp = m.rw(A(-3802))
        if wp < wp_prev and wp == 0:
            nlap += 1
            stamps.append(frame)
        elif wp == 0 and wp_prev != 0:
            nlap += 1
            stamps.append(frame)
        wp_prev = wp
    return stamps


if __name__ == '__main__':
    for slot, cap, meas in ((3, 72, [508, 506, 506, 506]), (0, 60, [620, 612, 612]), (2, 68, [539, 535, 535])):
        st = lap_frames(slot, cap, laps=len(meas))
        d = [st[0]] + [st[i] - st[i - 1] for i in range(1, len(st))]
        print('slot %d cap %d: simulated lap frames %s   measured (race) %s' % (slot, cap, d, [meas[0]] + [meas[i] - 0 for i in range(1, len(meas))]))
