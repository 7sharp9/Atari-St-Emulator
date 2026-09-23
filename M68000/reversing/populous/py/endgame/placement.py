"""placement.py - starting walkers of $120c6 vs a model, on the built worlds of the boot snapshots.
Count per side: LEVEL b6/b7 ($22ade/$22adf) in conquest or tutorial (mode 3); otherwise 1 without
a computer opponent, else 1 + 2*(god rec +12 > 4). Side 0 takes the first flat ($0f) cells from
$80 upward, side 1 from $f80 downward; each placed walker has str 45. Score += 10*count of $3affe's side."""
import sys; sys.setrecursionlimit(100000)
from eg import *
from popgen import build_world
PW = import_popworld()
cases = [('boot_custom_built', 0, 4), ('boot_tutorial_built', 0x69bc, 5)]
for t in ('lose_retry', 'play1235', 'play1240', 'play2470', 'w2470_play0'):   # conquest worlds at $1d0c0
    wn = w(ram(OUT + '/%s.snap' % t), WORLD)
    cases.append((t, PW.level(wn)['seed'], 4))
good = tot = 0
for tag, seed, pre in cases:
    m = ram(OUT + '/%s.snap' % tag)
    wd = build_world(seed, pre)
    conq = w(m, 0x21d5e) != 0xffff
    tut = seed == 0x69bc          # mode is already cleared by $b5ea at this point; the tutorial is the $69bc world
    cnt = []
    for s in (0, 1):
        if conq or tut: n = m[0x22ade + s]
        elif not w(m, 0x219b0): n = 1
        else: n = 1 + 2 * (sw(m, GOD + 0x2e * s + 12) > 4)
        cnt.append(n)
    exp0 = [c for c in range(0x80, 0x1000) if wd.shape[c] == 0x0f][:cnt[0]]
    exp1 = [c for c in range(0xf80, 0x7f, -1) if wd.shape[c] == 0x0f][:cnt[1]]
    real0 = [d['cell'] for i, e, d in entities(m) if d['side'] == 0]
    real1 = [d['cell'] for i, e, d in entities(m) if d['side'] == 1]
    strs = {d['str'] for i, e, d in entities(m)}
    sc = 10 * cnt[w(m, HUMAN)]
    ok = [exp0 == real0, exp1 == real1, strs == {45}, l(m, SCORE) == sc]
    good += sum(ok); tot += len(ok)
    print(tag, cnt, ok, real0[:5], exp0[:5])
print('placement: %d/%d checks' % (good, tot))
