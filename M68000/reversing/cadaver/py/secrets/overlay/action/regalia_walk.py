"""regalia_walk.py: walk the hero with natural joystick input to the regalia room (33, `$21`) and take the four regalia the BUTTON
(id 2, room 34) asks for (ids 16 breastplate, 32 circlet, 28 shield, 26), then press the BUTTON and enter the treasury (room 37).

Only the entry into room 33 is injected: a scratch script `37 21 4 4 0` written over LEVER 86's event-5 block (not object 2: the BUTTON's own script must stay intact) and run through the
consumer (`verbs2/h.py real()`), the same route the verb tests use.  From there every move is a joystick hold to a stall (`drv.walk`),
found by a breadth-first search over U/D/L/R holds: each node is a snapshot, a node's probe is `drv.probe` (fire held; the icon loop
$009c82 opens when an object is in front, the result is the object's template id and the icon list).  A goal is reached when the
probe returns the wanted id with the wanted icon offered; `take` then opens the panel and picks icon 2 (TAKE) with fire, and the
type-8 list and rucksack count `2438(A5)` are read back.

    python reversing/cadaver/py/secrets/overlay/action/regalia_walk.py [enter|search ID|jump32|full|finish]

Object 32 (the circlet) is not found by the walk search: it rests on top of the large object 31 (z 18..31 on 31's z 0..17), so a hero standing on the floor never
overlaps it.  Holding fire with nothing in front starts a jump (the hero's z span at 0x38338+4 rises 0 -> 18 over ~50,000 steps, one cell of x per 10,000 with
a direction held); a jump that peaks after crossing 31's edge lands on 31 at z base 18, where `U` puts 32 in front (`jump32`).

Snapshots are written under scratchpad/cadaver/secrets_out/action/rw/.  Result of the 81st pass: see secrets.md "Room scripts" / the
puzzle paragraph; the search and take are deterministic from the same start snapshot."""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'verbs2'))
from drv import *            # Repl, A5, walk, probe, Tally, open_panel, pick_icon_id, type8, pos, UP DOWN LEFT RIGHT FIRE, OUT
import h as H_               # verbs2 harness (H, real)
RW = OUT + os.environ.get('RW_DIR', 'rw') + '/'
os.makedirs(RW, exist_ok=True)
NAMES = {UP: 'U', DOWN: 'D', LEFT: 'L', RIGHT: 'R'}
ROOM33 = RW + 'room33.snap'
START = os.environ.get('RW_START')     # a snapshot already in room 33 (the natural arrival of route_to_room33.py): nothing is injected, and the walk to the stall against 31 goes Up first


def enter_room33():
    """teleport into room `$21` at (4,4,0) through a real verb 37 and save the snapshot (or, with RW_START, use the snapshot of a natural arrival)"""
    if START: return START
    if os.path.exists(ROOM33): return ROOM33
    h = H_.H(H_.SNAP0)
    h.owner = 86        # the scratch script goes over LEVER 86's event-5 block, never over the BUTTON's (id 2), which must stay intact
    res = H_.real(h, [0x25, 0x21, 4, 4, 0, 0x17], steps=400000)
    room = h.r.w(A5 + 1166)
    assert room == 0x21, room
    h.r.snap(ROOM33); h.close()
    return ROOM33


def jump_onto_31(snap, back=60000):
    """from room 33's entry: walk right to the stall against object 31 (x 44..55, z 0..17), walk `back` steps left, hold fire+right (jump; with nothing in front fire
    is not a probe), keep right held until the hero lands on 31 (z base 18, x lead 55), then walk up to the stall; returns the snapshot at that stall"""
    r = Repl(snap)
    if START:    # the natural arrival is the south edge (y 41..47), south of 31's rows 8..31: go up to a row band inside them and below the circlet (y 20..22) first
        print('  up to', walk(r, UP, until=lambda p: p[1] <= 30), flush=True)
    walk(r, RIGHT, max_steps=1500000)
    joy(r, LEFT); r.cmd('s %d' % back); joy(r, 0); r.cmd('s 30000')
    joy(r, FIRE | RIGHT); r.cmd('s 300000')       # the arc starts after ~55,000 steps and is still rising when fire is released
    joy(r, RIGHT)
    last = None
    for _ in range(60):
        r.cmd('s 10000'); z = tuple(r.mem(0x38338 + 4, 2))
        if z == last and z[1] == 18: break      # landed: z base 18 = 31's top (17) + 1, two reads equal
        last = z
    if START: print('  east on 31:', walk(r, RIGHT, max_steps=1500000), flush=True)     # a jump from the south-west lands on 31's west edge (x lead 46); the circlet's column is x 47..50
    p = walk(r, UP, max_steps=1500000)
    print('  on 31, after U: pos', p, 'z', tuple(r.mem(0x38338 + 4, 2)), flush=True)
    out = RW + 'on31_u.snap'; r.snap(out); r.close()
    return out


_n = [0]
def search(snap, goal, icon, maxdepth=5, budget=900, seen=None):
    """BFS over walk-to-stall holds from `snap`; returns (path, snapshot path taken at the goal node before the probe) or None"""
    seen = {} if seen is None else seen
    queue = [(snap, '', None)]; t0 = time.time()
    while queue and time.time() - t0 < budget:
        s, path, ppos = queue.pop(0)
        if len(path) >= maxdepth: continue
        for mv in (UP, DOWN, LEFT, RIGHT):
            r = Repl(s)
            p = walk(r, mv, max_steps=1500000)
            key = (p, mv, r.w(A5 + 1166))
            if key in seen: r.close(); continue
            seen[key] = path + NAMES[mv]
            _n[0] += 1; s2 = RW + 'n%d.snap' % _n[0]; r.snap(s2)
            res = probe(r); r.close()
            oid, ic = (res[0], res[1]) if res else (None, None)
            print('  %-8s pos %s probe %s %s' % (path + NAMES[mv], p, oid, ic), flush=True)
            if oid == goal and ic and (icon is None or icon in ic):
                return path + NAMES[mv], s2
            queue.append((s2, path + NAMES[mv], p))
    return None


def probe_snap(snap):
    r = Repl(snap); res = probe(r); r.close()
    return (res[0], res[1]) if res else None


def take(snap, out):
    """panel on the object in front, icon 2 (TAKE); returns type-8 records and count; snapshot after"""
    r = Repl(snap); t = Tally(r)
    open_panel(r, t); pick_icon_id(r, t, 2)
    t8 = type8(r); cnt = r.a5(2438, 1)[0]
    r.snap(out); r.close()
    return cnt, t8['recs'][:cnt], dict(t.tot)


def finish(cur):
    """from the state after the four natural takes: find the BUTTON by natural walks and operate it with its own icon"""
    s2 = cur
    found = search(s2, 2, None, maxdepth=6, budget=1200)
    if not found: print('BUTTON not found'); return
    path, snap = found
    print('BUTTON path', path)
    VERBS = {'34 in list': 0x1079c, '58 IF ==n': 0x1061a, '70 sound': 0x10ec8, '37 teleport': 0x10974, '41 place': 0x10aaa, '28 message': 0x11230, '$e854 room load': 0xe854}
    KEYSITES.extend(VERBS.values())        # Tally.run's default list, extended in place so pick_icon_id's counted windows see the verbs
    r = Repl(snap); t = Tally(r)
    xp0, room0 = r.l(A5 + 1192), r.w(A5 + 1166)
    open_panel(r, t); ic = icons(r); print('  icons', ic)
    ic_pick = 4 if 4 in ic else ic[0]
    pick_icon_id(r, t, ic_pick)
    t.run(600000)
    names = {v: k for k, v in VERBS.items()}
    print('  icon', ic_pick, 'room', room0, '->', r.w(A5 + 1166), 'XP', xp0, '->', r.l(A5 + 1192), 'hits', {names.get(k, hex(k)): v for k, v in sorted(t.tot.items()) if v})
    r.snap(RW + 'treasury.snap')
    r.close()


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'full'
    s = enter_room33()
    print('room 33 snapshot', s)
    if what == 'search':
        print(search(s, int(sys.argv[2]), 2))
    elif what == 'jump32':
        at = jump_onto_31(s)
        print('probe', probe_snap(at))
        cnt, recs, hits = take(at, RW + 'taken32.snap')
        print('  take 32: rucksack count', cnt, 'type-8 records', recs, 'hits', {hex(k): v for k, v in hits.items() if k in (0xa136, 0xc42a, 0xa184)})
    elif what == 'finish':
        finish(RW + 'taken26.snap')
    elif what == 'crown':      # from the treasury (room 37, `finish`'s treasury.snap): the royal crown 53, the pass of doors $2a and $29, lies one step east of the arrival
        found = search(RW + 'treasury.snap', 53, 2, maxdepth=4)
        print('crown path', found and found[0])
        cnt, recs, hits = take(found[1], RW + 'taken53.snap')
        print('  take 53: rucksack count', cnt, 'type-8 records', recs, 'hits', {hex(k): v for k, v in hits.items() if k in (0xa136, 0xc42a, 0xa184)})
    elif what == 'full':
        at = jump_onto_31(s)
        if START:      # a natural arrival stands on 31 away from the circlet: the search finds the stall that puts 32 in front (RDUD from the on-31 snapshot)
            found = search(at, 32, 2, maxdepth=4); print('goal 32 path', found and found[0], flush=True); at = found[1]
        cnt, recs, hits = take(at, RW + 'taken32.snap')
        print('  take 32: rucksack count', cnt, 'type-8 records', recs, flush=True)
        cur = RW + 'taken32.snap'
        for goal in (28, 16, 26):
            found = search(cur, goal, 2)
            print('goal', goal, 'path', found[0] if found else None, flush=True)
            if not found: break
            cnt, recs, hits = take(found[1], RW + 'taken%d.snap' % goal)
            print('  take', goal, ': rucksack count', cnt, 'type-8 records', recs, 'hits', {hex(k): v for k, v in hits.items() if k in (0xa136, 0xc42a, 0xa184)}, flush=True)
            cur = RW + 'taken%d.snap' % goal
        else:
            finish(cur)
