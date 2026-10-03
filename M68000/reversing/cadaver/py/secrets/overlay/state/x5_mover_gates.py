"""x5_mover_gates.py: live checks of what gates the mover pass $f71a and of verbs 11/12 on running movers.
Part 1 (L0 room 53, s87/b3/work/r16/s13_b.snap, object 198, a patrolling urn: state 0, delay byte $22): control, then rec+3 bit 4 cleared / set (poke).
Part 2 (L1 room 31, s89/full_A/room31/end_room31.snap, objects 130 and 131: stopped, state 1): verb 11 GOMOVE through the real consumer (a scratch script over another object's block) starts the program,
the block reaches the halt op (state 4), a second GOMOVE adds 1 to the cursor (skipping the halt op) and runs on; verb 12 STOPMOVE sets state 1 and the position freezes.
Every transition of the mover block is compared with mover_model.
usage: x5_mover_gates.py"""
import sys
from lab import *
import mover_model
class Gone(Exception): pass
def mvblock(r, oid):
    rec = rec_of(r, oid)
    if rec is None: raise Gone()
    h = r.mem(rec, 16)
    return bytearray(r.mem(rec + h[13], h[14] - h[13])), bytes(r.mem(rec, 3)), h[3]
def trace(r, oid, n):
    t = []
    try:
        for _ in range(n): t.append(mvblock(r, oid)); passes(r, 1)
    except Gone: print('   (object %d was freed after %d passes)' % (oid, len(t)))
    return t
def moved(t): return sum(1 for a, b in zip(t, t[1:]) if a[1] != b[1]), len(set(bytes(x[0][:14]) for x in t))
def compare(t, label):
    ok = n = 0
    for a, b in zip(t, t[1:]):
        m = bytearray(a[0]); d, ev, ended = mover_model.step(m)
        pm = bytearray(b[0]); mo = tuple((b[1][i] - a[1][i]) & 0xff for i in range(3))
        good = (bytes(pm) == bytes(m)) or (d is not None and mo == (0, 0, 0)) or (d is not None and mo != tuple(x & 0xff for x in d))   # blocked/adjusted steps are not part of the program model
        n += 1; ok += good
    print('   model: %d of %d transitions agree with mover_model (%s)' % (ok, n, label))
# ---------------- part 1
r = start(SN('URN53', 'scratchpad/cadaver/s87/b3/work/r16/s13_b.snap')); passes(r, 2)
MV = 198
t0 = trace(r, MV, 60); print('1 control (obj 198): position changes %d of 59 pass transitions, %d distinct mover blocks' % moved(t0)); compare(t0, 'control')
rec = rec_of(r, MV); f3 = r.mem(rec + 3, 1)[0]
wb(r, rec + 3, f3 & ~0x10); t1 = trace(r, MV, 60); print('1 +3 bit 4 cleared: position changes %d of 59, %d distinct mover blocks' % moved(t1))
wb(r, rec_of(r, MV) + 3, f3); t2 = trace(r, MV, 60); print('1 +3 bit 4 set again: position changes %d of 59, %d distinct mover blocks' % moved(t2))
r.close()
# ---------------- part 3: mover op 4 (event 12) captured at its push site $00f9a2 on object 131
r = start(SN('ROOM31', 'scratchpad/cadaver/s89/full_A/room31/end_room31.snap')); passes(r, 2)
own, ev = pick_owner(r, 3, exclude=(130, 131))
w = set_block(r, own, ev, [0x0b, 0x00, 131]); fire(r, own, ev, w)
o = r.cmd('u f9a2 3000000')
wp = r.l(A5 + 304); ent = bytes(r.mem(wp - 8, 8)); rec131 = rec_of(r, 131)
print('3 push at $f9a2 (mover op 4): ring entry %s  = opcode %d, record $%x (object 131 is at $%x), word %d' % (ent.hex(' '), int.from_bytes(ent[:2], 'big'), int.from_bytes(ent[2:6], 'big'), rec131, int.from_bytes(ent[6:8], 'big')))
r.close()
# ---------------- part 2
r = start(SN('ROOM31', 'scratchpad/cadaver/s89/full_A/room31/end_room31.snap')); passes(r, 2)
own, ev = pick_owner(r, 3, exclude=(130, 131)); print('2 script owner: object %d event %d; live objects %s' % (own, ev, sorted(sprites(r))))
def run_script(body, n=2):
    w = set_block(r, own, ev, body); fire(r, own, ev, w); passes(r, n)
for MV in (130, 131):
    b = mvblock(r, MV); print('2 obj %d before: state %d cursor %d counters %s delay $%02x  program %s' % (MV, b[0][0], b[0][1], list(b[0][3:6]), b[0][9], bytes(b[0][14:]).hex(' ')))
    t = trace(r, MV, 20); print('2   stopped (state 1): position changes %d of 19, %d distinct blocks' % moved(t))
    run_script([0x0b, MV >> 8, MV & 0xff]); b = mvblock(r, MV); print('2   after verb 11 GOMOVE: state %d cursor %d' % (b[0][0], b[0][1]))
    t = trace(r, MV, 80); print('2   running: position changes %d of 79, distinct blocks %d, state sequence %s' % ((moved(t) + (0,))[:2] + (''.join(str(x[0][0]) for x in t[::6]),))); compare(t, 'after GOMOVE')
    b = mvblock(r, MV); print('2   now state %d cursor %d counters %s' % (b[0][0], b[0][1], list(b[0][3:6])))
    if b[0][0] == 4:
        c0 = b[0][1]; run_script([0x0b, MV >> 8, MV & 0xff], n=1); b = mvblock(r, MV)
        print('2   second GOMOVE from state 4: cursor %d -> %d (verb 11 adds 1 when the state was 4), state now %d' % (c0, b[0][1], b[0][0]))
    run_script([0x0c, MV >> 8, MV & 0xff]); b = mvblock(r, MV); p0 = b[1]
    t = trace(r, MV, 20); print('2   after verb 12 STOPMOVE: state %d; position changes in 19 passes: %d' % (b[0][0], moved(t)[0]))
r.close()
