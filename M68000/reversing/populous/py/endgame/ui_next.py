"""ui_next.py - next world reached through the real UI (score screen -> NEW GAME -> lord screen ->
CONTINUE -> briefing) vs popworld.next_world: <tag>_score.snap (old world, score) and
<tag>_brief.snap (the $1afc4 briefing wait: world -18(A6) = $3c51a, name $37e86).
Made by win1.py/armwin.py/win1.py(play2470) + next1.py + brief1.py."""
from eg import *
PW = import_popworld()
def rname(n):
    v = PW.rand1(n); return PW.A[v & 31] + PW.B[(v >> 5) & 31] + PW.C[(v >> 10) & 31]
good = 0
TAGS = ['win', 'armwin', 'w2470']
for t in TAGS:
    s, b = ram(OUT + '/%s_score.snap' % t), ram(OUT + '/%s_brief.snap' % t)
    old, sc = w(s, WORLD), l(s, SCORE)
    new, done = PW.next_world(old, sc)
    ok = w(b, WORLD) == new and cstr(b, 0x37e86) == rname(new) and b[0x22ad8:0x22ae2].hex() == PW.level(new)['raw']
    good += ok
    print('%-7s world %4d score %6d -> %4d %-10s record %s  %s' % (t, old, sc, w(b, WORLD), cstr(b, 0x37e86), PW.level(new)['rec'], ok))
print('ui_next: %d/%d' % (good, len(TAGS)))
