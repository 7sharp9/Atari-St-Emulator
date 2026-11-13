"""(promoted: reversing/captive/py/ai/ratt/end_click.py; outputs under scratchpad/captive/ratt/) From a snapshot inside an end screen ($134b8), wait N steps, click, and report what follows (hits on $13624 end_Exit, $b122, $5608,
$8570; 14800, mode, 14778, party, mission 14776). Usage: end_click.py <snap> <wait-steps> <follow-steps> <tag>"""
import os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from objs import R, StServer, snappath, A6, OUT
s = StServer(R); s('load', snapshot=snappath(sys.argv[1]))
w = lambda o: int.from_bytes(s.read(A6 + o, 2), 'big')
sw = lambda o: (lambda v: v - 65536 if v > 32767 else v)(w(o))
ADDRS = ['$134b8', '$13624', '$b122', '$5608', '$8570', '$87b6']
tot = {int(a[1:], 16): 0 for a in ADDRS}
def run(n):
    for h in s('hits', steps=n, addrs=ADDRS)['hits']: tot[int(h['addr'].lstrip('$'), 16)] += h['count']
st = lambda: f'14800 {sw(14800)} mode {w(13564)} 14778 {w(14778)} mission {w(14776)} party {(w(26), w(28))} pc {s.reg("pc"):#x}'
print('start', st())
run(int(sys.argv[2])); print('after wait', st())
for _ in range(3): s('mouse', action='move', dx=-127, dy=-127); run(30000)
s('mouse', action='move', dx=100, dy=100); run(30000)
s('mouse', action='down', button='l'); run(60000); s('mouse', action='up', button='l')
for k in range(1, 9):
    run(int(sys.argv[3]) // 8)
    print(f'+{k * int(sys.argv[3]) // 8}: {st()} hits {{{", ".join(f"${a:x}: {v}" for a, v in tot.items())}}}')
    s('render', path=os.path.join(OUT, f'{sys.argv[4]}_{k}.png'))
s.save = None
s('save', path=os.path.join(OUT, sys.argv[4] + '_end.snap')) if len(sys.argv) > 5 else None
s.close()
