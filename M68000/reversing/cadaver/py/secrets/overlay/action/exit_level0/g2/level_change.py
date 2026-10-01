"""level_change.py <room60.snap> <OUTDIR>: from the room 60 arrival (end_room60.snap of route_altar_to_room36_real.py): `L`, `U` to the stall under object 84, icon 7 (verb 51 START LEVEL), then Space at the
"PLACE LEVELS DISK" prompt (s86/a3/run84.py + load1.py pattern) and ~20M steps to level 1; reports level/room/health/max/XP/rucksack.  Natural input (joystick + one Space key).  Writes only under OUTDIR."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
start, outdir = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
os.environ.setdefault('CAD_OUT', os.path.join(outdir, '_scratch'))
from lib import *
os.makedirs(outdir, exist_ok=True)
Rt = Route(outdir, start)
print('start', st(Rt.r), 'xp', Rt.r.l(A5 + 1192), 'max', Rt.r.w(A5 + 2516), 'level', Rt.r.a5(2524, 2).hex(), 'ruck', ruck_ids(Rt.r), flush=True)
Rt.leg('L', lambda r: hold(r, LEFT), 60)
Rt.leg('U', lambda r: hold(r, UP), 60)
def p84(r):
    q = probe(r); assert q and q[0] == 84, q
    r.cmd('s 100000'); return 'probe %s' % ((q[0], q[1]),)
Rt.leg('probe84', p84)
def op84(r):
    t = Tally(r); open_panel(r, t); ic = icons(r); assert 7 in ic, ic; pick_icon_id(r, t, 7)
    for i in range(6):
        t.run(500000, sites=[0xfe24, 0x695e, 0xa448, 0xa486])
        if r.a5(2524, 2).hex() == '0101': break
    return 'icons %s level %s room %d health %d max %d xp %d hits %s' % (ic, r.a5(2524, 2).hex(), r.w(ROOM), hp(r), r.w(A5 + 2516), r.l(A5 + 1192), t.show())
Rt.leg('operate84', op84)
r = Rt.r; t = Tally(r)
r.cmd('kbd 39'); t.run(60000, sites=[0x695e]); r.cmd('kbd b9')
for i in range(12):
    t.run(3000000, sites=[0x695e, 0x118ec, 0xba2e])
    print(i, 'pc', hex(r.pc()), 'level', r.a5(2524, 2).hex(), 'room', r.w(ROOM), 'health', hp(r), 'max', r.w(A5 + 2516), 'xp', r.l(A5 + 1192), 'hits', t.show(), flush=True)
    if hp(r) > 0 and i >= 2 and r.pc() and r.w(A5 + 2516) > 0:
        r.cmd('s 300000'); break
r.snap(os.path.join(outdir, 'level1_room0.snap'))
print('final: level', r.a5(2524, 2).hex(), 'room', r.w(ROOM), 'pos', pos(r), 'health', hp(r), 'max', r.w(A5 + 2516), 'xp', r.l(A5 + 1192), 'ruck', ruck_ids(r), 'type8', type8(r)['count'], flush=True)
r.close()
