"""watch_diff.py SNAP LO-HI(file offsets, poisoned) ADDR LEN STEPS: run SNAP with and without LO-HI of SUPER.DAT poisoned under `watch ADDR LEN`
and print both write logs (the first lines), to attribute a stray difference to the instruction that writes it."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uc import *
snap = snapath(sys.argv[1]); lo, hi = [int(x, 16) for x in sys.argv[2].split('-')]; addr = sys.argv[3]; ln = sys.argv[4]; steps = sys.argv[5]
for poisoned in (False, True):
    r = ReplErr(snap)
    if poisoned:
        r.cmd('\n'.join('w %x abababab' % a for a in range(BUF + (lo & ~3), BUF + ((hi + 3) & ~3), 4)))
    r.cmd('watch %s %s' % (addr, ln)); r.cmd('s %s' % steps)
    e = r.err().split('\n'); r.close()
    print('poisoned' if poisoned else 'clean', len(e), 'stderr lines'); print('\n'.join(e[:12]))
