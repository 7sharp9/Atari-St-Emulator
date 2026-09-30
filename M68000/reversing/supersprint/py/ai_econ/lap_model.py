"""lap_model.py - predict a drone's lap time (VBL frames) from the waypoint table alone and compare with the lap stamps
measured in a real race (pre_winner.log: car 3 laps 508,506,506,506; car 0: 620,612,612; car 2: 539,535,535 frames).

Model: per frame the car moves speed*dir/div = cap*dir/40 world units (drone div is forced to 40), a segment (X,Y,d,h) is d*dir
long, so it takes 40*d/cap frames independent of heading; the snap to the next record's X,Y removes overshoot only.
Lap frames = 40 * sum(d along the lane the car takes) / cap  (+ acceleration at the start, which is not in a lap>=2).
"""
from aiutil import *
from wptables import table, COUNT


def lane_walk(t, car):
    tb = table(t)
    cnt = COUNT[t]
    wp, seq = 0, []
    while True:
        seq.append(wp)
        wp = (wp + 2) % cnt
        x, y, d, h = tb[wp]
        if h == 0x100:
            wp += 3 if car % 2 == 0 else 2
        elif h & 0x200:
            wp += 2          # gate open
        elif h & 0x400:
            wp += h & 0xFF
        if wp == 0 or len(seq) > 400:
            break
    return seq, tb


if __name__ == '__main__':
    for t in range(8):
        for car in (0, 1):
            seq, tb = lane_walk(t, car)
            sd = sum(tb[i][2] for i in seq if not tb[i][3] & ~0xF)
            print('track %d car parity %d: %d records on the lane, sum d = %d -> lap frames at cap c = 40*%d/c' % (t + 1, car, len(seq), sd, sd), end='')
            if t == 0:
                for c, lab in ((60, 'car0'), (68, 'car2'), (72, 'car3')):
                    print('  c=%d: %.1f' % (c, 40 * sd / c), end='')
            print()
