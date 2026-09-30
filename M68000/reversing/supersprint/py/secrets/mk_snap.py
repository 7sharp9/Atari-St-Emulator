"""mk_snap.py SRC NAME STEPS : resume SRC, run STEPS, save agents/secrets/snap/NAME.snap"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh import *
src, name, steps = sys.argv[1], sys.argv[2], int(sys.argv[3])
r = R(src if os.path.exists(src) else getattr(sscfg, src))
r.cmd('s %d' % steps)
out, g = r.cmd('snap %s' % os.path.join(AGENT, 'snap', name + '.snap'))
print(name, 'PC=%x' % g['PC'])
r.close()
