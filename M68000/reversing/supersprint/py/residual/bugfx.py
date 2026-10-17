"""Audible effect of the missing rts at $13308 (channel C envelope advanced twice per sequencer step): buggy Driver vs FixedDriver
over every script entry the game can start, plus the three unreferenced ones.  Output: out/bugfx.txt and out/bugfx_*.wav (fixed renders)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rcommon import *
import numpy as np
from tune import *

ALL = [('A_0', [(0, 0), (1, 0)]), ('B_316', [(0, 316), (1, 316)]), ('C_28', [(0, 28)]), ('D_166', [(0, 166)]), ('E_88', [(0, 88)]),
       ('F_180', [(0, 180)]), ('G_302', [(0, 302)]), ('H_14', [(0, 14)]), ('I_74', [(0, 74)]), ('J_194_208_222', [(0, 194), (1, 208), (2, 222)]),
       ('K_242', [(0, 242)]), ('L_272', [(0, 272)]), ('M_ch1_322', [(1, 322)]), ('N_336', [(0, 336)]), ('O_236', [(0, 236)]),
       ('P0_3398', [(0, 3398)]), ('P1_4488', [(0, 4488)]), ('P2_5302', [(0, 5302)]), ('P3_5916', [(0, 5916)]), ('P4_6794', [(0, 6794)]),
       ('Q_906', [(0, 906)]), ('R_7780', [(0, 7780)]), ('S_2580', [(0, 2580)])]
rows = []
out = open(os.path.join(OUT, 'bugfx.txt'), 'w')
def P(*a):
    s = ' '.join(str(x) for x in a); print(s); out.write(s + '\n')
P('%-16s %6s | steps where the chC volume written differs / chC writes | max |dVolC| | first diff tick | other regs differing | PCM rms(actual-fixed)/rms(actual)' % ('entry', 'sec'))
for name, ents in ALL:
    d1, l1, n1 = run(Driver, ents); d2, l2, n2 = run(FixedDriver, ents)
    n = max(n1, n2)
    d1, l1, n1 = run(Driver, ents, ticks=n); d2, l2, n2 = run(FixedDriver, ents, ticks=n)
    c1 = [(t, v) for t, ws in l1 for r, v in ws if r == 10]; c2 = [(t, v) for t, ws in l2 for r, v in ws if r == 10]
    m = min(len(c1), len(c2))
    nd = sum(1 for i in range(m) if c1[i][1] != c2[i][1]); mx = max([abs(c1[i][1] - c2[i][1]) for i in range(m)] or [0])
    first = next((c1[i][0] for i in range(m) if c1[i][1] != c2[i][1]), None)
    def other(l):
        return [(t, tuple(x for x in ws if x[0] != 10)) for t, ws in l]
    # registers other than C's volume must be identical in actual and fixed (the extra advance touches only channel C's envelope state)
    same_other = [(t, tuple(x for x in ws if x[0] != 10)) for t, ws in l1] == [(t, tuple(x for x in ws if x[0] != 10)) for t, ws in l2]
    t1 = os.path.join(OUT, '_t1.wav'); t2 = os.path.join(OUT, '_t2.wav')
    a = render(l1, n, t1, 5).astype(float); b = render(l2, n, t2, 5).astype(float)
    mm = min(len(a), len(b))
    rms = float(np.sqrt(np.mean((a[:mm] - b[:mm]) ** 2))); ref = float(np.sqrt(np.mean(a[:mm] ** 2))) or 1.0
    P('%-16s %6.2f | %4d / %4d (%s writes in the two runs) | %2d | %s | %s | %.3f' %
      (name, n / ISR_HZ, nd, m, 'same count' if len(c1) == len(c2) else '%d vs %d' % (len(c1), len(c2)), mx, first, 'none' if same_other else 'DIFFER', rms / ref))
    if name in ('Q_906', 'J_194_208_222'):
        render(l2, n2, os.path.join(OUT, 'bugfx_%s_fixed.wav' % name), 5)
        render(l1, n1, os.path.join(OUT, 'bugfx_%s_actual.wav' % name), 5)
for f in ('_t1.wav', '_t2.wav'): os.remove(os.path.join(OUT, f))
out.close()
