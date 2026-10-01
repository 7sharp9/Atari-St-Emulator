"""route_level1_first.py <level1_room0.snap> <OUTDIR>: level 1's first leg by natural joystick input (89th pass; the 86th pass's a7/route_level1.py moved onto the exit_level0 libs, started from the real level-1 arrival: health 20 of 200, XP 980, rucksack empty).
Room 29 first takes STAMINA 556 from the top of block 425 and drinks it (health 20 -> 60, driven natural).
Room 0: U (north wall), L (north-west pocket), U -> room 34 (52,63,46,57); room 34: U (a no-op that still sets the reload phase), L, U -> room 29 (20,79,14,73), 100,000 steps for the entry block;
room 29: U, R, U, R -> room 31 (10,20,4,14), 100,000 steps.  Every hold reloads (snapshot, close, reopen).  The lane costs nothing (room 29's lane R then U costs 60: two static damage patches, 664 and 665, -15 a touch frame).
Writes ck_NN_*.snap and ends with `end room 31 ... health 60`."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE + '/../g2')
start, outdir = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
os.environ.setdefault('CAD_OUT', os.path.join(outdir, '_scratch'))
from lib import *
Rt = Route(outdir, start)
print('start', st(Rt.r), 'xp', Rt.r.l(A5 + 1192), 'max', Rt.r.w(A5 + 2516), 'level', Rt.r.a5(2524, 2).hex(), flush=True)
for name, mv in (('r0_U', 'U'), ('r0_L', 'L')): Rt.H(name, mv)
Rt.H('r0_U2', 'U', 34)
for name, mv in (('r34_U', 'U'), ('r34_L', 'L')): Rt.H(name, mv)
Rt.H('r34_U2', 'U', 29)
Rt.S('wait29', 100000)
# STAMINA 556 (+20 a dose, two doses) lies on top of block 425 (x 32..55, y 64..79, top z 24): one RIGHT+FIRE jump from the arrival lands on the block
def jump(r):
    joy(r, FIRE | RIGHT)
    for i in range(70): r.cmd('s 10000')
    joy(r, 0); r.cmd('s 700000'); return 'landed %s z %s' % (pos(r), zz(r))
Rt.leg('jump_block', jump)
Rt.G('goto_L40', 'L', lambda p: p[2] <= 40)
def take556(r):
    res = probe(r); assert res and res[0] == 556, res
    t = Tally(r); open_panel(r, t); pick_icon_id(r, t, 2); t.run(100000)
    return 'took 556 ruck %s' % ruck_ids(r)
Rt.leg('take556', take556)
def drink(r):
    t = Tally(r)
    for k in range(2):
        ruck_panel(r, t, 'space'); assert 9 in icons(r); h0 = hp(r); pick_icon_id(r, t, 9); t.run(100000)
        print('   drink %d: health %d -> %d' % (k, h0, hp(r)), flush=True)
    return 'ruck %s' % ruck_ids(r)
Rt.leg('drink556', drink)
# off the block's west edge, then the original lane: U must start in the x 14..20 column (block 561, x 16..23, stops it at y 56; from x 25..31 U runs into the damage patch 665, from the west wall it passes 561)
Rt.H('r29_L', 'L'); Rt.S('settle_drop', 200000); Rt.G('goto_L14', 'L', lambda p: p[2] <= 14)
Rt.S('settle29', 100000)
for name, mv in (('r29_U', 'U'), ('r29_R', 'R'), ('r29_U2', 'U')): Rt.H(name, mv)
Rt.H('r29_R2', 'R', 31)
Rt.S('wait31', 100000)
r = Rt.r
print('end room %d pos %s health %d xp %d' % (r.w(ROOM), pos(r), hp(r), r.l(A5 + 1192)), flush=True)
r.snap(os.path.join(outdir, 'end_room31.snap')); r.close()
