"""(promoted: reversing/captive/py/ai/ratt/click_at.py; outputs under scratchpad/captive/ratt/) Click on the screen at (x,y) from a snapshot, natural mouse input (pin to 0,0 then 1:1), report hand 404(A6) and floor pile
15020(A6) before/after, save snap + render. Usage: click_at.py <snap> <x> <y> <out-tag> [steps-after]"""
import os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from objs import R, StServer, snappath, A6, OUT
s = StServer(R); s('load', snapshot=snappath(sys.argv[1]))
x, y, tag = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
after = int(sys.argv[5]) if len(sys.argv) > 5 else 300000
st = lambda: (s.read(A6 + 404, 4).hex(), s.read(A6 + 15020, 2).hex())
print('before hand/pile', st())
for _ in range(3):
    s('mouse', action='move', dx=-127, dy=-127); s('step', n=30000)
def mv(dx, dy):
    while dx or dy:
        a = max(-127, min(127, dx)); b = max(-127, min(127, dy))
        s('mouse', action='move', dx=a, dy=b); s('step', n=30000); dx -= a; dy -= b
mv(x, y)
s('mouse', action='down', button='l'); s('step', n=60000); s('mouse', action='up', button='l'); s('step', n=after)
print('after hand/pile', st())
p = os.path.join(OUT, tag + '.snap'); s('save', path=p)
subprocess.run(['uv', 'run', 'python', '-I', os.path.join(R, 'tools', 'snap_render.py'), p, p[:-5] + '.png'], cwd=R, check=True, capture_output=True)
s.close()
