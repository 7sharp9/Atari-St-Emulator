"""pre_winner.py - race from data/prerace_k.snap (human idle) to the entry of the WINNER'S CIRCLE routine $1a4ca and
snapshot it (data/pre_winner.snap) for winner_diff.py.

    cd M68000 && python3 reversing/supersprint/py/ai_econ/pre_winner.py
"""
from aiutil import *
r = Repl2(os.path.join(DATA, 'prerace_k.snap'))
out, regs = r.cmd('bp 1a4ca 60000000')
print([l for l in out if 'reak' in l or 'gave' in l])
r.cmd('snap %s' % os.path.join(DATA, 'pre_winner.snap'))
print('laps', r.a4w(-3906), 'chk', r.a4w(-3850), 'tiles', r.a4w(-3842), 'drone', r.a4w(-3914), 'timer', r.a4w(-8072, 1))
print('lap times', r.a4w(-3946, 16))
print('record -8066', r.a4w(-8066, 8), 'R', r.a4w(-1748, 1))
r.close()
