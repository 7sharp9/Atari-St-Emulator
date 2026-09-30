"""f5_winner.py - A/B of the winner's-circle F-key hook at $1ad40 from snap/pre_winner.snap.
   For each case: inject key(s) (make only, held), run to $1ad44 (D0 = key returned by the poller), run to $1ad80, read
   -2(A6) (animation index) and -9064/-9062(A4) (animation-3 frame durations)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
SNAP = os.path.join(AGENT, 'snap', 'pre_winner.snap')
cases = [('no key', None), ('F5 held', ['3f']), ('F6 held', ['40']), ('F4 held', ['3e']), ('F5 tap before poll (make+break)', 'tap5')]
for tag, k in cases:
    res = []
    for trial in range(1 if k is None or k == 'tap5' else 1):
        r = R(sscfg.SNAP_RACE if False else SNAP)
        if k == 'tap5':
            r.cmd('kbd 3f'); r.cmd('s 60000'); r.cmd('kbd bf')
        elif k:
            r.cmd('kbd ' + ' '.join(k)); r.cmd('s 60000')
        out, g = r.cmd('u 1ad44 30000000')
        d0 = g['D0'] & 0xffff
        out, g = r.cmd('u 1ad80 2000')
        a6 = g['A6']
        anim = r.w16(a6 - 2)
        d = r.g16(-9064); e = r.g16(-9062)
        cell = r.g8(-4802 + 0x3f)
        print('%-32s poll D0=%d  anim(-2(A6))=%d  -9064=%d -9062=%d  F5cell=%02x' % (tag, d0, anim, d, e, cell))
        r.close()
