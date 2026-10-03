"""x11_anim_gates.py: what gates the animation pass $00af10 (live pokes, 10 main-loop passes each, count of distinct anim-block states; the control is the unpoked run).
 CAVERN torch 413 (template 86, class 0): control; rec+15 bit 0 set; anim byte $fe with bit 0 clear; anim byte $ff with bit 0 clear; template+12 bit 2 cleared; rec+3 bit 7 set (hidden, poke only: sprite entry stays: no effect expected).
 L1 room 29 (inj_room29.snap) class-3 creatures 664/665 and class-0 object 493: byte 2342(A5) (the FREEZE spell countdown) non-zero stops the class-3 anim passes only.
usage: x11_anim_gates.py"""
import sys
from lab import *
def animstates(r, oid, n=10):
    out = []
    for _ in range(n):
        rec = rec_of(r, oid); h = r.mem(rec, 16)
        out.append(bytes(r.mem(rec + h[14], 10))); passes(r, 1)
    return out
def run(label, setup, oid=413, snap=SN('CAVERN', 'scratchpad/cadaver/gameplay_empire.snap'), n=10):
    r = start(snap); passes(r, 2); setup(r)
    st = animstates(r, oid, n)
    print('%-58s distinct anim states in %d passes: %d (first %s)' % (label, n, len(set(st)), st[0].hex(' ')))
    r.close()
    return len(set(st))
def rec15(r, oid): return rec_of(r, oid) + 15
def tmplp(r, oid): return sprites(r)[oid]['e'][6:10]
run('control (torch 413 running)', lambda r: None)
run('rec+15 bit 0 set (poke)', lambda r: wb(r, rec15(r, 413), r.mem(rec15(r, 413), 1)[0] | 1))
def a_fe(r):
    rec = rec_of(r, 413); h = r.mem(rec, 16); wb(r, rec + h[14], 0xfe)
run('anim byte $fe, +15 bit 0 clear (poke)', a_fe)
def a_ff(r):
    rec = rec_of(r, 413); h = r.mem(rec, 16); wb(r, rec + h[14], 0xff)
run('anim byte $ff, +15 bit 0 clear (poke)', a_ff)
def t_bit2(r):
    ta = int.from_bytes(tmplp(r, 413), 'big'); wb(r, ta + 12, r.mem(ta + 12, 1)[0] & ~4)
run('template+12 bit 2 cleared (poke)', t_bit2)
run('rec+3 bit 7 set by poke only (sprite entry untouched)', lambda r: wb(r, rec_of(r, 413) + 3, 0x80))
S = SN('ROOM29', 'scratchpad/cadaver/s86/a7/snaps/inj_room29.snap')
for oid in (664, 493):
    run('L1 room 29 obj %d, 2342(A5)=0' % oid, lambda r: None, oid, S)
    run('L1 room 29 obj %d, 2342(A5)=5 (FREEZE)' % oid, lambda r: wb(r, A5 + 2342, 5), oid, S)
