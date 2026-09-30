"""Record the drone cars' per-frame state for a whole lap on track T from agents/tracks/snaps/race_T.snap
(a live race, one stationary human player) and check it against the racing line decoded from SUPER.DAT.
usage: drone_lap.py T [frames]     -> data/drone_T.csv   (frame, car, X, Y, wp, heading, speed, flags)
"""
import sys; sys.path.insert(0,'.')
from tkcommon import *
import struct

BASE = -4200; LEN = 620          # window A4-4200 .. A4-3580 covers every per-car array we need
def off(o): return o - BASE

def record(T, frames=1500, step=12000, warm=3000000):
    r = Repl(out('snaps', 'race_%d.snap' % T))
    r.cmd('s %d' % warm)                                 # countdown
    rows = []
    for f in range(frames):
        r.cmd('s %d' % step)
        b = r.mem(A4 + BASE, LEN)
        w = lambda o, i: struct.unpack('>h', b[off(o) + 2*i: off(o) + 2*i + 2])[0]
        for car in range(4):
            rows.append((f, car, w(-3690, car), w(-3698, car), w(-3802, car), w(-3706, car), w(-3730, car), w(-3914, car),
                         w(-3778, car), w(-3810, car)))
    r.close()
    return rows

if __name__ == '__main__':
    T = int(sys.argv[1]); frames = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
    rows = record(T, frames)
    p = out('data', 'drone_%d.csv' % T)
    with open(p, 'w') as fh:
        fh.write('frame,car,x,y,wp,heading,speed,droneflag,edge,stun\n')
        for row in rows: fh.write(','.join(map(str, row)) + '\n')
    print('wrote', p, len(rows))
