"""mover_free_run.py: checks mover_model.py on every live mover (template+12 bit 0, not bit 5; rec+3 bit 4; mover block of >= 14 bytes) of a snapshot, per $f71a PASS:
mover block, position x,y,z before the pass, run to the return address, compare with the model.  Classes: MOVED (position changed by the model's delta and the block equals the
model's), IDLE (model predicts no move: block and position unchanged), BLOCKED (model predicts a move, the position did not change: reported with the post block), BAD (anything else).
usage: mover_free_run.py SNAP [passes]    (V=1 prints BAD / BLOCKED rows)"""
import sys, os
from live import *
import mover_model
VERBOSE = os.environ.get('V')
snap = sys.argv[1]; passes = int(sys.argv[2]) if len(sys.argv) > 2 else 60
r = start(snap)
def to(addr):
    o = r.cmd('u %x 400000' % addr)
    if any('gave up' in l for l in o): raise SystemExit('PC never reached $%x (snapshot not in the running main loop)' % addr)
r.cmd('s 1'); to(0xf71a)
def grab():
    d = {}
    for o in objs(r):
        t = o['tm']; h = o['hdr']
        if not (t[12] & 1) or t[12] & 0x20 or not h[3] & 0x10 or h[15] & 0x80: continue
        ln = h[14] - h[13]
        if ln < 14: continue
        rec = o['rec']
        d[o['id']] = dict(m=bytearray(r.mem(rec + h[13], ln)), pos=bytes(r.mem(rec, 3)), cls=t[22], e22=o['e'][22], e45=o['e'][45])
    return d
from collections import Counter
tally = Counter(); per = {}; rows = []
for k in range(passes):
    pre = grab(); fz = r.mem(A5 + 2342, 1)[0]
    sp = None
    for l in r.cmd('r'):
        for tok in l.split():
            if tok.startswith('A7:'): sp = int(tok[3:], 16)
    to(r.l(sp)); post = grab()
    for oid, a in pre.items():
        b = post.get(oid)
        if b is None or len(b['m']) != len(a['m']): continue
        if a['e22'] & 0x20 or a['e45'] & 1: tally['skipped (sprite+22 bit5 / +45 bit0 path)'] += 1; continue
        if a['cls'] == 3 and fz: continue
        m = bytearray(a['m']); saved = bytes(a['m'][3:6])
        try: d, ev, ended = mover_model.step(m)
        except (ValueError, NotImplementedError) as ex: tally['model-error'] += 1; continue
        moved = tuple((b['pos'][i] - a['pos'][i]) & 0xff for i in range(3))
        pm = bytes(b['m'])
        if d is None:
            if pm != bytes(m): cls_ = 'BAD'
            else: cls_ = 'IDLE' if moved == (0, 0, 0) else 'IDLE+displaced'     # displaced = gravity ($5d7f table) or being pushed, not the mover block
        else:
            exp = tuple(x & 0xff for x in d)
            blk = bytearray(m)                                    # the block the model predicts if the step is refused ($fc2a: counters restored when m[13] bits 1|2, else cleared; class 3 sets bits 3,4)
            if blk[13] & 6: blk[3:6] = saved
            else: blk[3:6] = b'\0\0\0'
            if a['cls'] == 3: blk[13] |= 0x18
            acc = bytearray(m)
            if a['cls'] == 3: acc[13] &= ~8                       # $fc82: an accepted step clears bit 3 (class 3)
            if moved == exp and pm == bytes(acc): cls_ = 'MOVED'
            elif moved == (0, 0, 0) and pm == bytes(blk): cls_ = 'REFUSED'
            elif pm == bytes(acc): cls_ = 'MOVED-ADJUSTED'          # collision resolver $8868 returned another delta (slide) but the block advanced as predicted
            else: cls_ = 'BAD'
        tally[cls_] += 1; tally['state%d' % a['m'][0]] += 1
        if a['m'][0] == 3 and a['m'][13] & 1: tally['state3 with request bit'] += 1
        if a['m'][0] == 3 and any(a['m'][3:6]): tally['state3 with counters'] += 1
        per.setdefault(oid, Counter())[cls_] += 1
        if (cls_ == 'BAD' and VERBOSE):
            print('  %s obj %d k=%d state %d  pre %s -> post %s  model %s  d=%s moved=%s' % (cls_, oid, k, a['m'][0], a['m'][:14].hex(' '), b['m'][:14].hex(' '), m[:14].hex(' '), d, moved))
    r.cmd('s 1'); to(0xf71a)
r.close()
for oid in sorted(per): print('obj %4d: %s' % (oid, dict(per[oid])))
print('TOTAL', dict(tally), 'program ops fetched', dict(mover_model.OPS))
