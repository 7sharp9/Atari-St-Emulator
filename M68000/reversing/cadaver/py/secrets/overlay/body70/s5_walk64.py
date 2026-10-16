"""natural joystick walk room 62 -> 64 (door $24: north edge, x lines 36..59).  Path from ck_c_applied239.snap (room 62, door $24 opened by the keyhole 239):
D, R, D, R, U, U (BFS holds, = bfs64 node 'DRDRUU' at (71,12)), then Left until x lead <= XL, then Up."""
from lib17 import *
def goto(r, bits, cond, chunk=5000, maxn=600):
    joy(r, bits)
    for _ in range(maxn):
        r.cmd('s %d' % chunk)
        if cond(pos(r)) or r.w(ROOM) != 62: break
    joy(r, 0); r.cmd('s 30000'); return pos(r)
XL = int(sys.argv[1]) if len(sys.argv) > 1 else 52
r = Repl(ROOT + '/scratchpad/cadaver/secrets_out/action/r16/ck_c_applied239.snap')
for mv in (DOWN, RIGHT, DOWN, RIGHT, UP, UP):
    print(NAMES[mv], hold(r, mv), 'health', r.w(HEALTH))
print('L to x<=%d' % XL, goto(r, LEFT, lambda p: p[0] <= XL), st(r))
print('U', hold(r, UP), st(r))
if r.w(ROOM) == 64:
    r.snap(OUT + 'room64_arrival.snap'); print('saved room64_arrival.snap, steps since start', r.steps)
r.close()
