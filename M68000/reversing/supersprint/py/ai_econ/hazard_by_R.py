"""hazard_by_R.py [variants] - which hazards the race-start initialiser $be40 enables as a function of the race counter R=-1748(A4).

For `variants` (default 6) slightly different race starts (keyboard-fire hold 40000+997*i steps, so the game's RNG differs) the
snapshot at $bec0 (top of $be40's car loop) is resumed for each R in a list, R is poked, and the run continues to $c32e (after
the hazard initialisers $b22a/$b094/$a6c4/$a68a/$a8a0/$a828).  Reported per R: -1792 (hazard A flag set by $b22a), -1776 (roving
hazard flag set by $b094), -1858 (number of random hazard tiles placed by $a6c4), -1766 (number of blocking tiles placed by
$a8a0).  Static expectation: A iff (R+1)%3==0; roving iff R>3 and RNG; tiles = min(3,rand(R/6+1)); blocking = 4 iff R>=16 and rand(20)>=10.
"""
from aiutil import *

nvar = int(sys.argv[1]) if len(sys.argv) > 1 else 6
Rs = [0, 1, 2, 3, 4, 5, 6, 12, 17, 18, 30, 50]
snaps = []
for i in range(nvar):
    path = os.path.join(DATA, 'hz_%d.snap' % i)
    if not os.path.exists(path):
        r = Repl2(os.path.join(sscfg.WORK, 'ss_select.snap'))
        r.cmd('kbd 2a'); r.cmd('s %d' % (40000 + 997 * i)); r.cmd('kbd aa')
        out, regs = r.cmd('bpc bec0 1 12000000')
        assert any('hit' in l for l in out)
        r.cmd('snap %s' % path)
        r.close()
    snaps.append(path)
res = {R: [] for R in Rs}
for path in snaps:
    for R in Rs:
        r = Repl2(path)
        setwords(r, {A4 - 1748: R})
        out, regs = r.cmd('bpc c32e 1 500000')
        assert any('hit' in l for l in out), out
        res[R].append((r.a4w(-1792, 1)[0], r.a4w(-1776, 1)[0], r.a4w(-1858, 1)[0], r.a4w(-1766, 1)[0]))
        r.close()
for R in Rs:
    A = [x[0] for x in res[R]]
    B = [x[1] for x in res[R]]
    C = [x[2] for x in res[R]]
    D = [x[3] for x in res[R]]
    print('R=%2d  A(-1792)=%s roving(-1776)=%s tiles(-1858)=%s blocking(-1766)=%s   expected A=%d' % (R, A, B, C, D, 1 if (R + 1) % 3 == 0 else 0), flush=True)
