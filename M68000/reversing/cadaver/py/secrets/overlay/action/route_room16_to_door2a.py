"""route_room16_to_door2a.py: natural joystick input only, nothing poked.  Room 16 -> `U` into room 15, WAIT 2,300,000 steps (the roaming hazard 902 is then in its y 45..52 pause, and the climb
to room 13 costs no health: the same climb right after the arrival costs 30) -> `U` to room 13 -> `R` into room 14 -> the four BUTTONs on room 14's north wall in the order 183, 181, 180, 179
(each block needs the previous one's state bit; the 179 press runs CLEAR FLAG and door `$2a`'s word 53 -> 0) -> `D`, `L` into room 13 (east arrival) -> `U`, `L` to the stall (50,12,44,6) under
door `$2a`.  Reloads (snapshot, close, reopen) after every hold, like route_to_room33.py: `Repl.__init__` runs `s 1`.

    cd M68000 && .venv/bin/python reversing/cadaver/py/secrets/overlay/action/route_room16_to_door2a.py [TAG] [start snap]      (about 2 min; snapshots to r16/d2a_<TAG>_*.snap)

The default start is `r16/ck_e_room16.snap` (health 33); from `route_treasury_to_room16.py`'s end snapshot (`r16/t16_<run>/ck_12_R_to_16.snap`, health 37, crown carried) the road costs 0 as well.  86th pass: two
runs of the exploring agent, one rerun here and one chained rerun from the treasury route: every health reading is the start value, 11 checkpoints identical across the three runs from `ck_e_room16.snap`.
Once the four presses are done `U` from the stall crosses into room 36 (20,71,14,65) with or without the crown (the word is 0)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from route_lib import *

TAG = sys.argv[1] if len(sys.argv) > 1 else 'x'
START = sys.argv[2] if len(sys.argv) > 2 else OUT + 'r16/ck_e_room16.snap'
SITES = [0xa43c, 0xa486, 0xfe24, 0xfe5a, 0x10cc8, 0x104e2, 0x10514]


def st(r): return 'room %2d pos %s z %s health %d' % (r.w(ROOM), pos(r), tuple(r.mem(0x3833c, 2)), r.w(HEALTH))


def haz(r):
    tbl = r.l(A5 + 56); n = r.w(A5 + 1152); out = []
    for i in range(1, n):
        e = r.mem(tbl + 0x46 * i, 0x46); t = int.from_bytes(e[10:14], 'big'); oid = r.w(t + 4) if 0x1000 < t < 0x7ffff else None
        if oid in (902, 904, 237): out.append((oid, tuple(e[0:4])))
    return out


def objbytes(r, oid):
    tbl = r.l(A5 + 56); n = r.w(A5 + 1152)
    for i in range(1, n):
        e = r.mem(tbl + 0x46 * i, 0x46); t = int.from_bytes(e[10:14], 'big')
        if 0x1000 < t < 0x7ffff and r.w(t + 4) == oid: return t, r.mem(t, 24).hex()
    return None


def press(r, label, oid, icon=4):
    hold(r, UP)                                   # face the wall, stall adjacent (no move if already there)
    res = probe(r); print('  %s probe %s' % (label, res and (res[0], res[1])), flush=True); assert res and res[0] == oid, res
    t = Tally(r); h0 = r.w(HEALTH); b0 = objbytes(r, oid)
    open_panel(r, t); pick_icon_id(r, t, icon); t.run(100000, sites=SITES)
    print('  pressed %s: hits %s health %d->%d xp %d door2a %s' % (oid, t.show(), h0, r.w(HEALTH), r.l(A5 + 1192), door(r, 0x2a)), flush=True)
    print('   obj bytes before', b0[1] if b0 else None, 'after', (objbytes(r, oid) or (0, None))[1], flush=True)


def states(r):
    return {o: (objbytes(r, o) or (0, '?'))[1][:12] for o in (179, 180, 181, 183)}


def sp(name): return SN + 'd2a_%s_%s.snap' % (TAG, name)


def rk(r, name):
    p = sp(name); r.snap(p); r.close(); return Repl(p)


def leg(r, label, bits, **kw):
    room, p = hold(r, bits, **kw); print('  %-22s -> room %2d %s health %d' % (label, room, p, r.w(HEALTH)), flush=True); return room, p


r = Repl(START); print('start', st(r), flush=True)
leg(r, 'U (16 -> 15)', UP); r.cmd('s 150000'); r = rk(r, '01_r15')
r.cmd('s 2300000'); print('  waited 2.3M: hazards', haz(r), st(r)); r = rk(r, '02_wait')
room, p = leg(r, 'U (15 -> 13)', UP, max_steps=5000000); assert room == 13; r.cmd('s 150000'); r = rk(r, '03_r13')
room, p = leg(r, 'R (13 -> 14)', RIGHT); assert room == 14; r.cmd('s 150000'); r = rk(r, '04_r14')
print('  door $2a before:', door(r, 0x2a), 'rucksack', type8(r)['recs'][:3])
hold(r, UP)
press(r, 'button 183', 183); print('  states', states(r), flush=True); r = rk(r, '05_183')
print('  R ->', goto(r, RIGHT, lambda p: p[0] >= 48)); press(r, 'button 181', 181); r = rk(r, '06_181')
print('  L ->', goto(r, LEFT, lambda p: p[0] <= 38)); press(r, 'button 180', 180); r = rk(r, '07_180')
print('  L ->', goto(r, LEFT, lambda p: p[0] <= 25)); press(r, 'button 179', 179); print('  door $2a after:', door(r, 0x2a)); r = rk(r, '08_179')
leg(r, 'D (14)', DOWN); r = rk(r, '09_D')
room, p = leg(r, 'L (14 -> 13)', LEFT); assert room == 13; r.cmd('s 150000'); r = rk(r, '10_r13e')
leg(r, 'U (13 east wall)', UP); r = rk(r, '11_U')
leg(r, 'L (13 to the door stall)', LEFT); r.cmd('s 30000'); r.snap(sp('at_door2a'))
print('final:', st(r), 'door $2a', door(r, 0x2a), 'rucksack', type8(r)['recs'][:3])
r.close()
