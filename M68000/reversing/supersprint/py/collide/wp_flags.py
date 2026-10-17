"""wp_flags.py - per track, the waypoint-table records that carry control flags (0x100 fork by car parity, 0x200 gate-route `wp += -1832[t&3]`, 0x400 jump) at the first $df18."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'reversing', 'supersprint', 'py', 'physics'))
import pl
pl.OUT = os.path.join(pl.sscfg.WORK, 'agents', 'collide')
from difflib_ss import *
for t in range(8):
    h = Harness(os.path.join(pl.sscfg.WORK, 'agents', 'tracks', 'snaps', 'race_%d.snap' % t)); h.run_to(0xdf18, 1, 8000000); r = h.snap_ram()
    tb = r.gl(-4084); n = r.g(-4076); f = [r.u16(tb + 8 * i + 6) for i in range(n)]
    print('T%d: %3d records; gates(-1808)=%d; 0x100 forks %s; 0x200 gate-route %s; 0x400 jumps %s; -1832=%s' % (t + 1, n, r.g(-1808), [i for i, v in enumerate(f) if v == 0x100], [(i, hex(v)) for i, v in enumerate(f) if v & 0x200], [(i, v & 0xff) for i, v in enumerate(f) if v & 0x400], [r.g(-1832 + 2 * k) for k in range(3)]))
    h.close()
