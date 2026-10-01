"""route_room22_to_altar99.py <start.snap> <OUTDIR> [phases=ABCD]: Cadaver 88th pass, G1.  The real-lineage join E2 -> F1 -> E3, natural joystick/keyboard input only, nothing injected.
Start: E1's end (room 22, urn 143 carried, health 30).  End: the hero on altar 99's top (room 39) with 324 lying in front, 371/482/110 carried.
Phase A  E2 parts A, B (room 22 -> 15 -> 16) and the road to room 38's arrival (D5's road, E2's `to40` up to settle38).
Phase B  F1's `route_cross38.py down` (creature-table lookahead wait, then the crossing) in place of E2's room 38 `D` hold (which cost 24).
Phase C  E2's `to40` tail and part C: room 39 -> 40, urn 143 onto statue 156, flask 108 onto altar 45, jump up, 110 and 371, off the altar.
Phase D  E3's chain from room 40's floor: 39 -> 38 (adaptive wait W inside room 38: the smallest W of the list whose whole flame/door $12 stage costs 0), FLAMEs, 48, 52, 53 (4.8M wait,
         459, 458), D4's leg to chest 157 and 165, room 39, the 165 throw onto altar 99, the jump, walk to x lead 21 in front of 324 (not taken).
Reload after every leg (route_chain.Route); only OUTDIR is written.  Each phase starts from the previous phase's `<X>_end.snap` in OUTDIR, so a phase can be rerun alone."""
import sys, os, subprocess, shutil, json
ARGS = [os.path.abspath(a) if i < 2 else a for i, a in enumerate(sys.argv[1:])]
HD = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(HD, '..', '..', '..', '..', '..', '..', '..', '..')); os.environ['M68000_ROOT'] = ROOT
os.environ.setdefault('ATARI_NOTRACE', '1')
os.environ.setdefault('CAD_OUT', os.path.join(ARGS[1], '_scratch'))
sys.path.insert(0, HD)
import route_room22_to_371 as E2          # E2's helpers (grid_select, throw, take, part_a ... part_c); its own ARGS parse is harmless here
from e3lib import *                       # e3 lib: route_chain (Route, ...) + hp, zz, st, ruck, ent, objrec
_start0, OUT = ARGS[0], ARGS[1]
PHASES = ARGS[2] if len(ARGS) > 2 else 'ABCD'
os.makedirs(OUT, exist_ok=True)
WLIST = [int(x) for x in os.environ.get('G1_WLIST', '').split(',') if x] or [0, 250000, 500000, 750000, 1000000, 1250000, 1500000, 1750000, 2000000, 2250000, 2500000, 2750000, 3000000, 3250000, 3500000]

def end_snap(name): return os.path.join(OUT, name + '_end.snap')
def finish(R, name):
    R.r.snap(end_snap(name)); print('%s end: %s ruck %s' % (name, st(R.r), [x[0] for x in ruck(R.r)]), flush=True); R.r.close()

# ---------------------------------------------------------------- phase A
def phase_A():
    R = Route(OUT + '/A', _start0)
    print('start', st(R.r), [x[0] for x in ruck(R.r)], flush=True)
    E2.part_a(R); E2.part_b(R)
    R.S('settle16b', 20000)
    if pos(R.r) != (20, 13, 14, 7):
        R.H('R_stall', 'R', 16); R.H('U_north', 'U', 16)
    R.H('R', 'R', 17); R.S('settle17', 100000)
    R.G('goto_R40', 'R', lambda p: p[0] >= 40)
    R.H('D', 'D', 38); R.S('settle38', 100000)
    finish(R, 'A')

# ---------------------------------------------------------------- phase B
def phase_B():
    d = OUT + '/B'; os.makedirs(d, exist_ok=True)
    env = dict(os.environ, M68000_ROOT=ROOT, ATARI_NOTRACE='1')
    rc = subprocess.run([sys.executable, HD + '/route_cross38.py', end_snap('A'), d, 'down'], env=env).returncode
    assert rc == 0, 'F1 found no safe plan'
    shutil.copy(d + '/end_down.snap', end_snap('B'))
    print('B result', open(d + '/result.json').read(), flush=True)

# ---------------------------------------------------------------- phase C
def phase_C():
    R = Route(OUT + '/C', end_snap('B'))
    print('C start', st(R.r), [x[0] for x in ruck(R.r)], flush=True)
    R.G('goto_R46', 'R', lambda p: p[0] >= 46)
    R.H('D', 'D'); R.H('D', 'D', 40); R.S('settle40', 100000)
    E2.part_c(R)
    finish(R, 'C')

# ---------------------------------------------------------------- phase D (E3's chain)
def jump1(bits, minsteps=200000):
    def f(r):
        joy(r, FIRE | bits); n = 0
        while True:
            r.cmd('s 10000'); n += 10000
            if n >= minsteps and zz(r)[1] == 0: break
            assert n < 1500000
        joy(r, 0); r.cmd('s 200000')
        return 'landed after %d steps, flames %s %s' % (n, ent(r, 211) is not None, ent(r, 212) is not None)
    return f

class StrictRoute(Route):
    """a trial run: abort (Lost) at the first leg that costs health"""
    class Lost(Exception): pass
    strict = True
    def leg(self, name, f, expect_room=None):
        h0 = self.r.w(HEALTH); Route.leg(self, name, f, expect_room)
        if self.strict and hp(self.r) < h0: raise StrictRoute.Lost((name, h0, hp(self.r)))

def stageD0a(R):
    """room 40's floor (27,44,21,38) -> room 39 south arrival (44,79,38,73)"""
    R.H('U_north40', 'U'); R.G('goto_R44', 'R', lambda p: p[0] >= 44)
    R.H('U_to39', 'U', 39); R.S('settle39', 100000)

def stageD0b(R, W39):
    """room 39: stand W39 steps (creature 907 patrols the row y 48..55 westward at the hero's speed: a walk north at once costs 10), walk the east lane north, door $03 into room 38 (20,79,14,73)"""
    R.S('wait39_%d' % W39, W39)
    R.H('U_39_north', 'U'); R.G('goto_L20', 'L', lambda p: p[0] <= 20)
    R.settle_on_change('U_to38', lambda r: hold(r, UP), 38)

def stageD1(R, W):
    R.S('wait_patrol_%d' % W, W)
    R.G('goto_U50', 'U', lambda p: p[1] <= 50); R.G('goto_R33', 'R', lambda p: p[0] >= 33)
    R.leg('aimU', lambda r: aim(r, UP) or pos(r))
    R.leg('jump_212', jump1(UP))
    R.G('goto_R56', 'R', lambda p: p[0] >= 56)
    R.leg('aimD', lambda r: aim(r, DOWN) or pos(r))
    R.leg('jump_211', jump1(DOWN))
    print('door12', door(R.r, 0x12), flush=True)
    R.G('goto_R79', 'R', lambda p: p[0] >= 79)
    R.H('D_corner', 'D'); R.settle_on_change('R_to48', lambda r: hold(r, RIGHT), 48)
    assert R.r.w(ROOM) == 48, R.r.w(ROOM)

def stageD2(R):
    # room 48 -> 52 -> 53, wait for item 459, take it, apply it to 458 (s87/b3/s34_natural_to458.py as Route legs)
    R.H('R48', 'R'); R.H('U48', 'U')
    R.settle_on_change('R_48_52', lambda r: hold(r, RIGHT), 52)
    R.H('R52_spiders', 'R'); R.H('U52', 'U')
    for k in range(5):
        R.settle_on_change('R_52_53_try%d' % k, lambda r: hold(r, RIGHT))
        if R.r.w(ROOM) == 53: break
    assert R.r.w(ROOM) == 53
    R.S('wait_459', 4800000)
    print('  459', ent(R.r, 459), flush=True)
    R.G('goto_D60', 'D', lambda p: p[1] >= 60); R.G('goto_R20', 'R', lambda p: p[0] >= 20)
    def jump(r):
        joy(r, FIRE | RIGHT)
        for i in range(70): r.cmd('s 10000')
        joy(r, 0); r.cmd('s 700000'); return 'landed %s z %s' % (pos(r), zz(r))
    R.leg('jump_slab', jump)
    for k in range(5):
        R.S('settle300k_%d' % k, 300000); R.H('L_%d' % k, 'L')
        if pos(R.r)[0] <= 14: break
    R.G('goto_R24', 'R', lambda p: p[0] >= 24)
    def take(want):
        def f(r):
            res = probe(r); assert res and res[0] == want, res
            t = Tally(r); open_panel(r, t); pick_icon_id(r, t, 2); t.run(100000)
            return 'took %s ruck %s' % (want, [x[0] for x in ruck(r)])
        return f
    R.leg('take459', take(459))
    R.G('goto_U38', 'U', lambda p: p[1] <= 38); R.H('L_458', 'L')
    def apply458(r):
        res = probe(r); assert res and res[0] == 458, res
        t = Tally(r); ruck_panel(r, t, 'space'); pick_icon_id(r, t, 0xc); t.run(150000)
        return 'applied; door14 %s ruck %s' % (door(r, 0x14), [x[0] for x in ruck(r)])
    R.leg('apply458', apply458)

def ids(r, want):
    tbl = r.l(A5 + 56); n = r.w(A5 + 1152); out = {}
    for i in range(n):
        e = r.mem(tbl + 0x46 * i, 0x46); t = int.from_bytes(e[10:14], 'big')
        oid = r.w(t + 4) if 0x1000 < t < 0x7ffff else None
        if oid in want: out[oid] = tuple(e[0:4])
    return out

def pushes(r, n, hold_=30000, rest=20000):
    for i in range(n): joy(r, RIGHT); r.cmd('s %d' % hold_); joy(r, 0); r.cmd('s %d' % rest)

def jumpR(r):
    joy(r, FIRE | RIGHT)
    for i in range(70): r.cmd('s 10000')
    joy(r, 0); r.cmd('s 700000')
    z = tuple(r.mem(0x3833c, 2)); assert z[1] == 18 and pos(r)[0] >= 52, (pos(r), z)
    return 'landed %s z %s' % (pos(r), z)

def smash(r):
    r.cmd('s 400000'); f = ids(r, (482, 452, 453, 202)); assert 482 in f and 453 not in f, f; return 'urns smashed: %s' % f

def take3(want, icon=2):
    def f(r):
        res = probe(r); assert res and res[0] == want, res
        t = Tally(r); open_panel(r, t); pick_icon_id(r, t, icon); t.run(150000)
        return 'took %s ruck %s' % (want, [x[0] for x in ruck(r)])
    return f

def last_ck(R):
    import glob
    return glob.glob('%s/ck_%02d_*.snap' % (R.d, R.n))[0]

def find_n(R, oid, nav=False):
    """RIGHT-pulse count that opens the Return-grid panel of item `oid`.  With 8 items carried the grid shows 4 cells: the cursor `2122(A5)` sticks at cell 3 and the opened item is NOT the one 2122 names
    (3 RIGHT pulses opened item 371, 5 opened 110, 4 and 8 opened 165, 12 opened 165 with 2122 = 3), so n is searched on forks of the leg's own checkpoint (item word `1236(A5)` after FIRE must equal oid).
    Only one emulator process at a time: R.r is closed during the search and reopened from the same checkpoint (a live second process broke the panel navigation of the first)."""
    import glob
    ck = glob.glob('%s/ck_%02d_*.snap' % (R.d, R.n))[0]; R.r.close(); found = None
    for n in range(0, 14):
        f = Repl(ck); ft = Tally(f)
        tap(f, ft, 0x1c)
        for _ in range(n): pulse(f, ft, RIGHT)
        ft.joy(FIRE); ft.run(40000); ft.joy(0); ft.run(90000)
        ok = f.w(A5 + 1236) == oid
        if ok and nav: pulse(f, ft, RIGHT); ok = cur_icon(f)[0] == 13   # n = 0 opens the right item but the panel then ignores the cursor pulses (x7.py): require one RIGHT to move it
        f.close()
        if ok: found = n; break
    R.r = Repl(ck)
    assert found is not None, ('no pulse count opens', oid)
    return found

def sel_item(r, t, oid, n):
    tap(r, t, 0x1c)
    for _ in range(n): pulse(r, t, RIGHT)
    t.joy(FIRE); t.run(40000); t.joy(0); t.run(90000)
    assert r.w(A5 + 1236) == oid, (oid, r.a5(1236, 2).hex(), n)
    return n

def spell_then_open(r, n):
    t = Tally(r)
    sel_item(r, t, 482, n)
    ic = icons(r); assert 16 in ic, ic
    t.reset(); pick_icon_id(r, t, 0x10); t.run(200000)
    t.reset(); open_panel(r, t); ic2 = icons(r); assert ic2[0] == 3, ic2; pick_icon_id(r, t, 3); t.run(250000)
    f = ids(r, (124, 165, 398)); assert 165 in f, f
    return 'dispelled + opened: %s ruck %s' % (f, [x[0] for x in ruck(r)])

def stageD3(R):
    R.G('D40', 'D', lambda p: p[1] >= 40)
    R.G('R24', 'R', lambda p: p[0] >= 24)
    R.leg('jumpR_to_37', jumpR)
    R.G('U34_pushes_urns_up', 'U', lambda p: p[1] <= 34)
    R.G('R56', 'R', lambda p: p[0] >= 56)
    R.leg('push8', lambda r: pushes(r, 8)); R.S('settle300k', 300000)
    R.G('L56', 'L', lambda p: p[0] <= 56)
    R.G('U28', 'U', lambda p: p[1] <= 28)
    def push_off(r):
        n = 0
        while ids(r, (452, 453)) and n < 30 and any(v[0] < 70 for v in ids(r, (452, 453)).values()):
            pushes(r, 1); n += 1
        return '%d pushes, urns %s' % (n, ids(r, (452, 453)))
    R.leg('push_urns_off', push_off)
    R.leg('smash', smash)
    R.G('U16_off_north', 'U', lambda p: p[1] <= 16)
    R.S('settle600k', 600000)
    R.G('U12', 'U', lambda p: p[1] <= 12)
    R.G('L58', 'L', lambda p: p[0] <= 58)
    e = ent(R.r, 482)[0]; xlo = e[2]
    R.G('R_over_482', 'R', lambda p: p[0] >= xlo + 5)   # hero x trail >= 64: at xlo + 2 (trail 62) the probe sees platform 37 (x 52..63), not 482
    R.G('D15_482', 'D', lambda p: p[1] >= ent(R.r, 482)[0][3] - 1)
    R.leg('take482', take3(482))
    R.G('R70', 'R', lambda p: p[0] >= 70)
    R.G('D46', 'D', lambda p: p[1] >= 46)
    R.G('L20', 'L', lambda p: p[0] <= 20)
    R.G('D52', 'D', lambda p: p[1] >= 52)
    R.settle_on_change('L_to_52', lambda r: hold(r, LEFT), 52)
    R.settle_on_change('L_52_spiders', lambda r: hold(r, LEFT))
    R.settle_on_change('L_52_to_48', lambda r: hold(r, LEFT), 48)
    R.G('L30', 'L', lambda p: p[0] <= 30)
    R.settle_on_change('D_to_51', lambda r: hold(r, DOWN), 51)
    R.G('D31', 'D', lambda p: p[1] >= 31)
    R.G('L20b', 'L', lambda p: p[0] <= 20)
    R.leg('take166', take3(166))
    R.settle_on_change('U_to_48', lambda r: hold(r, UP), 48)
    R.G('L26', 'L', lambda p: p[0] <= 26)
    R.settle_on_change('U_to_49', lambda r: hold(r, UP), 49)
    R.settle_on_change('U_to_56', lambda r: hold(r, UP), 56)
    R.H('U_chest', 'U')
    R.leg('probe157', lambda r: (lambda res: (res and res[0]) == 157 or (_ for _ in ()).throw(AssertionError(res)))(probe(r)))
    n482 = find_n(R, 482); R.leg('dispell_open', lambda r: spell_then_open(r, n482))
    R.H('D_to_165', 'D')
    R.leg('take165', take3(165))
    R.settle_on_change('D_56_to_49', lambda r: hold(r, DOWN), 49)
    R.settle_on_change('D_49_to_48', lambda r: hold(r, DOWN), 48)
    R.settle_on_change('L_48_to_38', lambda r: hold(r, LEFT), 38)
    R.G('L73', 'L', lambda p: p[0] <= 73)
    R.settle_on_change('D_38_to_39', lambda r: hold(r, DOWN), 39)
    assert 165 in [x[0] for x in type8(R.r)['recs']], type8(R.r)['recs']

def stageD4(R):
    R.G('goto_L51', 'L', lambda p: p[0] <= 51)
    R.G('goto_D40', 'D', lambda p: p[1] >= 40)
    R.leg('aimL', lambda r: aim(r, LEFT, 20000) or pos(r))
    assert pos(R.r) == (49, 40, 43, 34), pos(R.r)
    def select165(r):
        t = Tally(r); cell = sel_item(r, t, 165, n165)
        ic = icons(r); assert 0xd in ic, ic
        print('  select165: n', n165, 'item', r.a5(1236, 2).hex(), 'cur', cur_icon(r), 'icons', ic, flush=True)
        t.reset(); pick_icon_id(r, t, 0xd); t.run(100000); assert r.w(A5 + 1262) == 165, r.a5(1262, 2).hex()
        return 'selected with %d RIGHT pulses icons %s sel %s' % (cell, ic, r.a5(1262, 2).hex())
    n165 = find_n(R, 165, nav=True)
    R.leg('select165', select165)
    def throw165(r):
        sites = (0x100b0, 0xfe24, 0x8a34, 0x8a68, 0xa19e, 0xa4ba); tot = {}; hmin = hp(r)
        joy(r, FIRE)
        for i in range(50):
            for k, v in r.hits(15000, *sites).items(): tot[k] = tot.get(k, 0) + v
            hmin = min(hmin, hp(r))
        joy(r, 0); r.cmd('s 30000')
        assert ent(r, 324) is not None and ent(r, 165) is None, (ent(r, 324), ent(r, 165))
        return 'hits %s e324 %s xp %d hmin %d' % ({hex(k): v for k, v in tot.items() if v}, ent(r, 324), r.l(A5 + 1192), hmin)
    R.leg('throw165', throw165)
    R.S('settle300k', 300000)
    def jump_left(r):
        joy(r, FIRE | LEFT)
        for i in range(140):
            r.cmd('s 4000')
            if i == 19: joy(r, LEFT)
        joy(r, 0); r.cmd('s 100000')
        assert zz(r)[1] == 22 and 7 <= pos(r)[2] <= 33, (zz(r), pos(r))
        return 'landed bottom z %d' % zz(r)[1]
    R.leg('jump_left_onto_altar', jump_left)
    R.G('goto_L21', 'L', lambda p: p[0] <= 21)
    def probe324(r):
        res = probe(r); assert res and res[0] == 324, res
        return 'in front: %s icons %s' % (res[:2], res[3:5])
    R.leg('probe324', probe324)
    held = [a for a, b in ruck(R.r)]; assert 371 in held and 482 in held and 165 not in held, held

W39LIST = [int(x) for x in os.environ.get('G1_W39LIST', '').split(',') if x] or list(range(0, 2000001, 125000))

def phase_D():
    base = StrictRoute(OUT + '/D0', end_snap('C'))
    print('D start', st(base.r), [x[0] for x in ruck(base.r)], flush=True)
    stageD0a(base)
    s39 = OUT + '/D0_arrival39.snap'; base.r.snap(s39); base.r.close()
    R = None; W39 = W = None
    for W39 in W39LIST:
        d = '%s/D0b_W%d' % (OUT, W39)
        t = StrictRoute(d, s39)
        try: stageD0b(t, W39)
        except StrictRoute.Lost as e:
            print('D0b W39=%d: lost %s' % (W39, e.args[0]), flush=True); t.r.close(); shutil.rmtree(d, ignore_errors=True); continue
        print('D0b W39=%d: free, room 38 arrival health %d' % (W39, hp(t.r)), flush=True)
        s38 = d + '/arrival38.snap'; t.r.snap(s38); t.r.close()
        for W in WLIST:
            d1 = '%s/D1_W%d_%d' % (OUT, W39, W)
            t1 = StrictRoute(d1, s38)
            try:
                stageD1(t1, W); R = t1; print('D1 W=%d: free (health %d)' % (W, hp(t1.r)), flush=True); break
            except StrictRoute.Lost as e:
                print('D1 W=%d: lost %s' % (W, e.args[0]), flush=True); t1.r.close(); shutil.rmtree(d1, ignore_errors=True)
        if R is not None: break
    assert R is not None, 'no wait pair in the lists was free'
    json.dump({'W39': W39, 'W38': W}, open(OUT + '/D_waits.json', 'w'))
    R.strict = False
    stageD2(R); R.r.snap(OUT + '/D2_end.snap')
    stageD3(R); R.r.snap(OUT + '/D3_end.snap')
    stageD4(R)
    print('FINAL ruck', ruck(R.r), 'xp', R.r.l(A5 + 1192), 'z', zz(R.r), flush=True)
    finish(R, 'D')

if __name__ == '__main__':
    for ph in PHASES: {'A': phase_A, 'B': phase_B, 'C': phase_C, 'D': phase_D}[ph]()
