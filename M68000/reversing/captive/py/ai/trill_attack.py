"""A type-$1f creature's attack raises the level event (no poke of the event words themselves).
trill_attack.py <snap> <group_index> <steps> <out_prefix> [period]
With [period], a second LABELLED POKE sets the group's period byte +7 (the final base's generated Trill has 50).
LABELLED POKE: the lead member's type byte (+8) of the group = $1f (the only type whose attack descriptor at $10b6c
starts with a negative byte). The group must be hostile and lined up with the party (g16_adj.snap: group 16,
adjacent, facing the party). Counts $10dfa (member attack) and $10eec (negative descriptor) over <steps>, printing
every change of 14798(A6), 15608(A6), the mode 13564 and the party cell, then saves and renders."""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cap import *

s = srv(sys.argv[1]); gi, steps, pre = int(sys.argv[2]), int(sys.argv[3]), os.path.abspath(sys.argv[4])
a = A6 + 4532
for _ in range(gi):
    a += struct.unpack('>h', s.read(a + 2, 2))[0]
print('group', gi, hex(a), 'rec', s.read(a, 16).hex())
s('poke', addr=a + 8, width=1, value=0x1f); print('POKE type byte', hex(a + 8), '= $1f')
if len(sys.argv) > 5:
    s('poke', addr=a + 7, width=1, value=int(sys.argv[5])); print('POKE period', hex(a + 7), '=', sys.argv[5])
F = [('mode', 13564), ('x', 26), ('y', 28), ('ev14798', 14798), ('exit15608', 15608), ('visited14794', 14794), ('msg14800', 14800)]
v = lambda: {n: w16(s, o) for n, o in F}
fk = s('fork')['id']
h = s('hits', steps=steps, addrs=['$10dfa', '$10eec', '$87d6'])
print('hits', ' '.join(f"{e['addr']}:{e['count']}@{e['first']}" for e in h['hits']))
s('restore', id=fk); prev = v(); print('start', prev)
for i in range(steps // 120000):
    s('step', n=120000); cur = v()
    d = {k: (prev[k], cur[k]) for k in cur if cur[k] != prev[k]}
    if d and set(d) != {'ev14798'}: print(f'  +{(i + 1) * 120000:>9d}', d)
    prev = cur
print('end', prev)
s('save', path=pre + '.snap'); s('render', path=pre + '.png'); s.close()
