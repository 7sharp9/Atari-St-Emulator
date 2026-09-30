"""race_keys.py - live A/B of the in-race keys from ss_prep.snap (race just started, red car on channel 2).
   F8 = pause/unpause ($c996 poll, then the $c9c8 re-poll loop), F10 = abort the race ($c9d4: returns 1 from $be40 -> session ends),
   every other F-key and ESC/others = no effect.  Observable: entries of the per-frame routine $df18, the pause poll loop $c9c8,
   and the session-exit tail $13b30 / $13b2c."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
ADDRS = [0xdf18, 0xc996, 0xc9c8, 0xc9de, 0x13b30, 0x13a9c]
def scenario(tag, seq):
    r = R(sscfg.SNAP_RACE)
    a = Acc(r, ADDRS)
    a.run(1500000)      # let the race settle past the countdown
    base = dict(a.tot)
    marks = []
    for step in seq:
        kind = step[0]
        if kind == 'tap':
            a.press(['%02x' % step[1]], 60000)
        elif kind == 'run':
            before = dict(a.tot); a.run(step[1]); marks.append((step, {hex(k): a.tot[k] - before[k] for k in ADDRS if a.tot[k] - before[k]}))
    print(tag)
    print('   baseline 1.5M steps:', {hex(k): v for k, v in base.items() if v})
    for m in marks: print('   ', m)
    r.close()
scenario('no key', [('run', 600000), ('run', 600000)])
scenario('F8 pause, run, F8 resume', [('tap', 0x42), ('run', 600000), ('tap', 0x42), ('run', 600000)])
scenario('other keys (F1..F7,F9, ESC, keypad +/-) then run', [('tap', c) for c in (0x3b, 0x3c, 0x3d, 0x3e, 0x3f, 0x40, 0x41, 0x43, 0x01, 0x4e, 0x4a)] + [('run', 600000)])
scenario('F10 abort', [('tap', 0x44), ('run', 900000)])
