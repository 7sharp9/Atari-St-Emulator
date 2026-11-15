"""Routes from the Croolis land screen (q16_d.snap) to the contact setup $d8c8, against a no-input control.
  esc      : left click on "land" (187,16), 8M steps of flight, ESC (kbd 01) held 200,000 steps (> the 60,000-step
             flight tick), released, then to a total of 18.2M steps after the click. No poke.
  control  : same click, same 18.2M steps, no key.
  landing  : from fly2_landing.snap (the landing ravine reached by mouse steering alone, fly2.py), poke the flight's own
             state $110f6 (the ravine row counter, tested by $10ce8) to $ffff, 3M steps. LABELLED POKE.
  landctl  : the same snapshot, no poke, 12M steps.
Counts are `hits` per address summed over the run. Run from M68000/:  uv run python reversing/captainblood/py/canyon/routes.py <arm>"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from repl import Repl
W = 'scratchpad/captainblood/canyon'
ADDRS = 'd8c8 d840 db16 10d14 10d42 11568 11222 10c50 10b8a'
def hits(r, n):
    out = r.cmd(f'hits {n} {ADDRS}')
    return {l.split()[0]: int(l.split()[1]) for l in out.splitlines() if l.strip().startswith('$0')}
def add(a, b):
    for k, v in b.items(): a[k] = a.get(k, 0) + v
arm = sys.argv[1]
tot = {}
if arm in ('esc', 'control'):
    r = Repl('scratchpad/captainblood/q16_d.snap')
    x, y = r.w(0xc6ce, 2), r.w(0xc6d0, 2); dx, dy = 187 - x, 16 - y; lines = []
    while dx or dy:
        sx = max(-100, min(100, dx)); sy = max(-100, min(100, dy)); lines += [f'mouse move {sx} {sy}', 's 30000']; dx -= sx; dy -= sy
    lines += ['s 100000', 'mouse down l', 's 40000', 'mouse up l']
    r.cmd(*lines)
    add(tot, hits(r, 8_000_000))
    if arm == 'esc':
        r.cmd('kbd 01'); add(tot, hits(r, 200_000)); r.cmd('kbd 81'); add(tot, hits(r, 10_000_000))
    else:
        add(tot, hits(r, 10_200_000))
else:
    r = Repl(f'{W}/fly2_landing.snap')
    print('start f6', r.w(0x110f6, 2), 'cb', hex(r.w(0x10a86, 4)))
    if arm == 'landing': r.cmd('ww 110f6 ffff')
    add(tot, hits(r, 12_000_000))
print(arm, tot, 'hit table', hex(r.w(0xd586, 4)))
r.snap(f'{W}/routes_{arm}.snap'); r.close()
