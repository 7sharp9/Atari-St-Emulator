import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'reversing', 'supersprint', 'py', 'physics'))
import pl
pl.OUT = os.path.join(pl.sscfg.WORK, 'agents', 'collide')
from difflib_ss import *
h=Harness(sys.argv[1]); h.run_to(0xdf18,1,8000000)
r=h.snap_ram(); base=r.gl(-94)+16000+7*40+34
print('watch at %x'%base)
out,_=h.cmd('watch %x 6'%base)
out,_=h.cmd('s %d'%int(sys.argv[2]))
print('\n'.join(l for l in out if 'WATCH' in l.upper() or 'watch' in l)[:3000])
h.close()
