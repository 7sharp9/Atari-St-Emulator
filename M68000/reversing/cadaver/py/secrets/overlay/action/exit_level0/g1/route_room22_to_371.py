"""route_room22_to_371.py <start.snap> <OUTDIR>: Cadaver 88th pass, E2.  Natural joystick/keyboard input only, nothing injected, from room 22 (urn 143 carried; D2's end snapshot) to
scroll 371 and key 110 in the rucksack, the hero on HIGH ALTAR 45's top (room 40).
Part A  room 22 -> 20 -> 19 -> 14 -> 13 -> 15 (the reverse of route_to_room16's outbound road; door words 0 on the whole road).
Part B  room 15: wait for the patrol of 902/904 (the 2.3M-step wait of route_room16_to_door2a), `D`, `L` to object 81; if door $18 is still closed (word ffff: the lineage of `ck_d_key104`, key 104 never
        applied) apply key 104 (Return grid, slot of 104, FIRE, icon $c); `D` -> room 16.  If the door is already open (the real chain: the heal road opened it) `D` crosses directly.
Part C  D5's road (room 16 -> 17 -> 38 -> 39 -> 40, throw the urn onto statue 156, take flask 108, throw it onto altar 45, jump on top, take 110 and 371).
Item selection by id: the throw item is chosen through the Return grid (RIGHT pulses to the item's slot, FIRE, icon $d), not by 'the most recently added item is selected first'.
Reload after every leg (Route); only OUTDIR is written."""
import sys, os
ARGS = [os.path.abspath(a) if i < 2 else a for i, a in enumerate(sys.argv[1:])]   # drv.py chdirs to the repo root on import: absolutize first
HD = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(HD, '..', '..', '..', '..', '..', '..', '..', '..')); os.environ['M68000_ROOT'] = ROOT
os.environ.setdefault('CAD_OUT', os.path.join(ARGS[1], '_scratch'))
sys.path.insert(0, HD + '/../lib')
from route_chain import *

SITES = [0xa19e, 0xf328, 0x100b0, 0xfe24]
def ruck(r): t8 = type8(r); return [x[0] for x in t8['recs'][:t8['count']]]

def cell_of(r, oid):
    """grid cell of item `oid`: the index array (4 bytes per cell: flag.w, byte offset.w into the 4-byte records) maps a cell to its record; a cell keeps its number when other items go"""
    t8 = type8(r); idx, dat = int(t8['index'], 16), int(t8['data'], 16)
    for c in range(64):
        fl, ofs = r.w(idx + 4 * c), r.w(idx + 4 * c + 2)
        if fl and r.w(dat + ofs) == oid: return c
    raise AssertionError(('item not in the grid', oid, ruck(r)))

def grid_select(r, t, oid):
    """Return grid: RIGHT pulses until the cursor (2122(A5), a cell number) is on the cell of item `oid`, FIRE: the icon panel of that item opens"""
    c = cell_of(r, oid)
    tap(r, t, 0x1c)
    for _ in range(12):
        if r.w(A5 + 2122) == c: break
        pulse(r, t, RIGHT)
    assert r.w(A5 + 2122) == c, (oid, c, r.a5(2122, 2).hex())
    t.joy(FIRE); t.run(40000); t.joy(0); t.run(90000)
    return c

def pick_icon_xy(r, t, want, hold=40000):
    """pick icon `want` by reading the panel layout (box bytes at $6180 + row*64 + count*8 + slot): RIGHT x slot then DOWN x row.  drv.pick_icon_id's blind R,R,D,... walks off a short row
    onto its cancel box, and DOWN from there selects the NEXT rucksack item (a 5-icon flask panel [9,11,13,1,6]: the target 13 is row 1 slot 0, one DOWN)"""
    cnt = r.a5(2303, 1)[0]
    for row in range(2):
        for slot in range(4):
            box = r.b(0x6180 + row * 64 + cnt * 8 + slot)
            if box != 6 and r.b(0x5ff6 + box) == want and not (row == 0 and slot == 3 and cnt < 4):
                for _ in range(slot): pulse(r, t, RIGHT)
                for _ in range(row): pulse(r, t, DOWN)
                assert cur_icon(r)[0] == want, (cur_icon(r), want, row, slot)
                t.joy(FIRE); t.run(hold); t.joy(0); t.run(70000)
                return 'R%dD%d' % (slot, row)
    raise AssertionError(('icon not in the panel layout', want, icons(r)))

def throw(r, oid, ids):
    def ent():
        tbl = r.l(A5 + 56); n = r.w(A5 + 1152); out = []
        for i in range(n):
            e = r.mem(tbl + 0x46 * i, 0x46); tp = int.from_bytes(e[10:14], 'big')
            o = r.w(tp + 4) if 0x1000 < tp < 0x7ffff else None
            if o in ids: out.append((o, tuple(e[0:4]), 'z', e[5], e[4]))
        return out
    t = Tally(r); grid_select(r, t, oid); pick_icon_xy(r, t, 0xd); assert r.w(A5 + 1262) == oid, (oid, r.a5(1262, 2).hex())
    joy(r, FIRE)
    for i in range(40):
        for k, v in r.hits(20000, *SITES).items(): t.tot[k] = t.tot.get(k, 0) + v
    joy(r, 0); t.run(300000, sites=SITES)
    return 'xp %d ruck %s ents %s hits %s' % (r.l(A5 + 1192), ruck(r), ent(), t.show())

def take(r, want):
    res = probe(r); assert res and res[0] == want, res
    t = Tally(r); open_panel(r, t); pick_icon_id(r, t, 2); t.run(100000)
    return 'probe %s ruck %s' % (res[:2], ruck(r))

def aim_leg(R, name, mv): R.leg(name, lambda r: aim(r, K[mv]) or pos(r))

def part_a(R):
    S = R.S
    for nm, mv in [('L22_20', 'L'), ('L20w', 'L'), ('L20_19', 'L'), ('L19w', 'L'), ('L19_14', 'L'), ('L14w', 'L')]:
        R.H(nm, mv); S('w_' + nm, 100000)
    R.H('D14', 'D'); S('w_D14', 100000); R.H('L14_13', 'L', 13); S('w_L14_13', 100000)
    R.H('D13', 'D'); S('w_D13', 50000); R.H('L13w', 'L'); S('w_L13w', 50000); R.H('D13_15', 'D', 15); S('w_D13_15', 100000)

def part_b(R):
    R.S('patrol_wait_2.3M', 2300000)
    R.H('D15', 'D'); closed = door(R.r, 0x18)[4:8] == 'ffff'
    print('door $18 word', door(R.r, 0x18), flush=True)
    if closed:
        R.H('L15_obj81', 'L')
        def apply(r):
            res = probe(r); assert res and res[0] == 81, res
            t = Tally(r); grid_select(r, t, 104); assert 12 in icons(r), icons(r)
            pick_icon_id(r, t, 0xc); t.run(150000, sites=[0xa682, 0xa6f4, 0xfe24, 0xfe5a, 0x104e2, 0x10514])
            assert door(r, 0x18)[4:8] == '0000', door(r, 0x18); return 'door $18 %s' % door(r, 0x18)
        R.leg('apply104_on81', apply)
    R.S('w15', 100000)
    R.H('D15_16', 'D', 16); R.S('settle16', 100000)

def to40(R):
    R.S('settle16b', 20000)
    if pos(R.r) != (20, 13, 14, 7):
        R.H('R_stall', 'R', 16); R.H('U_north', 'U', 16)
    R.H('R', 'R', 17); R.S('settle17', 100000)
    R.G('goto_R40', 'R', lambda p: p[0] >= 40)
    R.H('D', 'D', 38); R.S('settle38', 100000)
    R.H('D', 'D'); R.G('goto_L22', 'L', lambda p: p[0] <= 22)
    R.H('D', 'D', 39); R.S('settle39', 100000)
    R.G('goto_R46', 'R', lambda p: p[0] >= 46)
    R.H('D', 'D'); R.H('D', 'D', 40); R.S('settle40', 100000)

def part_c(R):
    sc = R.settle_on_change
    R.H('D', 'D'); R.G('goto_R74', 'R', lambda p: p[0] >= 74); R.G('goto_L64', 'L', lambda p: p[0] <= 64); R.G('goto_D60', 'D', lambda p: p[1] >= 60)
    sc('R', lambda r: hold(r, RIGHT), 43)
    R.G('goto_U46', 'U', lambda p: p[1] <= 46); aim_leg(R, 'aimR', 'R')
    R.leg('throw_urn', lambda r: throw(r, 143, (143, 108)))
    R.G('goto_U42', 'U', lambda p: p[1] <= 42); R.H('R', 'R', 43)
    R.G('goto_U38', 'U', lambda p: p[1] <= 38); aim_leg(R, 'aimD', 'D'); aim_leg(R, 'aimR2', 'R')
    R.leg('take108', lambda r: take(r, 108))
    R.H('L', 'L'); R.G('goto_D52', 'D', lambda p: p[1] >= 52)
    sc('L', lambda r: hold(r, LEFT), 40)
    R.G('goto_L12', 'L', lambda p: p[0] <= 12); R.G('goto_U40', 'U', lambda p: p[1] <= 40); aim_leg(R, 'aimR3', 'R')
    R.G('goto_U40b', 'U', lambda p: p[1] <= 40); aim_leg(R, 'aimR4', 'R')
    R.leg('throw_flask', lambda r: throw(r, 108, (108, 371, 110)))
    R.G('goto_R20', 'R', lambda p: p[0] >= 20)
    def jump(r):
        joy(r, RIGHT | FIRE); r.cmd('s %d' % (21 * 20000)); joy(r, 0); r.cmd('s 100000')
        return 'z %s' % (tuple(r.mem(0x3833c, 2)),)
    R.leg('jump_onto_altar', jump)
    assert tuple(R.r.mem(0x3833c, 2)) == (51, 22), 'not on the altar top'
    aim_leg(R, 'aimD5', 'D')
    R.leg('take110', lambda r: take(r, 110))
    R.G('goto_D43', 'D', lambda p: p[1] >= 43); R.G('goto_R43', 'R', lambda p: p[0] >= 43); aim_leg(R, 'aimR5', 'R')
    R.leg('take371', lambda r: take(r, 371))
    # off the altar: `L` walks off its west edge, the fall to the floor (z 22 -> 0) completes in a 300,000-step settle; no health cost (L, R, D, U each tried from the take371 snapshot: 4/4 reach z (29,0), health unchanged)
    R.H('L_off_altar', 'L'); R.S('settle_down', 300000)
    assert tuple(R.r.mem(0x3833c, 2)) == (29, 0), tuple(R.r.mem(0x3833c, 2))

def main():
    start, out = ARGS[0], ARGS[1]
    stop = ARGS[2] if len(ARGS) > 2 else 'all'
    R = Route(out, start)
    print('start: room %d pos %s health %d xp %d ruck %s' % (R.r.w(ROOM), pos(R.r), R.r.w(HEALTH), R.r.l(A5 + 1192), ruck(R.r)), flush=True)
    part_a(R)
    if stop != 'a':
        part_b(R)
        if stop != 'b':
            to40(R); part_c(R)
    print('end: room %d pos %s health %d xp %d ruck %s' % (R.r.w(ROOM), pos(R.r), R.r.w(HEALTH), R.r.l(A5 + 1192), ruck(R.r)), flush=True)
    R.r.close()
if __name__ == '__main__': main()
