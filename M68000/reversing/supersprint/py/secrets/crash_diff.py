"""crash_diff.py - a held non-ESC key crashes the game in the race-start initialisation (Line-F exception, vector $2c).  Compare the set of
function entries executed in the window [7M, 9.5M] steps after the prepare-screen snapshot with and without `kbd 02` (make, no break)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
import reach
ins = reach.load()
links = [a for a, t in ins if t.startswith('link')]
res = {}
for tag, pre in (('no key', []), ('key 02 held', ['kbd 02', 's 30000'])):
    r = R(os.path.join(AGENT, 'snap', 'prep_kbd.snap'))
    for c in pre: r.cmd(c)
    r.cmd('s %d' % (7000000 - (30000 if pre else 0)))
    h, regs = hits(r, 2500000, links)
    res[tag] = {a: v for a, v in h.items() if v[0]}
    print(tag, 'functions entered:', len(res[tag]), 'PC at end', hex(regs['PC']))
    r.close()
a, b = res['no key'], res['key 02 held']
print('entered with no key but NOT with key held:', sorted(hex(x) for x in a if x not in b))
print('entered with key held but not without:', sorted(hex(x) for x in b if x not in a))
print('last function first-entered in the keyed run:', sorted(((v[1], hex(k)) for k, v in b.items()))[-6:])
