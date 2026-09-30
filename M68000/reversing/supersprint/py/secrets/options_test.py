"""options_test.py - live proof of the options screen keys ($18b54, F1 from attract; poll $18e56).
   From snap/opt.snap: F2/F3/F4 cycle the player control channel (0 keyboard -> 2 joystick0 -> 3 joystick1; channel 1 'mouse' is skipped),
   F9 toggles sound (-8068), F10 leaves the screen only if the controls are distinct.  Reads -4810/-4808/-4806 (channels) and -8068."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
SNAP = os.path.join(AGENT, 'snap', 'opt.snap')
names = {0x3c: 'F2', 0x3d: 'F3', 0x3e: 'F4', 0x3f: 'F5', 0x40: 'F6', 0x41: 'F7', 0x42: 'F8', 0x43: 'F9', 0x44: 'F10', 0x01: 'ESC', 0x3b: 'F1'}
def state(r):
    return {'ch': [r.g16(o) for o in (-4810, -4808, -4806)], 'sound': r.g16(-8068)}
def tap(a, r, code, hold=40000, after=200000):
    a.press(['%02x' % code], hold, after)
r = R(SNAP)
a = Acc(r, [0x18b54, 0x18e56, 0x1399e, 0x139ac, 0x18ffa, 0x1901e, 0x190b8])
print('start', state(r))
for code in (0x3c, 0x3c, 0x3c, 0x3c):
    tap(a, r, code); print(names[code], state(r))
for code in (0x3d, 0x3e):
    tap(a, r, code); print(names[code], state(r))
for code in (0x43, 0x43):
    tap(a, r, code); print(names[code], state(r))
for code in (0x3f, 0x40, 0x41, 0x42, 0x01, 0x3b):
    tap(a, r, code); print(names[code], '(other keys)', state(r))
# duplicates: make blue=joystick0 (2) equal to red (2)
h = {}
tap(a, r, 0x3c); print('F2 ->', state(r))       # blue 0 -> 2  (now equals red=3? no red=3): set explicitly below
print('hits so far', {hex(k): v for k, v in a.tot.items() if v})
r.close()
# duplicates + exit test, fresh process
r = R(SNAP); a = Acc(r, [0x18b54, 0x138b2, 0x190b8, 0x18ffa, 0x1901e, 0x18e56])
tap(a, r, 0x3d); print('F3 (red 2->3 => duplicate with yellow 3)', state(r))
tap(a, r, 0x44, after=1500000)
print('F10 with duplicate controls: error-message code $18ffa hit', a.tot[0x18ffa], 'times; main loop top $138b2 re-entered', a.tot[0x138b2], 'times (0 = still in options)')
a.run(6000000)
tap(a, r, 0x3d, after=400000); tap(a, r, 0x3d, after=400000); print('F3 x2 more (red 3->0->2, distinct again)', state(r))
tap(a, r, 0x44, after=3000000)
print('F10 with distinct controls: main loop top $138b2 re-entered', a.tot[0x138b2], 'times; PC=%x' % a.regs['PC'], state(r))
r.close()
