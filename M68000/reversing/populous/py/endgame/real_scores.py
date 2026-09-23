"""real_scores.py - score_ref.score() against every real end state kept in this dir.
Each pair <tag>_entry.snap (stopped at $1c858 entry, lost argument read from 4(A7)) and
<tag>_score.snap (the click wait): 7 rows + $36cea per state."""
from eg import *
import score_ref as S
TAGS = {'win': 'late4, evil wiped (poke)', 'lose': 'late4, human wiped (poke)', 'arm': 'late4 + Armageddon, natural loss',
        'armwin': 'late4 + Armageddon, human x40 / evil /20, natural win', 'w2470': 'world 2470 (typed WEAVUSPERT), evil wiped',
        'surr': 'game_start, GAME SETUP > SURRENDER THIS GAME', 'clost': 'custom boot, human wiped'}
good = tot = 0
for t, what in TAGS.items():
    e = OUT + '/%s_entry.snap' % t
    r = regs(repl(e, ['r']))
    m0, m1 = ram(e), ram(OUT + '/%s_score.snap' % t)
    assert r['PC'] == 0x1c858
    lost = w(m0, r['A7'] + 4)
    rows, sc, btn = S.score(m0, lost)
    real = [rowtext(m1, k) for k in range(7)]
    n = sum(a == b for a, b in zip(rows, real)) + (sc == S.s32(l(m1, SCORE)))
    good += n; tot += 8
    print('%-7s lost=%d score=%-6d %d/8  %s' % (t, lost, sc, n, what))
print('real_scores: %d/%d fields over %d real end states' % (good, tot, len(TAGS)))
