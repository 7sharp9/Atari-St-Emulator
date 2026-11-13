"""Drive the level event a negative attack descriptor raises ($10eec: 14798(A6) = 1, 15608(A6) set).
level_event.py <snap> <out_prefix> [final]
LABELLED POKES: 14798(A6) = 1 and 15608(A6) = $ffff (what $10eec writes); with 'final', also 13412(A6) = 1 (the
flag $b5a8 stores from the base build's D2, 1 at the station's final target). Then steps 60 main frames' worth
(4.8M steps) in 120k-step slices, printing every change of: mode 13564, party 26/28, 13410, 13412, 14776 (mission),
14794 (visited count), 14798, 14800, 15608, 14778, 14880; counts PC arrivals at $87d6 and $8804/$8836 with a
second fork run of the same length. Saves <out_prefix>.snap and renders <out_prefix>.png."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cap import *

s = srv(sys.argv[1]); pre = os.path.abspath(sys.argv[2]); final = len(sys.argv) > 3 and sys.argv[3] == 'final'
F = [('mode', 13564), ('x', 26), ('y', 28), ('13410', 13410), ('final13412', 13412), ('mission14776', 14776),
     ('visited14794', 14794), ('ev14798', 14798), ('msg14800', 14800), ('exit15608', 15608), ('14778', 14778),
     ('14880', 14880), ('14782', 14782)]
snapv = lambda: {n: w16(s, o) for n, o in F}
print('before', snapv())
s('poke', addr=A6 + 14798, width=2, value=1); s('poke', addr=A6 + 15608, width=2, value=0xffff)
if final:
    s('poke', addr=A6 + 13412, width=2, value=1)
print('POKE 14798=1 15608=$ffff' + (' 13412=1' if final else ''))
fk = s('fork')['id']
h = s('hits', steps=4_800_000, addrs=['$87d6', '$8804', '$8836', '$134b8', '$b122', '$90be'])
print('hits', ' '.join(f"{e['addr']}:{e['count']}@{e['first']}" for e in h['hits']))
s('restore', id=fk)
prev = snapv()
for i in range(40):
    s('step', n=120_000)
    v = snapv()
    d = {k: (prev[k], v[k]) for k in v if v[k] != prev[k]}
    if d: print(f'  +{(i + 1) * 120_000:>9d}', d)
    prev = v
print('after', prev)
s('save', path=pre + '.snap'); s('render', path=pre + '.png'); s.close()
