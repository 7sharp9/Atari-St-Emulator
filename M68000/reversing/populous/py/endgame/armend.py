"""armend.py - end GENESIS naturally: force Armageddon ($3d524=1) in a late snapshot and run until
$db4c calls the score screen, snapshot at $1c858 entry and at its click wait.
usage: python armend.py <src.snap> <tag> [max_steps]"""
import sys
from eg import *
src, tag = sys.argv[1], sys.argv[2]
mx = int(sys.argv[3]) if len(sys.argv) > 3 else 400000000
m = ram(src)
P = Poker(m); P.w(0x3d524, 1)
out = repl(src, P.flush() + ['bp 1c858 %d' % mx, 'r', 'snap %s/%s_entry.snap' % (OUT, tag),
                             'bp 1cfe2 30000000', 'snap %s/%s_score.snap' % (OUT, tag)], timeout=20000)
print('\n'.join(x for x in out.splitlines() if 'breakpoint' in x or x.startswith('PC')))
