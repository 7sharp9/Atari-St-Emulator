"""retry.py - click the button on a score screen and stop after $b316(0,-1) rebuilt the world ($1d0c0).
For a lost conquest game (TRY IT AGAIN) the same world must come back: compare with build_world.
usage: python retry.py <score_tag> <out_tag>"""
import sys
from eg import *
from popdrive import click_lines
from startgame import check_world
tin, tout = sys.argv[1], sys.argv[2]
src = OUT + '/%s.snap' % tin
m = ram(src)
L = click_lines(sw(m, 0x24748), sw(m, 0x2474a), 160, 184)[:-1] + ['bp 1d0c0 80000000', 'snap %s/%s.snap' % (OUT, tout)]
out = repl(src, L)
print('\n'.join(x for x in out.splitlines() if 'breakpoint' in x))
m1 = ram(OUT + '/%s.snap' % tout)
print('world before/after', w(m, WORLD), w(m1, WORLD), check_world(m1, w(m1, WORLD))[1], 'score', l(m1, SCORE), 'ctrl you', w(m1, GOD + 6))
