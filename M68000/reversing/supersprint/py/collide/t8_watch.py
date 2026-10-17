"""t8_watch.py - who writes map offset +1234..+1238 ( [-4940(A4)]+234.. ) on Track 8 after $15550 has overrun the map; run from race_7 ($beb2) to the first $df18."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'reversing', 'supersprint', 'py', 'physics'))
import pl
pl.OUT = os.path.join(pl.sscfg.WORK, 'agents', 'collide')
from difflib_ss import *
h = Harness(sys.argv[1]); r = h.snap_ram(); mb = r.gl(-1910); print('map %x buf %x byte@+1234=%02x' % (mb, r.gl(-4940), r.u8(mb + 1234)))
h.cmd('watch %x 8' % (mb + 1232))
out, _ = h.cmd('bpc df18 1 8000000')
print('\n'.join(l for l in out if 'WATCH' in l)[:3000])
r = h.snap_ram(); print('at df18: byte@+1234=%02x' % r.u8(mb + 1234))
h.close()
