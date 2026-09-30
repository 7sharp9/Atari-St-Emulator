"""mk_race_kbd.py - from the attract snapshot start a session with the KEYBOARD player (LShift = channel 0 fire, blue car),
confirm the track with LShift, run into the race; saves snap/race_kbd.snap 1M steps after the race loop $df18 is first entered."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
r = R(sscfg.SNAP_ATTRACT)
r.cmd('s 500000')
press(r, ['2a'], 60000)
r.cmd('s 1500000')
press(r, ['2a'], 60000)
out, g = r.cmd('u df18 60000000')
print(out[1], hex(g['PC']))
r.cmd('s 1000000')
print('human flags -3914.. (0 = human):', [r.g16(-3914 + 2*i) for i in range(4)], ' channels', [r.g16(-4810 + 2*i) for i in range(3)], 'speeds', [r.g16(-3730 + 2*i) for i in range(4)])
r.cmd('snap %s' % os.path.join(AGENT, 'snap', 'race_kbd.snap'))
r.close()
