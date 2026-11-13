"""(promoted: reversing/captive/py/ai/ratt/clicks.py; outputs under scratchpad/captive/ratt/) Click a sequence of screen points on one stserver from a snapshot (natural mouse input: pin to 0,0, then 1:1), print hand 404(A6)
and floor pile count 15020(A6) after each, optionally hits on the item-description routines, save snap + render of the end state.
Usage: clicks.py <snap> '<x,y;x,y;...>' <out-tag> [hits]
hits: count arrivals at $138ae (Ratt text selector), $bb4c (print), $702c (item-description dispatch) over all the clicks."""
import os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from objs import R, StServer, snappath, A6, OUT
s = StServer(R); s('load', snapshot=snappath(sys.argv[1]))
pts = [tuple(int(v) for v in p.split(',')) for p in sys.argv[2].split(';')]
tag = sys.argv[3]
ADDRS = ['$138ae', '$702c', '$6f8e']
tot = {int(a[1:], 16): 0 for a in ADDRS}
def run(n):
    r = s('hits', steps=n, addrs=ADDRS)
    for h in r['hits']: tot[int(h['addr'].lstrip('$'), 16)] += h['count']
st = lambda: (s.read(A6 + 404, 4).hex(), s.read(A6 + 15020, 2).hex())
print('start hand/pile', st())
for x, y in pts:
    for _ in range(3):
        s('mouse', action='move', dx=-127, dy=-127); run(30000)
    dx, dy = x, y
    while dx or dy:
        a = max(-127, min(127, dx)); b = max(-127, min(127, dy))
        s('mouse', action='move', dx=a, dy=b); run(30000); dx -= a; dy -= b
    s('mouse', action='down', button='l'); run(60000); s('mouse', action='up', button='l'); run(300000)
    print(f'click ({x},{y}) -> hand/pile', st())
print('hits', {f'${k:x}': v for k, v in tot.items()})
p = os.path.join(OUT, tag + '.snap'); s('save', path=p)
subprocess.run(['uv', 'run', 'python', '-I', os.path.join(R, 'tools', 'snap_render.py'), p, p[:-5] + '.png'], cwd=R, check=True, capture_output=True)
s.close()
