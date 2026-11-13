"""Map region around the Phoopel lock (D0=13, D2=0, lock 4) with reachability from the entrance, door closed.
Passability is lockcensus.Grid's (open cells by $24efc's rule plus arrow edges, so lifts and shafts count)."""
import sys
import os as _os
_M = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '../../../..'))  # M68000/
sys.path.insert(0, _M + '/reversing/captive/py/mapgen/full')
import lockcensus as LC
locks, m, ab, full = LC.record_locks(13, 0)
L = locks[4]
g = LC.Grid(m)
ex = LC.w(m, 32); ent = (ex % 64, ex // 64)
D, E, W, K = L['D'], L['E'], L['W'], L['K']
reach = g.reach(ent, {D})
allreach = g.reach(ent, set())
print('lock 4:', L)
print('K == D:', K == D, '| K reachable with D closed:', K in reach, '| with D open:', K in allreach)
print('E reachable with D closed:', E in reach)
nb = [(D[0]+dx, D[1]+dy) for dx, dy in ((1,0),(-1,0),(0,1),(0,-1))]
print('door neighbours open/reachable (D closed):', [(c, g.is_open(*c), c in reach) for c in nb])
wn = [(W[0]+dx, W[1]+dy) for dx, dy in ((1,0),(-1,0),(0,1),(0,-1))]
print('wall item W neighbours open/reachable (D closed):', [(c, g.is_open(*c), c in reach) for c in wn])
print('G0 D', g.g0(*D), 'G0 E', g.g0(*E))
# arrow path from E to the entrance, first cells
pe, _ = g.arrow_path(*E)
print('arrow path E -> entrance (first 8):', pe[:8])
# uniqueness of G0 over open cells
from collections import Counter
cnt = Counter(g.g0(x, y) for y in range(32) for x in range(64) if g.is_open(x, y) and 2 <= g.g0(x, y) < 0x8000)
print('open cells with a G0 shared by another open cell:', sum(v for v in cnt.values() if v > 1), 'of', sum(cnt.values()))
print('G0 value of D shared by', cnt[g.g0(*D)], 'open cell(s)')
x0, x1, y0, y1 = 0, 16, 4, 16
print('legend: # rock, . reachable with door closed, o open but not reachable with it closed, D door+key (7,9), E prize, W wall item, @ entrance')
print('    ' + ''.join(str(x % 10) for x in range(x0, x1)))
for y in range(y0, y1):
    row = ''
    for x in range(x0, x1):
        c = (x, y)
        ch = '#' if not g.is_open(x, y) else ('.' if c in reach else 'o')
        if c == D: ch = 'D'
        elif c == E: ch = 'E'
        elif c == W: ch = 'W'
        elif c == ent: ch = '@'
        row += ch
    print(f'{y:3d} ' + row)
