"""g2 lib: thin layer over route_lib/route_chain (shared ../lib); everything it writes goes under $CAD_OUT (88th pass, D3/G2)."""
import sys, os
D3 = os.path.dirname(os.path.abspath(__file__))
M68 = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(D3, '..', '..', '..', '..', '..', '..', '..', '..')))
os.environ['M68000_ROOT'] = M68
sys.path.insert(0, D3 + '/../lib')      # shared lib/ (the repo's action/ and verbs2/ copies write to scratchpad/.../secrets_out: these write under $CAD_OUT)
from route_chain import *      # Route, route_lib (Repl, A5, joy, pos, hold, goto, probe, Tally, ...), K
import h as H_
from ov import ww, wb
os.makedirs(H_.TMP, exist_ok=True)

def hp(r): return r.w(HEALTH)
def zz(r): return tuple(r.mem(0x3833c, 2))
def st(r): return 'room %d pos %s z(top,bot) %s health %d' % (r.w(ROOM), pos(r), zz(r), r.w(HEALTH))

def ent(r, oid):
    tbl = r.l(A5 + 56); n = r.w(A5 + 1152)
    for i in range(n):
        e = r.mem(tbl + 0x46 * i, 0x46)
        t = int.from_bytes(e[10:14], 'big')
        if 0x1000 < t < 0x7ffff and r.w(t + 4) == oid: return (tuple(e[0:4]), e[5], e[4])
    return None

def have(r, oid): return any(a == oid for a, b in type8(r)['recs'])

def ruck_ids_data(r):
    t8 = type8(r); return [a for a, b in t8['recs'][:t8['count']]]

def slot_map(r):
    """occupied rucksack slots -> (slot, object id): the type-8 index words are [flag.w][ofs.w] per slot (slot 0 never used, flag 0 = free: slot 1 frees when the first item goes), the data records hold the ids"""
    a0 = r.l(A5 + 96) + 8 * 0x12; idx, dat = r.l(a0), r.l(a0 + 4)
    return [(k, r.w(dat + r.w(idx + 4 * k + 2))) for k in range(1, 40) if r.w(idx + 4 * k) != 0][:r.b(A5 + 2438)]

def slot_ids(r): return [i for k, i in slot_map(r)]

def select_item(r, t, oid):
    """Return (the item grid), RIGHT pulses until the cursor slot 2122(A5) (1-based) holds oid, FIRE -> that item's icon panel (asserted: item word 1236(A5) == oid)"""
    sm = dict((i, k) for k, i in slot_map(r)); assert oid in sm, (oid, sm); want = sm[oid]
    tap(r, t, 0x1c)
    for _ in range(len(sm) + 1):
        if r.w(A5 + 2122) == want: break
        pulse(r, t, RIGHT)
    assert r.w(A5 + 2122) == want, (r.w(A5 + 2122), sm)
    t.joy(FIRE); t.run(40000); t.joy(0); t.run(90000)
    assert r.w(A5 + 1236) == oid, (r.w(A5 + 1236), oid)
    return icons(r)

def live_rec(r, oid, typ=6):
    row = r.l(A5 + 96) + 0x12 * typ; idx, dat = r.l(row), r.l(row + 4)
    e = r.l(idx + 4 * oid)
    return None if (e >> 16) == 0 else dat + (e & 0x1ffff)

def live_body(r, oid):
    a = live_rec(r, oid); return None if a is None else a + r.b(a + 12)

def ruck_ids(r): return sorted(slot_ids(r))
