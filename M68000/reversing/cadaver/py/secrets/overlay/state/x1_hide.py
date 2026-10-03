"""x1_hide.py: PROVES rec+3 bit 7 (hidden) and bit 3 (deferred show) live (verbs 26 HIDE / 1 SHOW run by the real consumer, from a scratch script written over object 168's event-16 block).
Part A (CAVERN, room 0): HIDE then SHOW the silver coin 412 (on screen): sprite entry, counters 1148/1150/1152, rec+3, rendered pixels in its box.
Part B: HIDE the animated torch 413: its anim block freezes while hidden (no sprite entry, so $af10 never visits it) and resumes after SHOW.
Part C: HIDE then SHOW object 2 (room 0x22, not the current room): SHOW sets bit 3 instead of placing; teleporting to room 0x22 (event 5 of object 86) places it and clears bit 3; a control run with HIDE only leaves it absent.
usage: x1_hide.py"""
import sys
from lab import *
SNAP = SN('CAVERN', 'scratchpad/cadaver/gameplay_empire.snap')
def mk():
    r = start(SNAP); passes(r, 2); return r
def run_script(r, body, owner=168, ev=16, n=3):
    w = set_block(r, owner, ev, body); fire(r, owner, ev, w); passes(r, n)
def box(r, oid):
    e = sprites(r)[oid]['e']
    return e
# ---------- Part A (a control timeline with no-op scripts (verb 46) gives the pixels that change by themselves, so the diffs below are the coin only)
def timeline(b1, b2, tag):
    r = mk(); pics = []
    rec = rec_of(r, 412)
    run_script(r, b1); pics.append((snap_png(r, 'x1_%s1' % tag), 412 in sprites(r), counters(r), r.mem(rec_of(r, 412) + 3, 1)[0]))
    run_script(r, b2); pics.append((snap_png(r, 'x1_%s2' % tag), 412 in sprites(r), counters(r), r.mem(rec_of(r, 412) + 3, 1)[0]))
    r.close(); return pics
ctl = timeline([0x2e], [0x2e], 'ctl'); act = timeline([0x1a, 0x01, 0x9c], [0x01, 0x01, 0x9c], 'act')
for k, name in ((0, 'HIDE(412)'), (1, 'SHOW(412)')):
    d = np.argwhere((ctl[k][0] != act[k][0]).any(axis=2))
    print('A after %-9s: +3=%02x  in sprite array %s  counters %s  pixels differing from the no-op timeline: %d%s' % (name, act[k][3], act[k][1], act[k][2], len(d), (' (bbox x %d-%d y %d-%d)' % (d[:, 1].min(), d[:, 1].max(), d[:, 0].min(), d[:, 0].max())) if len(d) else ''))
# ---------- Part B
r = mk()
def anim(r, oid):
    rec = rec_of(r, oid); return bytes(r.mem(rec + r.mem(rec + 14, 1)[0], 10)).hex(' ')
trace = []
for k in range(6): trace.append(anim(r, 413)); passes(r, 1)
print('B torch 413 running  :', trace[:3], '...', 'distinct states in 6 passes: %d' % len(set(trace)))
run_script(r, [0x1a, 0x01, 0x9d], n=2)
fro = []
for k in range(8): fro.append(anim(r, 413)); passes(r, 1)
print('B torch 413 hidden   : in sprite array %s; distinct anim states in 8 passes: %d (%s)' % (413 in sprites(r), len(set(fro)), fro[0]))
run_script(r, [0x01, 0x01, 0x9d], n=1)
res = []
for k in range(8): res.append(anim(r, 413)); passes(r, 1)
print('B torch 413 shown    : in sprite array %s; distinct anim states in 8 passes: %d' % (413 in sprites(r), len(set(res))))
r.close()
# ---------- Part C
def partC(do_show, label):
    r = mk(); rec2 = rec_of(r, 2)
    print('C%s obj 2: room byte %02x, +3=%02x, current room %d, in sprite array %s' % (label, r.mem(rec2 + 10, 1)[0], r.mem(rec2 + 3, 1)[0], room(r), 2 in sprites(r)))
    run_script(r, [0x1a, 0x00, 0x02], n=2)
    print('C%s after HIDE(2): +3=%02x' % (label, r.mem(rec_of(r, 2) + 3, 1)[0]))
    if do_show:
        run_script(r, [0x01, 0x00, 0x02], n=2)
        print('C%s after SHOW(2) from room 0: +3=%02x (bit 7 cleared, bit 3 set), in sprite array %s' % (label, r.mem(rec_of(r, 2) + 3, 1)[0], 2 in sprites(r)))
    fire(r, 86, 5); 
    for k in range(40):
        passes(r, 1)
        if room(r) == 0x22: break
    passes(r, 6)
    s = sprites(r)
    print('C%s after teleport: room %d  obj 2 in sprite array %s  +3=%02x  live ids %s' % (label, room(r), 2 in s, r.mem(rec_of(r, 2) + 3, 1)[0], sorted(s)[:10]))
    r.close()
partC(True, ' (HIDE, SHOW)')
partC(False, ' (HIDE only)')
