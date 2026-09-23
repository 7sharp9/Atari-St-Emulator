"""win1.py - win/lose GENESIS for real from a late snapshot by zeroing one side's entity
strengths; snapshots at $1c858 entry and at its click-wait loop ($1cfe2)."""
import sys
from eg import *
src = sys.argv[1] if len(sys.argv) > 1 else WORK + '/late4.snap'
kill = int(sys.argv[2]) if len(sys.argv) > 2 else 1      # side to wipe out
tag = sys.argv[3] if len(sys.argv) > 3 else 'win'
m = ram(src)
P = Poker(m)
for i, e, d in entities(m):
    print(i, d)
    if d['side'] == kill and d['str'] > 0:
        P.w(e + 4, 0)
print('pop', l(m, SIDE + 8), l(m, SIDE + 16 + 8), 'score', l(m, SCORE), 'battles', w(m, BATTLES), w(m, BATTLES + 2))
lines = P.flush() + ['bp 1c858 3000000', 'snap %s/%s_entry.snap' % (OUT, tag),
                     'bp 1cfe2 30000000', 'snap %s/%s_score.snap' % (OUT, tag)]
out = repl(src, lines)
print('\n'.join(x for x in out.splitlines() if 'PC' in x or 'bp' in x.lower() or 'snap' in x.lower())[-3000:])
