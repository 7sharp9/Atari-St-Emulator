"""regalia_walk.py: walk the hero with natural joystick input to the regalia room (33, `$21`) and take the four regalia the BUTTON
(id 2, room 34) asks for (ids 16 breastplate, 32 circlet, 28 shield, 26), then press the BUTTON and enter the treasury (room 37).

Only the entry into room 33 is injected: a scratch script `37 21 4 4 0` written over LEVER 86's event-5 block (not object 2: the BUTTON's own script must stay intact) and run through the
consumer (`verbs2/h.py real()`), the same route the verb tests use.  From there every move is a joystick hold to a stall (`drv.walk`),
found by a breadth-first search over U/D/L/R holds: each node is a snapshot, a node's probe is `drv.probe` (fire held; the icon loop
$009c82 opens when an object is in front, the result is the object's template id and the icon list).  A goal is reached when the
probe returns the wanted id with the wanted icon offered; `take` then opens the panel and picks icon 2 (TAKE) with fire, and the
type-8 list and rucksack count `2438(A5)` are read back.

    python reversing/cadaver/py/secrets/overlay/action/regalia_walk.py [enter|search ID|full|finish]

Snapshots are written under scratchpad/cadaver/secrets_out/action/rw/.  Result of the 81st pass: see secrets.md "Room scripts" / the
puzzle paragraph; the search and take are deterministic from the same start snapshot."""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'verbs2'))
from drv import *            # Repl, A5, walk, probe, Tally, open_panel, pick_icon_id, type8, pos, UP DOWN LEFT RIGHT FIRE, OUT
import h as H_               # verbs2 harness (H, real)
RW = OUT + 'rw/'
os.makedirs(RW, exist_ok=True)
NAMES = {UP: 'U', DOWN: 'D', LEFT: 'L', RIGHT: 'R'}
ROOM33 = RW + 'room33.snap'


def enter_room33():
    """teleport into room `$21` at (4,4,0) through a real verb 37 and save the snapshot"""
    if os.path.exists(ROOM33): return ROOM33
    h = H_.H(H_.SNAP0)
    h.owner = 86        # the scratch script goes over LEVER 86's event-5 block, never over the BUTTON's (id 2), which must stay intact
    res = H_.real(h, [0x25, 0x21, 4, 4, 0, 0x17], steps=400000)
    room = h.r.w(A5 + 1166)
    assert room == 0x21, room
    h.r.snap(ROOM33); h.close()
    return ROOM33


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


def take(snap, out):
    """panel on the object in front, icon 2 (TAKE); returns type-8 records and count; snapshot after"""
    r = Repl(snap); t = Tally(r)
    open_panel(r, t); pick_icon_id(r, t, 2)
    t8 = type8(r); cnt = r.a5(2438, 1)[0]
    r.snap(out); r.close()
    return cnt, t8['recs'][:cnt], dict(t.tot)


def finish(cur):
    """from the state after the three natural takes: poke object 32 into the type-8 list (its box lies inside the altar 31's, so the
    fire probe returns 31; see the docstring result), find the BUTTON by natural walks and operate it with its own icon"""
    r = Repl(cur)
    d = type8(r); n = d['count']
    idx, dat = int(d['index'], 16), int(d['data'], 16)
    print('  type-8 before poke: count', n, 'recs', d['recs'][:n], 'index words', r.mem(idx, 4 * (n + 1)).hex(' '))
    r.cmd('w %x %08x' % (idx + 4 * n, 0x00040000 | (4 * n))); r.cmd('w %x %08x' % (dat + 4 * n, 32 << 16))   # the game's own index format: flag 4, offset 4*slot
    s2 = RW + 'poked32.snap'; r.snap(s2); r.close()
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
    elif what == 'finish':
        finish(RW + 'taken26.snap')
    elif what == 'full':
        cur = s
        for goal in (28, 16, 26):
            found = search(cur, goal, 2)
            print('goal', goal, 'path', found[0] if found else None, flush=True)
            if not found: break
            cnt, recs, hits = take(found[1] if False else found[1], RW + 'taken%d.snap' % goal)
            print('  take', goal, ': rucksack count', cnt, 'type-8 records', recs, 'hits', {hex(k): v for k, v in hits.items() if k in (0xa136, 0xc42a, 0xa184)}, flush=True)
            cur = RW + 'taken%d.snap' % goal
