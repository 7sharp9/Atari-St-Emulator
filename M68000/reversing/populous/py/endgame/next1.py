"""next1.py - click NEW GAME on a won score screen, stop at $1d0e6 entry and at the lord screen loop."""
import sys
from eg import *
from popdrive import click_lines
tag = sys.argv[1] if len(sys.argv) > 1 else 'win'
src = OUT + '/%s_score.snap' % tag
m = ram(src)
L = click_lines(sw(m, 0x24748), sw(m, 0x2474a), 160, 184)[:-3]   # up to `mouse down`: $1d0e6 follows at once
L += ['bp 1d0e6 20000000', 'snap %s/%s_next_entry.snap' % (OUT, tag), 'mouse up l',
              'bp 1d36c 80000000', 'snap %s/%s_lord.snap' % (OUT, tag)]
out = repl(src, L)
print('\n'.join(x for x in out.splitlines() if x.startswith('PC') or 'saved' in x))
