"""(promoted: reversing/captive/py/ai/ratt/scan_click.py; outputs under scratchpad/captive/ratt/) Scan clicks over the lower view area from a snapshot (one server, fork/restore per click); report cells where the hand 404(A6)
or the pile count 15020(A6) changes. Usage: scan_click.py <snap> x0 x1 dx y0 y1 dy"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from objs import R, StServer, snappath, A6, OUT
s = StServer(R); s('load', snapshot=snappath(sys.argv[1]))
x0, x1, dx, y0, y1, dy = [int(v) for v in sys.argv[2:8]]
st = lambda: (s.read(A6 + 404, 4).hex(), s.read(A6 + 15020, 2).hex())
base = s('fork')['id']
b = st(); print('base', b)
def mv(ddx, ddy):
    while ddx or ddy:
        a = max(-127, min(127, ddx)); c = max(-127, min(127, ddy))
        s('mouse', action='move', dx=a, dy=c); s('step', n=30000); ddx -= a; ddy -= c
for y in range(y0, y1 + 1, dy):
    row = []
    for x in range(x0, x1 + 1, dx):
        s('restore', id=base); s.sp = None
        for _ in range(3):
            s('mouse', action='move', dx=-127, dy=-127); s('step', n=30000)
        mv(x, y)
        s('mouse', action='down', button='l'); s('step', n=60000); s('mouse', action='up', button='l'); s('step', n=200000)
        r = st()
        if r != b: print('CHANGE at', x, y, r)
s.close()
