"""a3: probe.py -- helper library: run a snapshot to a producer push site with `bp`, decode the queue entry that was just written ([op.w][ptr.l][word.w][long.l if bit 15]),
resolve ptr to a type-6 object id / type-3 room id, and read 1166(A5) (current room id word).  import as `from probe import *`."""
import sys, os, re
CWD0 = os.getcwd()
def absp(p): return p if os.path.isabs(p) else os.path.abspath(os.path.join(CWD0, p))
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../../..'))
OUTDIR = os.environ.get('OUTDIR') or os.path.join(ROOT, 'scratchpad/cadaver/s91_events'); os.makedirs(OUTDIR, exist_ok=True)   # scratch output (callcap json, caches, scan listings)
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay/verbs2')
import h as HH
from h import *
os.chdir(ROOT); HH.TMP = OUTDIR
A5 = HH.A5

def live_res(h, t, i):
    """live type-t record address of id i (index table entries are read from RAM now, not from the snapshot file: DELETE verbs move records)"""
    idx, dat, cnt = h.rows[t]
    e = h.r.l(idx + 4 * i)
    return None if (e >> 16) == 0 else dat + (e & 0x1ffff)

def ptr_name(h, p):
    """what a pointer in a queue entry is: type-6 object record id (word at +4, checked against the live index), type-3 room record id, or raw"""
    if p < 0x1000 or p > 0x7ffff: return '$%06x' % p
    i = h.r.w(p + 4)
    if i < 1000 and live_res(h, 6, i) == p: return 'obj %d' % i
    idx, dat, cnt = h.rows[3]
    for k in range(min(cnt, 100)):
        if live_res(h, 3, k) == p: return 'room %d' % k
    return '$%06x' % p

def regs(r):
    d = {}
    for l in r.cmd('r'):
        for m in re.finditer(r'([DA]\d):([0-9a-f]{8})', l): d[m.group(1)] = int(m.group(2), 16)
    return d

def entry_at_push(h, long4=False):
    r = h.r
    wp = r.l(A5 + 304); n = 12 if long4 else 8
    b = r.mem(wp - n, n)
    op = int.from_bytes(b[0:2], 'big'); ptr = int.from_bytes(b[2:6], 'big'); word = int.from_bytes(b[6:8], 'big')
    lg = int.from_bytes(b[8:12], 'big') if long4 else None
    return op, ptr, word, lg

def bp_push(h, site, cap=3000000, long4=False):
    out = h.r.cmd('bp %x %d' % (site, cap))
    hit = any('hit' in l.lower() and 'break' in l.lower() for l in out)
    if not hit: return None
    op, ptr, word, lg = entry_at_push(h, long4)
    return dict(op=op, ptr=ptr, ptrname=ptr_name(h, ptr), word=word, long4=lg, long4name=(ptr_name(h, lg) if lg else None), regs=regs(h.r), room1166=h.r.w(A5 + 1166), cur_room_rec=h.r.l(A5 + 164))

def follow_consumer(h, entry, event, max_gates=40):
    """after bp_push stopped at a push site: run the consumer and report EVERY gate call ($fe30) it makes for this entry (same object pointer and event byte), in order, with the operand bytes
    at A1 (gate operands first), the entry word 1156(A5) and whether the gate accepted (fe36 reached) or rejected (fe64 reached) within 22 steps."""
    r = h.r; res = []
    for _ in range(max_gates):
        out = r.cmd('bp fe30 200000')
        if not any('hit' in l.lower() and 'break' in l.lower() for l in out): break
        g = regs(r)
        ptr = g['A0']; ev = g['D6'] & 0xff
        if not (ev == event and ptr == entry['ptr']):
            continue
        a1 = g['A1']; operand = r.mem(a1, 4).hex(); word = r.w(A5 + 1156)
        out = r.cmd('hits 22 fe36 fe64')
        d = {}
        for l in out:
            t = l.split()
            if len(t) >= 2 and t[0].startswith('$'): d[int(t[0][1:], 16)] = int(t[1])
        res.append(dict(ptrname=ptr_name(h, ptr), event=ev, word=word, operand=operand, accepted=d.get(0xfe36, 0) > 0, rejected=d.get(0xfe64, 0) > 0))
    return res
