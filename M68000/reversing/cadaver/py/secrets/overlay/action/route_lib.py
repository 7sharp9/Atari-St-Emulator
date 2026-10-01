"""route_lib.py: helpers of route_to_room16.py (placement dump, door words, goto, wall summary); imports trek/drv from this directory."""
import sys, os
_HERE = os.path.dirname(os.path.abspath(__file__))   # underscore: `from route_lib import *` must not overwrite the importer's own HERE (86th pass: three agents' snapshots landed here)
sys.path.insert(0, _HERE)
from trek import *
SN = OUT + 'r16/'
os.makedirs(SN, exist_ok=True)
R12 = OUT + 'r12/'

def dump(r, label=''):
    """room id, hero bbox/z, placement entries (id, rect, z, class)"""
    tbl = r.l(A5 + 56); n = r.w(A5 + 1152)
    print('== %s room %d hero %s z %s health %d  (%d entries)' % (label, r.w(ROOM), pos(r), tuple(r.mem(0x3833c, 2)), r.w(HEALTH), n))
    for i in range(n):
        e = r.mem(tbl + 0x46 * i, 0x46)
        t = int.from_bytes(e[10:14], 'big')
        oid = r.w(t + 4) if 0x1000 < t < 0x7ffff else None
        cls = r.b(t + 22) if 0x1000 < t < 0x7ffff else None
        print('   slot %2d id %-5s rect %s z %d..%d cls %s' % (i, oid, tuple(e[0:4]), e[4], e[5], cls))
    sys.stdout.flush()

def door(r, d): return r.mem(0x6d35a + 8 * d, 8).hex()

def goto(r, bits, cond, chunk=5000, maxn=400):
    joy(r, bits)
    for _ in range(maxn):
        r.cmd('s %d' % chunk)
        if cond(pos(r)): break
    joy(r, 0); r.cmd('s 30000')
    return pos(r)

def wall(r):
    """compact one-line summary of the placement entries after the hero: id:rect/z (del = rect 255)"""
    tbl = r.l(A5 + 56); n = r.w(A5 + 1152); out = []
    for i in range(1, n):
        e = r.mem(tbl + 0x46 * i, 0x46)
        t = int.from_bytes(e[10:14], 'big'); oid = r.w(t + 4) if 0x1000 < t < 0x7ffff else None
        out.append('%s:%s/z%d-%d' % (oid, ','.join(map(str, e[0:4])) if e[0] != 255 else 'del', e[5], e[4]))
    return ' '.join(out)

def select_held(r, t):
    """Space (rucksack item panel of the held item), icon $d SELECT"""
    ruck_panel(r, t, 'space'); pick_icon_id(r, t, 0xd)
    return r.a5(1262, 2).hex()

def aim(r, bits, n=35000):
    """a short tap that turns the hero without (much) moving it; 35,000 steps moved one cell fraction (1 px)"""
    joy(r, bits); r.cmd('s %d' % n); joy(r, 0); r.cmd('s 30000')

def classes(r):
    """per placement entry: id, class template (entry+6) bytes +22 (class), +23 (subclass), +29, +12"""
    tbl = r.l(A5 + 56); n = r.w(A5 + 1152)
    for i in range(1, n):
        e = r.mem(tbl + 0x46 * i, 0x46)
        t = int.from_bytes(e[10:14], 'big'); ct = int.from_bytes(e[6:10], 'big')
        if not (0x1000 < t < 0x7ffff and 0x1000 < ct < 0x7ffff): continue
        c = r.mem(ct, 32)
        print('   id %-5s rect %s z %d..%d class(+22)=%d sub(+23)=%d b29=%d b12=%d  obj byte3(+15)=%02x' % (r.w(t + 4), tuple(e[0:4]), e[5], e[4], c[22], c[23], c[29], c[12], r.b(t + 15)))

import time, trek
def bfs_goal(snap, goal, maxdepth=6, budget=2400, tag='g', quiet=False):
    """BFS over full-length holds; goal(r, room, pos, probe_result) -> bool.  Returns (path, snapshot)"""
    tk = SN + 'bfs_%s/' % tag; os.makedirs(tk, exist_ok=True)
    seen = {}; queue = [(snap, '')]; t0 = time.time(); n = 0
    while queue and time.time() - t0 < budget:
        s, path = queue.pop(0)
        if len(path) >= maxdepth: continue
        for mv in (UP, DOWN, LEFT, RIGHT):
            r = Repl(s); room, p = hold(r, mv); key = (room, p)
            if key in seen: r.close(); continue
            seen[key] = path + trek.NAMES[mv]; n += 1
            s2 = tk + 'n%d.snap' % n; r.snap(s2); hp = r.w(HEALTH)
            res = probe(r); ok = goal(r, room, p, res); r.close()
            if not quiet: print('  %-10s room %2d pos %s health %d%s' % (path + trek.NAMES[mv], room, p, hp, ' probe %s %s' % (res[0], res[1]) if res else ''), flush=True)
            if ok: return path + trek.NAMES[mv], s2
            queue.append((s2, path + trek.NAMES[mv]))
    return None

KEYSITES.extend([0x104e2, 0x10514])   # verb 10 CLEAR FLAG and its sound-$12 branch (Tally's default site list is this same list object)
