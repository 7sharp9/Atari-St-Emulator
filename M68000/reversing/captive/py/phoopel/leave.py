"""Which code leaves a base, and when the target is marked visited.
leave.py <snap> [poke]     <snap> under scratchpad/captive; 'poke' = labelled pokes party onto the entrance, facing N
Per input (a view click at (100,105), then keypad forward), a `hits` census over 3M steps of the leave flag's setters
($dd90 view click on the entrance, $9064, $e28e), the frame test $87c0, the exit $87d6, the visited mark $87f4, the
rebuild $8836, and $885a; then the same input replayed from the same state to read the words after it."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../ai'))
from cap import *

s = srv(sys.argv[1])
F = [('mode', 13564), ('x', 26), ('y', 28), ('face', 30), ('13410', 13410), ('target14782', 14782),
     ('visited14794', 14794), ('msg14800', 14800), ('14788', 14788)]
sv = lambda: {n: w16(s, o) for n, o in F}
if len(sys.argv) > 2:
    for off, v in ((26, w16(s, 22)), (28, w16(s, 24)), (30, 0)):
        s('poke', addr=A6 + off, width=2, value=v)
    s('step', n=180000)
    print('labelled pokes: party onto the entrance, facing 0')
t = w16(s, 14782)
print('start', sv(), 'target entry 14170(A6)+4*(t-1):', s.read(A6 + 14170 + 4 * (t - 1), 4).hex() if t > 0 else '-')
ADDRS = ['$dd90', '$9064', '$e28e', '$87c0', '$87d6', '$87f4', '$8836', '$885a']


def click():
    for _ in range(3):
        s('mouse', action='move', dx=-127, dy=-127); s('step', n=30000)
    s('mouse', action='move', dx=100, dy=105); s('step', n=30000)
    s('mouse', action='down', button='l')


def fwd():
    s('kbd', bytes=[0x68])


for name, press, release in (('view click', click, lambda: s('mouse', action='up', button='l')),
                             ('forward', fwd, lambda: s('kbd', bytes=[0xe8]))):
    fk = s('fork')['id']
    press()
    h = s('hits', steps=60000, addrs=ADDRS)
    release()
    h2 = s('hits', steps=3_000_000, addrs=ADDRS)
    print(f'{name}: hits', ' '.join(f"{a['addr']}:{a['count'] + b['count']}" for a, b in zip(h['hits'], h2['hits'])))
    print(f'{name}: after', sv())
    if w16(s, 13564) != 3:
        break
s.close()
