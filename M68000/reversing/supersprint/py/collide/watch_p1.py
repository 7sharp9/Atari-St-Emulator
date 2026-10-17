"""watch_p1.py <snap> <RACE> <plane 0|1|2> <row> <byte> <steps> - who writes a collision-plane byte after a hazard placement (RACE poked at $beb2)."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'reversing', 'supersprint', 'py', 'physics'))
import pl
pl.OUT = os.path.join(pl.sscfg.WORK, 'agents', 'collide')
from difflib_ss import *
snap, R, pi, row, byte, steps = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6])
h = Harness(snap)
r0 = h.snap_ram(); h.cmd('w %x %04x%04x' % (A4 - 1748, R, r0.gu(-1746)))
h.run_to(0xdf18, 1, 8000000)
r = h.snap_ram(); a = r.gl(-94) + 8000 * pi + row * 40 + byte
print('watch %x ; hazards: oil_n %d obst_n %d roam %d' % (a, r.g(-1858), r.g(-1766), r.g(-1776)))
h.cmd('watch %x 2' % a)
out, _ = h.cmd('s %d' % steps)
ev = [l for l in out if 'WATCH' in l]
print(len(ev), 'writes'); print('\n'.join(ev[:14]))
h.close()
