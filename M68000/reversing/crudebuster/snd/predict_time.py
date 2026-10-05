#!/usr/bin/env python3
"""Check the tick/tempo model against MAME key-on times.
Model (from $E65A, $E1B0.., $E5BE..): every YM2151 timer-B IRQ (IRQ2, 8.61 per 58 Hz frame) subtracts T=$06/$07 from the 16-bit accumulator $04/$05;
when the result is <= 0 one engine tick occurs and 1250 ($04E2) is added back, so ticks per IRQ2 = T/1250.  T = tempo base ($98 lo hi) + signed $27 (latch $d0-$ff).
A note/rest lasts `length` ticks (the last byte < $70 read on that channel).  Predicted key-on frame of the n-th note = frame0 + (ticks before it) * 1250/T / (IRQ2 per frame).
usage: predict_time.py out/rt_0e.log [channel]"""
import sys, os, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import songs as S

def load(path):
    frame = 0
    ev = []   # (kind, frame, ...)
    for l in open(path):
        p = l.split()
        if not p: continue
        k = p[0]
        if k == 'FR': frame = int(p[1]); ev.append(('FR', frame))
        elif k in ('F', 'G'): ev.append((k, frame, int(p[1]), int(p[2], 16) + int(p[3]), int(p[4], 16)))
        elif k == 'D': ev.append(('D', frame, int(p[1]), int(p[2])))
        elif k == 'E': ev.append(('E', frame, p[1], p[2], int(p[3], 16)))
        elif k == 'SEND': ev.append(('SEND', frame))
    return ev

def main(path, only=None):
    ev = load(path)
    # tempo from the $98 opcodes: first one executed on channel 0 (any channel: songs set the same tempo on several)
    T = 0x78
    dur = {}
    seq = collections.defaultdict(list)      # ch -> [(start_tick, kind)]
    tick = collections.defaultdict(int)
    last = {}
    tempo_hist = []
    for e in ev:
        if e[0] in ('F', 'G'):
            _, f, ch, pos, b = e
            last[ch] = (pos, b)
            if b < 0x70: dur[ch] = b
            elif 0x70 <= b < 0x90 or b >= 0xe0:
                seq[ch].append((tick[ch], 'note')); tick[ch] += dur.get(ch, 1)
        elif e[0] == 'D':
            _, f, ch, idx = e
            pos, b = last[ch]
            if idx == 0:
                seq[ch].append((tick[ch], 'rest')); tick[ch] += dur.get(ch, 1)
            elif idx == 8 and not tempo_hist:
                T = S.rb(pos + 1) | S.rb(pos + 2) << 8; tempo_hist.append(T)
    # observed key-on frames per YM2151 channel
    obs = collections.defaultdict(list)
    areg = None
    for e in ev:
        if e[0] == 'E' and e[2] == 'ym2151':
            if e[3] == 'a': areg = e[4]
            elif areg == 0x08 and e[4] & 0x78: obs[e[4] & 7].append(e[1])
    irq_per_frame = 500.0 / 58.0
    for ch in sorted(obs):
        if only is not None and ch != only: continue
        notes = [t for t, k in seq[ch] if k == 'note']
        n = min(len(notes), len(obs[ch]))
        if n < 3: continue
        xs = [(notes[i] - notes[0]) * 1250.0 / T / irq_per_frame for i in range(n)]
        ys = [obs[ch][i] - obs[ch][0] for i in range(n)]
        # least squares y = a + b x
        mx = sum(xs) / n; my = sum(ys) / n
        sxx = sum((x - mx) ** 2 for x in xs); sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        b = sxy / sxx; a = my - b * mx
        res = [y - (a + b * x) for x, y in zip(xs, ys)]
        print('%s ch%d T=%d notes predicted %d observed %d: observed/predicted time slope %.3f, residual max %.2f frames (1 frame = %.1f IRQ2)' % (os.path.basename(path), ch, T, len(notes), len(obs[ch]), b, max(abs(r) for r in res), irq_per_frame))

if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None)
