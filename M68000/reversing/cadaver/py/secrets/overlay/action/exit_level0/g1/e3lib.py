"""e3 lib: thin layer over route_chain, everything written under the OUTDIR a script is given (88th pass, E3)."""
import sys, os
E3 = os.path.dirname(os.path.abspath(__file__))
M68 = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(E3, '..', '..', '..', '..', '..', '..', '..', '..')))
os.environ['M68000_ROOT'] = M68
sys.path.insert(0, E3 + '/../lib')      # shared lib/ (the repo's action/ libs write to scratchpad/.../secrets_out/action: this copy writes under $CAD_OUT)
from route_chain import *      # Route, route_lib (Repl, A5, joy, pos, hold, goto, probe, Tally, aim, ...), K
def hp(r): return r.w(HEALTH)
def zz(r): return tuple(r.mem(0x3833c, 2))
def st(r): return 'room %d pos %s z(top,bot) %s health %d xp %d' % (r.w(ROOM), pos(r), zz(r), r.w(HEALTH), r.l(A5 + 1192))
def ruck(r): t8 = type8(r); return t8['recs'][:t8['count']]
def have(r, oid): return any(a == oid for a, b in type8(r)['recs'])
def ent(r, oid):
    tbl = r.l(A5 + 56); n = r.w(A5 + 1152)
    for i in range(n):
        e = r.mem(tbl + 0x46 * i, 0x46); t = int.from_bytes(e[10:14], 'big')
        if 0x1000 < t < 0x7ffff and r.w(t + 4) == oid: return (tuple(e[0:4]), e[5], e[4])
    return None

def objrec(r, oid, n=24):
    tbl = r.l(A5 + 56); cnt = r.w(A5 + 1152)
    for i in range(1, cnt):
        e = r.mem(tbl + 0x46 * i, 0x46); t = int.from_bytes(e[10:14], 'big')
        if 0x1000 < t < 0x7ffff and r.w(t + 4) == oid: return t, r.mem(t, n).hex(), tuple(e[0:6])
    return None

def jumpw(r, dirbits, steps=520000, chunk=10000, watch=(211, 212), release=True):
    """hold fire+dir for `steps`; log (steps, pos, z, health, changed watched object records)"""
    base = {o: (objrec(r, o) or (0, None))[1] for o in watch}
    joy(r, FIRE | dirbits); log = []; n = 0
    while n < steps:
        r.cmd('s %d' % chunk); n += chunk
        cur = {o: (objrec(r, o) or (0, None))[1] for o in watch}
        ch = [o for o in watch if cur[o] != base[o]]
        if ch: log.append((n, pos(r), zz(r), hp(r), ch)); base.update(cur)
    if release: joy(r, 0)
    return log
