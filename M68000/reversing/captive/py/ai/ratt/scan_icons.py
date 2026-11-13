"""(promoted: reversing/captive/py/ai/ratt/scan_icons.py; outputs under scratchpad/captive/ratt/) Click a grid of screen points from a snapshot (fork/restore per click), count hits on a handler. scan_icons.py <snap> <addr_hex> x0 x1 dx y0 y1 dy"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from objs import R, StServer, snappath, A6, OUT
s = StServer(R); s('load', snapshot=snappath(sys.argv[1])); addr = '$' + sys.argv[2]
x0, x1, dx, y0, y1, dy = [int(v) for v in sys.argv[3:9]]
base = s('fork')['id']
for y in range(y0, y1 + 1, dy):
    for x in range(x0, x1 + 1, dx):
        s('restore', id=base); s.sp = None
        for _ in range(3): s('mouse', action='move', dx=-127, dy=-127); s('step', n=30000)
        ddx, ddy = x, y
        while ddx or ddy:
            a = max(-127, min(127, ddx)); c = max(-127, min(127, ddy)); s('mouse', action='move', dx=a, dy=c); s('step', n=30000); ddx -= a; ddy -= c
        s('mouse', action='down', button='l'); r1 = s('hits', steps=60000, addrs=[addr]); s('mouse', action='up', button='l')
        r2 = s('hits', steps=400000, addrs=[addr])
        n = r1['hits'][0]['count'] + r2['hits'][0]['count']
        if n: print('HIT at', x, y, 'count', n)
s.close()
