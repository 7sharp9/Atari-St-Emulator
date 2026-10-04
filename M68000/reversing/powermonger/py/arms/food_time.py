"""food_time.py: from census_groups.out, steps until each AI group's food falls below the `$68ee` score ceiling (no combat, no refill).
   steps per tick 182,000 (50M steps = 275 `$6522` calls on pm143 k0)."""
import os, statistics, sys
from load_rows import load
# usage: food_time.py [census_groups.out]; default <ARMS_WORK>/census_groups.out (ARMS_WORK env, default scratchpad/pm148/arms), made by
#   census_groups.py scratchpad/pm144/allsnaps.txt > census_groups.out
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(_here, '../../../..'))
rows = load(sys.argv[1] if len(sys.argv) > 1 else os.path.join(_root, os.environ.get('ARMS_WORK', 'scratchpad/pm148/arms'), 'census_groups.out'))
SPT = 182000
out = []
for r in rows:
    if r['men'] <= 4: continue
    men, food, per, st = r['men'], r['food'], r['per'], r['st']
    drain = men // 8 + 1
    eff = per * (2 if st == 6 else 1)
    rate_idle = drain / (per * 2)     # camp: eats every 2*period ticks
    rate_move = drain / per
    d = 158                           # Chebyshev 127 (y 7 bits) + asr 2 of a signed byte (max +31)
    ceil = (d // 2) * ((men - 4) // 8 + 1) + d // 2
    ticks_c = (food - ceil) / rate_idle     # all camp (slowest)
    ticks_m = (food - ceil) / rate_move     # always eating at the unhalved period (fastest)
    out.append((ticks_m * SPT / 1e9, ticks_c * SPT / 1e9, men, ceil, per))
out.sort()
print('groups with men > 4:', len(out))
print('fastest case (no camp halving, geometry ceiling): min %.2f G, median %.2f G steps' % (out[0][0], statistics.median(x[0] for x in out)))
print('camped rate: min %.2f G, median %.2f G steps' % (min(x[1] for x in out), statistics.median(x[1] for x in out)))
print('smallest 5:', [(round(a,2), round(b,2), m, c, p) for a,b,m,c,p in out[:5]])
print('max men', max(x[2] for x in out), 'max score ceiling', max(x[3] for x in out))
