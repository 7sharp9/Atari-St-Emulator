"""route_altar_to_room36_real.py <start.snap> <OUTDIR> [--poke2a] [--pre=N] [--upto=<stage>]: the last leg of the MASSACRE road on the real items (88th pass, G2), room 39 altar 99 -> room 60.
Start: G1's D_end.snap (exit_level0/g1), formerly s88/e3/at_324_front.snap (room 39, hero on altar 99's top at (20,40,14,34), 324 in front, health 23, rucksack [110,482,371], door $2a word 53, key 104 gone; D5's lineage).
INJECTED (verb 35, labelled): the royal crown 53 only when it is not already carried (the real chain carries it from the heal chain, so there the script injects nothing).  371 is the carried one (selected by id).  Joystick/keyboard input only otherwise.
Stages: A = READ MAGIC cast at 324, take 324, walk off the altar, settle in room 39; F = f1/route_cross38.py up (creature-table lookahead wait inside room 38, arrival -> room 17);
B = rooms 17 -> 16 -> 15 (2.3M wait) -> 13; C = door $2a (the BUTTON chain of room 14 unless --poke2a: TEST ONLY, door word poked to 0 on the room-13 arrival, emulating the real lineage where
the heal chain already opened it, buttons skipped); D = room 36, MASSACRE, 486, door $29, room 60.  Everything but F runs through route_chain.Route (reload after every leg).
Writes only under OUTDIR (checkpoints, f1out/, c/, _scratch/); F's script is copied beside this file (f1/), the libs are the shared ../lib."""
import sys, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
args = [a for a in sys.argv[1:] if not a.startswith('--')]
flags = [a for a in sys.argv[1:] if a.startswith('--')]
start, outdir = os.path.abspath(args[0]), os.path.abspath(args[1])
POKE = '--poke2a' in flags
PRE = int(([f for f in flags if f.startswith('--pre=')] or ['--pre=0'])[0].split('=')[1])
POKEHP = ([f for f in flags if f.startswith('--hp=')] or [None])[0]
UPTO = ([f.split('=')[1] for f in flags if f.startswith('--upto=')] or ['D'])[0]
sys.path.insert(0, HERE)
os.makedirs(outdir, exist_ok=True)
os.environ.setdefault('CAD_OUT', os.path.join(outdir, '_scratch'))   # the lib's own output goes under the output dir
from lib import *
import drv as _drv

# ---------------- stage A
GIVEN = os.path.join(outdir, 'ck_00_given.snap')
h = H_.H(start); r0 = h.r
if 53 in ruck_ids(r0):
    print('crown 53 already carried (the real lineage): no give', 'ruck', ruck_ids(r0), flush=True)
else:
    res = H_.real(h, [0x23, 0, 53, 0x17], steps=300000)
    print('INJECTED give 53 (crown)', 'ruck', ruck_ids(r0), flush=True)
if POKEHP:
    hpv = int(POKEHP.split('=')[1]); r0.cmd('w %x %04x%04x' % (HEALTH, hpv, r0.w(HEALTH + 2)))  # REPL w writes a longword: keep the neighbouring word; print('TEST ONLY: health poked to', hpv, 'now', hp(r0), flush=True)
r0.snap(GIVEN); r0.close()
Rt = Route(outdir, GIVEN)
sc = Rt.settle_on_change
print('start', st(Rt.r), 'xp', Rt.r.l(A5 + 1192), 'ruck', ruck_ids(Rt.r), flush=True)

def cast_read(r):
    t = Tally(r); ic = select_item(r, t, 371); assert ic[0] == 16, ic
    b0 = r.mem(live_body(r, 324), 6).hex(' ')
    t.joy(FIRE); t.run(40000); t.joy(0); t.run(70000); r.cmd('s 300000')
    b1 = r.mem(live_body(r, 324), 6).hex(' ')
    assert 371 not in ruck_ids(r) and b0 != b1
    return '324 body %s -> %s, ruck %s' % (b0, b1, ruck_ids(r))
def take324(r):
    t = Tally(r); n0 = type8(r)['count']
    open_panel(r, t); ic = icons(r); pick_icon_id(r, t, 2); t.run(100000)
    assert have(r, 324), 'no 324'
    return 'icons %s count %d -> %d ruck %s' % (ic, n0, type8(r)['count'], ruck_ids(r))
def walk_off(r):
    goto(r, RIGHT, lambda p: zz(r)[1] == 0, maxn=200)
    return 'z %s' % (zz(r),)
def press(r, oid, icon=4):
    hold(r, UP)
    res = probe(r); assert res and res[0] == oid, res
    t = Tally(r); open_panel(r, t); pick_icon_id(r, t, icon); t.run(100000)
    return 'pressed %s door2a %s xp %d' % (oid, door(r, 0x2a), r.l(A5 + 1192))
def find_n(R, oid):
    """RIGHT-pulse count that opens the Return-grid panel of item `oid` (88th pass, G1's finding: with six or more items carried the grid shows 4 cells, the cursor 2122(A5) sticks
    and the opened item is not the one 2122 names, so `select_item`'s cursor test fails; search the count on forks of the last checkpoint, item word 1236(A5) == oid after FIRE).
    One emulator process at a time: R.r is closed during the search and reopened from the same checkpoint."""
    import glob
    ck = glob.glob('%s/ck_%02d_*.snap' % (R.d, R.n))[0]; R.r.close(); found = None
    for n in range(0, 14):
        f = Repl(ck); ft = Tally(f)
        tap(f, ft, 0x1c)
        for _ in range(n): pulse(f, ft, RIGHT)
        ft.joy(FIRE); ft.run(40000); ft.joy(0); ft.run(90000)
        ok = f.w(A5 + 1236) == oid
        f.close()
        if ok: found = n; break
    R.r = Repl(ck)
    assert found is not None, ('no pulse count opens', oid)
    return found
def sel324(r, n):
    t = Tally(r)
    tap(r, t, 0x1c)
    for _ in range(n): pulse(r, t, RIGHT)
    t.joy(FIRE); t.run(40000); t.joy(0); t.run(90000)
    assert r.w(A5 + 1236) == 324, (r.w(A5 + 1236), n)
    ic = icons(r); assert 0xd in ic, ic
    pick_icon_id(r, t, 0xd)
    return 'selected 1262 %s icons %s pulses %d' % (r.a5(1262, 2).hex(), ic, n)

Rt.leg('read_magic', cast_read, 39)
Rt.leg('take324', take324, 39)
Rt.leg('walk_off', walk_off, 39)
Rt.S('settle39', 100000)
Rt.r.snap(os.path.join(outdir, 'A_end.snap')); Rt.r.close()
if UPTO == 'A': sys.exit(0)

# ---------------- stage F: room 38 crossing, creature-table lookahead (f1/route_cross38.py up)
fdir = os.path.join(outdir, 'f1out')
env = dict(os.environ); env['ATARI_NOTRACE'] = '1'; env['M68000_ROOT'] = M68
cmd = [sys.executable, os.path.join(HERE, 'f1', 'route_cross38.py'), os.path.join(outdir, 'A_end.snap'), fdir, 'up', str(PRE)]
flog = os.path.join(outdir, 'f1.log')
with open(flog, 'w') as fh: rc = subprocess.call(cmd, stdout=fh, stderr=subprocess.STDOUT, env=env)
print('F1 up rc', rc, '(log f1.log):'); print(''.join(l for l in open(flog) if l.startswith(('start', 'S0', 'margin', 'EXEC', 'NO SAFE', 'hero profile', 'enter'))), end='', flush=True)
if rc != 0: sys.exit('F1: no safe plan')
Rt = Route(outdir + '/c', os.path.join(fdir, 'end_up.snap')); sc = Rt.settle_on_change
print('after F1', st(Rt.r), flush=True)
assert Rt.r.w(ROOM) == 17
if UPTO == 'F': sys.exit(0)

# ---------------- stage B: 17 -> 16 -> 15 -> 13
sc('L_16', lambda r: hold(r, LEFT), 16)
sc('U', lambda r: hold(r, UP))
sc('goto_L20', lambda r: goto(r, LEFT, lambda p: p[0] <= 20))
sc('U_15', lambda r: hold(r, UP), 15)
Rt.S('settle15', 150000)
Rt.S('wait15', 2300000)
sc('U_13', lambda r: hold(r, UP, max_steps=5000000), 13)
Rt.S('settle13', 150000)
if UPTO == 'B': sys.exit(0)

# ---------------- stage C: door $2a
def poke2a(r):
    a = 0x6d35a + 8 * 0x2a
    b = r.mem(a, 8).hex(); r.cmd('w %x 00000101' % (a + 2)); return 'TEST ONLY poke door2a %s -> %s' % (b, door(r, 0x2a))
w2a = door(Rt.r, 0x2a)[4:8]
print('door $2a word', w2a, flush=True)
if POKE and w2a != '0000': Rt.leg('poke2a', poke2a)
w2a = door(Rt.r, 0x2a)[4:8]
sc('R_14', lambda r: hold(r, RIGHT), 14)
Rt.S('settle14', 50000)
if w2a != '0000':
    Rt.leg('press183', lambda r: press(r, 183))
    Rt.leg('goto_R48', lambda r: goto(r, RIGHT, lambda p: p[0] >= 48))
    Rt.leg('press181', lambda r: press(r, 181))
    Rt.leg('goto_L38', lambda r: goto(r, LEFT, lambda p: p[0] <= 38))
    Rt.leg('press180', lambda r: press(r, 180))
    Rt.leg('goto_L25', lambda r: goto(r, LEFT, lambda p: p[0] <= 25))
    Rt.leg('press179', lambda r: press(r, 179))
sc('D', lambda r: hold(r, DOWN))
sc('L_13', lambda r: hold(r, LEFT), 13)
Rt.S('settle13e', 50000)
sc('U_wall', lambda r: hold(r, UP))
sc('L_stall', lambda r: hold(r, LEFT))
assert door(Rt.r, 0x2a)[4:8] == '0000', door(Rt.r, 0x2a)
N324 = find_n(Rt, 324)
Rt.leg('select324', lambda r: sel324(r, N324))
print('door2a', door(Rt.r, 0x2a), flush=True)
if UPTO == 'C': sys.exit(0)

# ---------------- stage D: room 36
sc('U_36', lambda r: hold(r, UP), 36)
def massacre(r):
    hp0 = hp(r); xp0 = r.l(A5 + 1192); n0 = (r.w(A5 + 396), [r.w(A5 + 398 + 2 * i) for i in range(4)])
    joy(r, FIRE)
    hh = r.hits(300000, 0xf02e, 0x4cde0, 0x4ce24, 0xfe24, 0xfdbc)
    joy(r, 0); r.cmd('s 300000')
    return 'creatures before %s hits %s xp %d -> %d health %d -> %d ruck %s dragon %s 486 %s' % (n0, {hex(k): v for k, v in hh.items() if v}, xp0, r.l(A5 + 1192), hp0, hp(r), ruck_ids(r), live_rec(r, 483) and 'alive', ent(r, 486))
Rt.leg('massacre', massacre, 36)
def probe486(r):
    q = probe(r); assert q and q[0] == 486, q
    return 'probe %s' % ((q[0], q[1]),)
def op486(r):
    t = Tally(r)
    d0 = door(r, 0x29); open_panel(r, t); ic = icons(r); pick_icon_id(r, t, 4); t.run(300000)
    assert door(r, 0x29)[4:8] == '0000', door(r, 0x29)
    return 'icons %s door29 %s -> %s xp %d' % (ic, d0, door(r, 0x29), r.l(A5 + 1192))
Rt.leg('U_north36', lambda r: hold(r, UP))
Rt.leg('goto_R66', lambda r: goto(r, RIGHT, lambda p: p[0] >= 66))
Rt.leg('U_486', lambda r: hold(r, UP))
Rt.leg('probe486', probe486)
Rt.leg('operate486', op486)
Rt.leg('goto_L50', lambda r: goto(r, LEFT, lambda p: p[0] <= 50))
sc('U_60', lambda r: hold(r, UP), 60)
print('end', st(Rt.r), 'xp', Rt.r.l(A5 + 1192), 'level', Rt.r.w(A5 + 2524), 'ruck', ruck_ids(Rt.r), flush=True)
print('ledger', [(a, b, c, e) for a, b, c, d, e in Rt.ledger])
Rt.r.snap(os.path.join(outdir, 'end_room60.snap')); Rt.r.close()
