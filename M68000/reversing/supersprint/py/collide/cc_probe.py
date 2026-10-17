import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'reversing', 'supersprint', 'py', 'physics'))
import pl
pl.OUT = os.path.join(pl.sscfg.WORK, 'agents', 'collide')
from difflib_ss import *
h=Harness(sys.argv[1]); h.run_to(0xdf18,1,8000000)
d,j,o=h.callcap(0x13b34)
print(o, list(j.keys()), {k:j[k] for k in j if k!='mem'})
h.close()
