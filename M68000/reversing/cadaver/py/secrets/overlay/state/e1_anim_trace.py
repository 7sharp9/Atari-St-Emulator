"""e1_anim_trace.py: PROVES the animation interpreter pseudocode (anim_model.py) against a live object.
Snapshot: L0 room 12 (agent_door22/exp22_poke.snap): objects 170-177 halted ($fe, rec+15 bit0 set).  Inject event 9 [rec 170][word $00a9] at the ring write pointer,
step main-loop passes ('s 1' + 'u af10'), record anim block+rec+15 at every pass entry, and compare each transition with anim_model.step.
usage: e1_anim_trace.py [passes]"""
import sys
from live import *
from st import St
import anim_model
passes = int(sys.argv[1]) if len(sys.argv) > 1 else 40
SNAP = SN('WALL12', 'scratchpad/cadaver/agent_door22/exp22_poke.snap')
s = St(SNAP)
rec = s.obj(170); tm = bytes(s.mem(s.tmpl((s.b(rec + 6) << 8) | s.b(rec + 7)), 160))
r = start(SNAP)
def obs():
    b = r.mem(rec, 52)
    return bytearray(b[0x2a:0x34]), b[15], r.mem(A5 + 1154, 2)
def inject(op, recptr, word):
    wp = r.l(A5 + 304); n = r.w(A5 + 1154)
    for i, (sz, v) in enumerate(((2, op), (4, recptr), (2, word))): pass
    r.cmd('w %x %04x%04x' % (wp, op, recptr >> 16), 'w %x %04x%04x' % (wp + 4, recptr & 0xffff, word))
    r.cmd('w %x %08x' % (A5 + 304, wp + 8))
    ww(r, A5 + 1154, n + 1)
# let the loop run twice so the trace starts from a pass entry
r.cmd('s 1'); r.cmd('u af10 400000')
rows = []
inj = 3
ev13 = None
for k in range(passes):
    if k == inj: inject(9, rec, 0x00a9)
    o = obs()
    if r.mem(rec + 4, 2) != b'\x00\xaa': break                 # record 170 was freed (the heap compacted: another object now sits at this address)
    rows.append(o)
    if o[0][3] == 4 and o[0][0] == 0 and ev13 is None:           # next pass runs step 4 = (f8 01): catch the event push at $00b0f0
        r.cmd('u b0f0 100000'); wp = r.l(A5 + 304); ev13 = r.mem(wp - 8, 8).hex(' ')
    r.cmd('s 1'); out = r.cmd('u af10 400000')
deleted_at = len(rows)
r.close()
ok = bad = goani = 0
print('pass  anim block                  +15  model-check')
for k in range(len(rows) - 1):
    a, f, _ = rows[k]; a2, f2, _ = rows[k + 1]
    note = ''
    pred = bytearray(a); pf = f
    if not f & 1:                                                 # $af10 skips an object whose rec+15 bit 0 is set
        ev, st = anim_model.step(tm, pred); pf = f | (1 if st else 0)
        if ev: note = 'events %s' % ev
    if f2 & 1 == 0 and pred[0] == 0xfe and pf & 1:                # GOANI ($0101d0) runs later in the same frame: $fe -> 0, step + 1, stop bit cleared
        pred[0] = 0; pred[3] += 1; pf &= ~1; note += ' GOANI'; goani += 1
    good = (bytes(pred[0:4] + pred[8:10]) == bytes(a2[0:4] + a2[8:10])) and (pf & 1) == (f2 & 1) and bytes(pred[4:8]) == bytes(a2[4:8])
    ok += good; bad += (not good)
    print('%3d   %s   %02x   %s %s' % (k, a.hex(' '), f, 'match' if good else 'MISMATCH pred=%s/%02x' % (pred.hex(' '), pf), note))
print('transitions matching the model: %d of %d (GOANI resumes: %d); record 170 freed after pass %d; event pushed by the f8 step: %s' % (ok, ok + bad, goani, deleted_at, ev13))
a, f, _ = rows[-1]; pred = bytearray(a); ev, st = anim_model.step(tm, pred)
print('last observed pass entry %s, model next state %s events %s stop=%s (then script DELETE frees the record: matches the vanished id)' % (a.hex(' '), pred.hex(' '), ev, st))
