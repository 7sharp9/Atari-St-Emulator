import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
import re
def steps_to(r, cap=30000000):
    out, g = r.cmd('u df18 %d' % cap)
    m = [l for l in out if 'reached PC' in l or 'gave up' in l]
    return m[0].strip()
for tag, pre in (('no key', []), ('kbd 02 (make)', ['kbd 02', 's 30000']), ('kbd 39 (space make)', ['kbd 39', 's 30000']), ('kbd 02 then 82', ['kbd 02', 's 30000', 'kbd 82']), ('just s 30000', ['s 30000'])):
    r = R(os.path.join(AGENT, 'snap', 'prep_kbd.snap'))
    for c in pre: r.cmd(c)
    print('%-22s %s' % (tag, steps_to(r)))
    r.close()
