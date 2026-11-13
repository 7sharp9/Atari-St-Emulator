"""(promoted: reversing/captive/py/ai/ratt/value2.py; outputs under scratchpad/captive/ratt/) 14800(A6) = 2 ("TRILL HAS BEEN LEFT TO DIE", $87d0/$882e): leave a FINAL base (13412(A6) nonzero) after the generators are blown (state
13410 >= 2) without the Trill level event (14798 = 0).
Start phoopel/finish_base1_blast_state2.snap (natural mission 1 base, generators blown; labelled pokes built it, see finish13.py).
Labelled pokes: party onto the entrance 22/24(A6) facing N (as revisit.py exit), and for the test run 13412(A6) = 1 (the final-base flag
the generator's D2 sets at $b5a8; the station landing itself is not driven here). The leave click is natural (mouse to the entrance icon).
Control (no 13412 poke): the base is left through $8836 (mode 1, rebuild) and $87d0/$882e do not run.
Usage: value2.py test|control [wait-steps-before-click]"""
import os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from objs import R, StServer, snappath, A6, OUT
mode = sys.argv[1]
s = StServer(R); s('load', snapshot=snappath('phoopel/finish_base1_blast_state2.snap'))
w = lambda o: int.from_bytes(s.read(A6 + o, 2), 'big')
sw = lambda o: (lambda v: v - 65536 if v > 32767 else v)(w(o))
ADDRS = ['$87c0', '$87d0', '$882e', '$87d6', '$8836', '$8804', '$134b8', '$13624', '$56ae', '$5608', '$8570']
tot = {int(a[1:], 16): 0 for a in ADDRS}; first = {}; step = [0]
def run(n):
    for h in s('hits', steps=n, addrs=ADDRS)['hits']:
        k = int(h['addr'].lstrip('$'), 16); tot[k] += h['count']
        if h['count'] and k not in first: first[k] = step[0] + h['first']
    step[0] += n
st = lambda: f'14800 {sw(14800)} mode {w(13564)} 13410 {w(13410)} 13412 {w(13412)} 14798 {w(14798)} mission {w(14776)} pc {s.reg("pc"):#x}'
for off, v in ((26, w(22)), (28, w(24)), (30, 0)):
    s('poke', addr=A6 + off, width=2, value=v)
print('labelled pokes: party onto the entrance, facing N')
if mode == 'test':
    s('poke', addr=A6 + 13412, width=2, value=1); print('labelled poke: 13412 = 1 (final base)')
run(180000)
print('before click:', st())
for _ in range(3): s('mouse', action='move', dx=-127, dy=-127); run(30000)
s('mouse', action='move', dx=100, dy=105); run(30000)
s('mouse', action='down', button='l'); run(60000); s('mouse', action='up', button='l')
for k in range(1, 41):
    run(500000)
    if k <= 8: s('render', path=os.path.join(OUT, f'v2_{mode}_t{k:02d}.png'))
    if k == 20:   # click the end screen (it ignores clicks for over a million steps, state3 trap): natural click, same pointer
        s('mouse', action='down', button='l'); run(60000); s('mouse', action='up', button='l'); print('click at +10M')
    if k % 5 == 0: print(f'+{k * 0.5}M:', st(), {f'${a:x}': v for a, v in tot.items()})
print('hits', {f'${a:x}': v for a, v in tot.items()}); print('first', {f'${a:x}': v for a, v in first.items()})
s('save', path=os.path.join(OUT, f'v2_{mode}_end.snap'))
s.close()
