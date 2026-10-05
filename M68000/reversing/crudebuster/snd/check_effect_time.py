#!/usr/bin/env python3
"""Effect-mode time unit: a duration byte d (< $80) in an effect stream lasts d*256/436 IRQ2 periods ($23B0 = d, low byte 0; every IRQ2 and every timer IRQ subtracts $01/$02 = 2*$DA = 436).
Predict the frame distance between consecutive OKI1 starts (opcode $CC) of every effect id with >= 2 starts and compare with the frames of the first OKI byte of each start in the sweep log.
IRQ2 per frame = measured 8.594 (21485 IRQ2 in 2500 frames, irq_play1)."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import songs as S, static_streams as SS, analyze_sweep as A
blocks = A.parse(os.path.join(HERE, 'out', 'sw_all.log'))
irq_per_frame = 21485 / 2500.0
tot = 0; worst = 0; rows = []
for i in range(1, S.MAXID + 1):
    p, h, chans, q = S.header(i)
    if h[2]: continue
    for ch, a in chans:
        if ch != 11: continue
        ev, loops = SS.decode(a, ch)
        t = 0.0; starts = []
        for e in ev:
            if e[0] == 'dur': t += e[1] * 256 / 436.0
            elif e[0] == 'oki1': starts.append(t)
        if len(starts) < 2: continue
        b = blocks[i]; w = A.decode(b['ev'])
        fr = []
        st = None
        for f, c, r, v in w:
            if c != 'oki1': continue
            if st is not None: st = None; continue
            if v & 0x80: fr.append(f - b['send']); st = v
        if len(fr) < len(starts): continue
        # stub phrases are retried 4x within the same IRQ2 burst: only compare the first start of each group
        dp = [(starts[k] - starts[0]) / irq_per_frame for k in range(len(starts))]
        # frames of the first attempt of each predicted start: pick the observed starts spaced by more than 2 frames
        firsts = [fr[0]]
        for f in fr[1:]:
            if f - firsts[-1] > 2: firsts.append(f)
        if len(firsts) != len(starts): continue
        do = [f - firsts[0] for f in firsts]
        dev = max(abs(x - y) for x, y in zip(dp, do))
        rows.append((i, len(starts), dev)); tot += 1; worst = max(worst, dev)
        print('%02x starts %d predicted frame offsets %s observed %s max dev %.2f' % (i, len(starts), ['%.1f' % x for x in dp], do, dev))
print('effects compared: %d, worst deviation %.2f frames' % (tot, worst))
