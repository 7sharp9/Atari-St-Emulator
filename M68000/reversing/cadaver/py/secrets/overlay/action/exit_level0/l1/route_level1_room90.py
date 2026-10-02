"""route_level1_room90.py <end_room31.snap> <OUTDIR>: level 1 from room 31 (health 60) to room 90 by natural joystick input (90th pass).  Nothing poked, nothing injected.

Room 31: one RIGHT+FIRE jump from the arrival lands on the altar (131) top, UP and RIGHT on it, one FIRE jump under the skull 198 (z 56..62) fires its event 9: GOMOVE 130 and 131 (the drape slides west, the altar south),
which frees the north portal (door $7a) to room 12.
Room 32 (door $36, south of 31): armour 578 is taken; the iron gates 127/128 close behind the hero and open only when lever 146 is pulled while VAR 6 and VAR 7 (bytes at 2282(A5)+6, +7, stepped by the room's tick
every ~400,000 steps) both read 2; the way back is the arrival lane x 14..20 (lead 20).
Room 12: the armour thrown east (select with icon $d, one FIRE press with a settle of 125,000 steps after the facing tap, which gives the long flight) lands in region 1 (x 41..55, y 9..23, z 4..12): the room's event 17
runs PLACE (the object goes to room 7), arms lever 225 (state bit 0), deletes 215/216/529 (+26 XP).  Lever 225 (icon 7) then runs GOMOVE 213 and 214: the two pillars (x 56..59 and 36..39, z 0..47) oscillate
vertically, and the hero (z 0..29) crosses each while its bottom z is above 30: `cross()` searches the wait before each walk (the pillars' clock runs on frames, so a recording with the hero standing still does not
predict the walk), accepts the first wait with no health loss and a clearance (pillar bottom - 30) of at least 2, and ends in room 90 at (14,20,8,14) with health unchanged.
Writes ck_NN_*.snap and ends with `end room 90 ... health 60`."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE + '/../g2')
start, outdir = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
os.environ.setdefault('CAD_OUT', os.path.join(outdir, '_scratch'))
from lib import *
Rt = Route(outdir, start)
r = Rt.r
print('start', st(r), 'xp', r.l(A5 + 1192), flush=True)


def rec(r, oid):
    tbl = r.l(A5 + 56); n = r.w(A5 + 1152)
    for i in range(n):
        e = r.mem(tbl + 0x46 * i, 0x46); t = int.from_bytes(e[10:14], 'big')
        if 0x1000 < t < 0x7ffff and r.w(t + 4) == oid: return t


def hold_fire(r, bits, n):
    joy(r, bits)
    for i in range(n): r.cmd('s 10000')
    joy(r, 0)


# ---- room 31: altar, skull, north door ------------------------------------------------------------------------------------------------------------------------------------------------------------
def jump_altar(r):
    goto(r, RIGHT, lambda p: p[0] >= 10); hold_fire(r, FIRE | RIGHT, 30); r.cmd('s 700000')
    assert pos(r) == (24, 20, 18, 14) and zz(r)[1] == 24, (pos(r), zz(r)); return 'on the altar top %s' % (pos(r),)
Rt.leg('jump_altar', jump_altar)
Rt.G('altar_up', 'U', lambda p: p[1] <= 11); Rt.S('s_up', 100000)
Rt.G('altar_right', 'R', lambda p: p[0] >= 33); Rt.S('s_right', 100000)
def skull(r):
    hold_fire(r, FIRE, 30); r.cmd('s 700000'); r.cmd('s 500000')
    assert ent(r, 130)[0] == (22, 3, 7, 3) and ent(r, 131)[0] == (43, 36, 20, 21), (ent(r, 130), ent(r, 131)); return '130 %s 131 %s' % (ent(r, 130)[0], ent(r, 131)[0])
Rt.leg('skull', skull)
Rt.H('fall_off', 'U'); Rt.S('settle_fall', 300000)
Rt.H('north31', 'U', 12); Rt.S('s12', 150000)

# ---- room 32: armour 578, lever 146 --------------------------------------------------------------------------------------------------------------------------------------------------------------
Rt.H('back31', 'D', 31); Rt.S('s31', 150000)
Rt.G('west31', 'L', lambda p: p[0] <= 18)
Rt.H('south31', 'D', 32); Rt.S('s32', 150000)
Rt.H('down32', 'D'); Rt.S('s32b', 100000)
def take578(r):
    res = probe(r); assert res and res[0] == 578 and 2 in res[1], res
    t = Tally(r); open_panel(r, t); pick_icon_id(r, t, 2); t.run(100000)
    assert (578, 73) in type8(r)['recs'][:type8(r)['count'] + 1], type8(r); return 'took 578'
Rt.leg('take578', take578)
Rt.H('up32', 'U'); Rt.S('s32c', 100000)
def at146(r):
    room, p = hold(r, LEFT); res = probe(r); assert res and res[0] == 146, res; return 'lever 146 in front at %s' % (p,)
Rt.leg('at146', at146)
def pull146(r):
    vars_ = lambda: (r.b(A5 + 2282 + 6), r.b(A5 + 2282 + 7))
    n = 0
    while vars_() != (2, 2) and n < 200: r.cmd('s 25000'); n += 1
    assert vars_() == (2, 2), vars_(); r.cmd('s 25000')
    t = Tally(r); sites = [0x101d0]; _run = Tally.run.__get__(t); t.run = lambda m, sites=sites + KEYSITES: _run(m, sites)
    open_panel(r, t); pick_icon_id(r, t, 7); t.run(200000)
    assert t.tot.get(0x101d0) == 2, t.show(); r.cmd('s 1000000'); return 'pulled after %d steps, GOANI x2' % (n * 25000)
Rt.leg('pull146', pull146)
Rt.leg('lane20', lambda r: goto(r, RIGHT, lambda p: p[0] >= 20, chunk=2000, maxn=400))
Rt.H('out32', 'U', 31); Rt.S('s31b', 150000)
Rt.G('west31b', 'L', lambda p: p[0] <= 18); Rt.H('north31b', 'U'); Rt.G('east31b', 'R', lambda p: p[0] >= 36)
Rt.H('north31c', 'U', 12); Rt.S('s12b', 150000)

# ---- room 12: the throw, lever 225, the pillars --------------------------------------------------------------------------------------------------------------------------------------------------------
def face_right(r):
    aim(r, RIGHT, 35000); assert pos(r)[0] == 21, pos(r)
Rt.leg('face_right', face_right)
def select578(r):
    t = Tally(r); ic = select_item(r, t, 578); assert 0xd in ic, ic
    t.reset(); pick_icon_id(r, t, 0xd); t.run(100000); assert r.w(A5 + 1262) == 578, r.a5(1262, 2).hex(); return 'selected 578'
Rt.leg('select578', select578)
def throw(r):
    """the flight length depends on the steps since the facing tap (a frame-phase lottery: 60,000 and 125,000 sent the armour into the region in the exploration, 20,000, 40,000, 80,000 and 100,000 left it on a pillar edge):
    search the settle S on forks and keep the first that sends the armour away, arms 225 and pays +26 XP"""
    tmp = os.path.join(outdir, '_throw.snap'); r.snap(tmp)
    for S in range(0, 400001, 5000):
        f = Repl(tmp); xp0 = f.l(A5 + 1192); f.cmd('s %d' % S) if S else None; hold_fire(f, FIRE, 5); f.cmd('s 900000')
        ok = ent(f, 578) is None and rec(f, 225) and (f.b(rec(f, 225) + 3) & 1) == 1 and f.l(A5 + 1192) == xp0 + 26
        print('   throw settle %6d -> 578 %s xp %+d%s' % (S, ent(f, 578), f.l(A5 + 1192) - xp0, '  <- taken' if ok else ''), flush=True)
        if ok:
            f.snap(os.path.join(outdir, 'throw_S%d.snap' % S)); f.close()
            Rt.r.close(); Rt.r = Repl(os.path.join(outdir, 'throw_S%d.snap' % S)); print('throw            room %d pos %s health %d  armour gone to room 7, lever 225 armed, XP +26 (settle %d)' % (Rt.r.w(ROOM), pos(Rt.r), hp(Rt.r), S), flush=True); Rt.reopen('throw'); return
        f.close()
    raise AssertionError('no settle sends the armour into region 1')
throw(Rt.r)
Rt.G('to225', 'U', lambda p: p[1] <= 15)
def at225(r):
    room, p = hold(r, LEFT); res = probe(r); assert res and res[0] == 225, res; return 'lever 225 in front at %s' % (p,)
Rt.leg('at225', at225)
def pull225(r):
    t = Tally(r); sites = [0x10554]; _run = Tally.run.__get__(t); t.run = lambda m, sites=sites + KEYSITES: _run(m, sites)
    open_panel(r, t); pick_icon_id(r, t, 7); t.run(200000); assert t.tot.get(0x10554) == 2, t.show(); return 'GOMOVE 213, 214'
Rt.leg('pull225', pull225)
Rt.G('park1', 'R', lambda p: p[0] >= 30); Rt.S('s_park1', 50000)


def cross(r, pid, stop, label, need=2, wmax=3000000, step=100000):
    """search the wait W (steps) before a RIGHT walk under pillar `pid`: first W with no health loss and clearance >= need; returns the end snapshot of that trial"""
    px = {214: (36, 39), 213: (56, 59)}[pid]; tmp = os.path.join(outdir, '_cross_%s.snap' % label); r.snap(tmp)
    for W in range(0, wmax + 1, step):
        f = Repl(tmp); h0 = hp(f); n = 0
        while n < W: f.cmd('s 5000'); n += 5000
        joy(f, RIGHT); minc = 99; lost = False; steps = 0; seen = False
        while steps < 2500000:
            f.cmd('s 5000'); steps += 5000
            if f.w(ROOM) != 12: break
            p = pos(f); b = ent(f, pid)[1]
            if p[0] >= px[0] and p[2] <= px[1]: seen = True; minc = min(minc, b - 30)
            if hp(f) < h0: lost = True; break
            if stop != 'room' and p[2] > px[1] and p[0] >= int(stop): break
        joy(f, 0); f.cmd('s 30000')
        ok = (not lost) and seen and minc >= need
        print('   %s W %8d steps %7d clearance %s lost %s room %d pos %s hp %d%s' % (label, W, steps, minc if seen else '-', lost, f.w(ROOM), pos(f), hp(f), '  <- taken' if ok else ''), flush=True)
        if ok:
            end = os.path.join(outdir, 'cross_%s_W%d.snap' % (label, W)); f.snap(end); f.close(); return W, end
        f.close()
    raise AssertionError('no clear crossing of pillar %d' % pid)


W_A, endA = cross(Rt.r, 214, 50, 'A')
Rt.r.close(); Rt.r = Repl(endA); Rt.reopen('crossA')
print('crossA: wait %d, hero %s' % (W_A, pos(Rt.r)), flush=True)
W_B, endB = cross(Rt.r, 213, 'room', 'B')
Rt.r.close(); Rt.r = Repl(endB); Rt.reopen('crossB')
r = Rt.r
print('crossB: wait %d' % W_B, flush=True)
assert r.w(ROOM) == 90, r.w(ROOM)
r.cmd('s 100000')
print('end room %d pos %s health %d xp %d' % (r.w(ROOM), pos(r), hp(r), r.l(A5 + 1192)), flush=True)
r.snap(os.path.join(outdir, 'end_room90.snap')); r.close()
