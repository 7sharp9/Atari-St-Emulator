"""race_input.py - which physical inputs drive which car in a live race (ss_prep.snap).  Per-car arrays indexed car*2 from A4:
   speed -3730, heading -3706, X -3690, Y -3698.  Channel of player i = -4810+2i (0 keyboard, 2 joystick0, 3 joystick1).
   Each trial: hold the input for HOLD steps from the same snapshot and report Δspeed/Δheading/ΔX,ΔY of cars 0..2 vs the no-input run."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
HOLD = 1200000
SNAP = sys.argv[1] if len(sys.argv) > 1 else sscfg.SNAP_RACE
def cars(r):
    return [dict(spd=r.g16(-3730 + 2*i), hd=r.g16(-3706 + 2*i), x=r.g16(-3690 + 2*i), y=r.g16(-3698 + 2*i)) for i in range(3)]
def trial(tag, pre_cmds):
    r = R(SNAP)
    r.cmd('s 20000')
    c0 = cars(r)
    for c in pre_cmds: r.cmd(c)
    r.cmd('s %d' % HOLD)
    c1 = cars(r)
    moved = ['car%d:(%+d,%+d) spd %d hd %d' % (i, c1[i]['x'] - c0[i]['x'], c1[i]['y'] - c0[i]['y'], c1[i]['spd'], c1[i]['hd']) for i in range(3)]
    print('%-34s' % tag, ' | '.join(moved))
    r.close()
r = R(SNAP)
print('players joined flags -3914..-3908:', [r.g16(-3914 + 2*i) for i in range(4)], ' channels:', [r.g16(-4810 + 2*i) for i in range(3)], ' joined(-4822):', [r.g16(-4822+2*i) for i in range(3)], '-3906:', [r.g16(-3906+2*i) for i in range(4)])
r.close()
trial('no input', [])
trial('LShift (2a) held', ['kbd 2a'])
trial('RShift (36) held', ['kbd 36'])
trial('Alt (38) held', ['kbd 38'])
trial('joystick0 fire (fe 80)', ['kbd fe 80'])
trial('joystick1 fire (ff 80)', ['kbd ff 80'])
trial('LShift + A (left)', ['kbd 2a', 'kbd 1e'])
trial('LShift + D (right)', ['kbd 2a', 'kbd 20'])
trial('LShift + Z (left)', ['kbd 2a', 'kbd 2c'])
trial('LShift + X (right)', ['kbd 2a', 'kbd 2d'])
trial('LShift + L (left)', ['kbd 2a', 'kbd 26'])
trial("LShift + ' (right)", ['kbd 2a', 'kbd 28'])
trial('LShift + Up arrow (48)', ['kbd 2a', 'kbd 48'])
trial('LShift + Left arrow (4b)', ['kbd 2a', 'kbd 4b'])
trial('joy0 fire+left (fe 84)', ['kbd fe 84'])
trial('joy0 fire+right (fe 88)', ['kbd fe 88'])
trial('joy0 up+fire (fe 81)', ['kbd fe 81'])
trial('joy0 down+fire (fe 82)', ['kbd fe 82'])
