"""anim_free_run.py: check of anim_model.py on every animated (template+12 bit 2, not bit 5) live object of a snapshot, per $af10 PASS: read each object's anim block and rec+15 at the
entry of $af10, run to its return address (the caller's next instruction) and compare the state after the pass with the model (so nothing between passes can interfere).
Objects with GOANI/STOPANI-style outside writers in the same pass cannot occur (the consumer runs after the pass).  usage: anim_free_run.py SNAP [passes]   (V=1 prints mismatches)"""
import sys, os
from live import *
import anim_model
VERBOSE = os.environ.get('V')
snap = sys.argv[1]; passes = int(sys.argv[2]) if len(sys.argv) > 2 else 60
r = start(snap)
def to(addr):
    o = r.cmd('u %x 400000' % addr)
    if any('gave up' in l for l in o): raise SystemExit('PC never reached $%x (snapshot not in the running main loop): %s' % (addr, o[-1]))
r.cmd('s 1'); to(0xaf10)
targets = []
for o in objs(r):
    t = o['tm']
    if not t[12] & 4 or t[12] & 0x20 or o['hdr'][15] & 0x80: continue
    targets.append((o['id'], o['rec'], bytes(r.mem(int.from_bytes(o['e'][6:10], 'big'), 0x300)), t[22]))
def grab():
    """fresh per pass: ids/records/templates can change between passes (verb 36 clones reuse ids 900+, the heap compacts)"""
    d = {}
    for o in objs(r):
        t = o['tm']
        if not t[12] & 4 or t[12] & 0x20 or o['hdr'][15] & 0x80: continue
        rec = o['rec']; h = o['hdr']
        d[o['id']] = (bytearray(r.mem(rec + h[14], 10)), h[15], h[3], bytes(r.mem(int.from_bytes(o['e'][6:10], 'big'), 0x300)), t[22])
    return d
res = {}
for k in range(passes):
    pre = grab(); fz = r.mem(A5 + 2342, 1)[0]                     # $af10 skips class-3 objects while byte 2342(A5) is non-zero
    sp = None
    for l in r.cmd('r'):
        for tok in l.split():
            if tok.startswith('A7:'): sp = int(tok[3:], 16)
    ret = r.l(sp) if sp else 0x6b12
    to(ret)
    post = grab()
    for oid in pre:
        a, f, _, tm, cls = pre[oid]
        if oid not in post: continue
        a2, f2, _, tm2, _ = post[oid]
        if tm2 != tm: continue                                    # a different object now owns this id
        res.setdefault(oid, [0, 0, set(), cls])
        if cls == 3 and fz: continue
        pred = bytearray(a); pf = f
        if not f & 1:
            ev, st = anim_model.step(tm, pred); pf = f | (1 if st else 0)
            res[oid][2].add(tm[0x28 + 2 * a[3]] if a[0] == 0 else -1)
        good = bytes(pred[0:4] + pred[8:10]) == bytes(a2[0:4] + a2[8:10]) and (pf & 1) == (f2 & 1) and bytes(pred[4:8]) == bytes(a2[4:8])
        res[oid][0] += good; res[oid][1] += 1
        if not good and VERBOSE: print('  obj %d k=%d pre %s f=%02x -> post %s f=%02x pred %s pf=%02x' % (oid, k, a.hex(' '), f, a2.hex(' '), f2, pred.hex(' '), pf))
    r.cmd('s 1'); to(0xaf10)
r.close()
T = [0, 0]
for oid in sorted(res):
    ok, n, ops, cls = res[oid]
    T[0] += ok; T[1] += n
    print('obj %4d (class %02x): %3d of %3d passes match; ops seen %s' % (oid, cls, ok, n, ' '.join('%02x' % x for x in sorted(x for x in ops if x >= 0))))
print('TOTAL %d of %d' % tuple(T))
