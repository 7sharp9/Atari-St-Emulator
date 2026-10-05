#!/usr/bin/env python3
"""Static prediction of YM2203 FM key-ons (opcode $A6 on channels 8-10) of every effect id vs MAME's key-on count (reg $28 with a slot mask) in the sweep window.
Streams with an infinite jump are reported separately (count depends on the window)."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import songs as S, static_streams as SS, analyze_sweep as A
blocks = A.parse(os.path.join(HERE, 'out', 'sw_all.log'))
tot = same = 0; loops = []
for i in range(1, S.MAXID + 1):
    p, h, chans, q = S.header(i)
    if h[2]: continue
    pred = {}; lp = False
    for ch, a in chans:
        if ch not in (8, 9, 10): continue
        ev, l = SS.decode(a, ch)
        lp |= l
        pred[ch - 8] = sum(1 for e in ev if e[0] == 'keyon')
    if not pred: continue
    r = A.summarise(blocks[i])
    obs = {k: v for k, v in r['ym2203_fm_keyon'].items()}
    pred = {k: v for k, v in pred.items() if v}
    if lp: loops.append((i, pred, obs)); continue
    tot += 1; ok = pred == obs; same += ok
    if not ok: print('MISMATCH %02x static %s MAME %s' % (i, pred, obs))
print('FM effect ids without infinite loop: %d, static key-on count per FM channel == MAME: %d' % (tot, same))
for l in loops: print('  infinite-loop stream %02x: static per-cycle %s, MAME in window %s' % l)
