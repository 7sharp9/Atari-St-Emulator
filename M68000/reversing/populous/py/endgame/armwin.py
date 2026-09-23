"""armwin.py - natural Armageddon win on GENESIS: late4 with every human entity's strength x40
(capped 32000), every computer entity's /20 (min 1), and $3d524=1, run to the score screen.  usage: python armwin.py [tag]"""
import sys
from eg import *
tag = sys.argv[1] if len(sys.argv) > 1 else 'armwin'
src = WORK + '/late4.snap'
m = ram(src)
P = Poker(m); P.w(0x3d524, 1)
for i, e, d in entities(m):
    if d['side'] == 0 and d['str'] > 0:
        P.w(e + 4, min(32000, d['str'] * 40))
    if d['side'] == 1 and d['str'] > 0:
        P.w(e + 4, max(1, d['str'] // 20))
out = repl(src, P.flush() + ['bp 1c858 400000000', 'snap %s/%s_entry.snap' % (OUT, tag),
                             'bp 1cfe2 30000000', 'snap %s/%s_score.snap' % (OUT, tag)], timeout=20000)
print('\n'.join(x for x in out.splitlines() if 'breakpoint' in x))
