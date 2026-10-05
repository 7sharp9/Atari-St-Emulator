#!/usr/bin/env python3
"""Check the sequencer's note/pitch encoding against MAME: replay the stream bytes the HuC6280 fetched (rtrace log F/G/D lines),
predict the YM2151 KC/KF register values of every note of channels 0-7 from the documented encoding, and compare with the KC/KF
writes MAME saw (E lines, `ym2151 a 28+ch / d KC`, `a 30+ch / d KF`).

Encoding (read from $E6A5..$E6FE, $E712..$E75F, $E80F, tables F827/F836):
  byte < $70            : note length in ticks ($23A0,x); remembered until the next length byte
  $70-$8f and $e0-$ff   : note, nibble = (byte - $70/$c0) & $0f ; semitone p = nibble + 12*octave + transpose ; octave starts at 4
  $91/$92/$93 n         : octave +1 / -1 / = n (clamped 0..7)       $d7 kf tr : fine tune KF = kf, transpose tr (semitones, 8-bit add)
  KC = ((p div 12 + F836[p mod 12]) << 4) | F827[p mod 12] ,  KF = kf  (written to $28+ch / $30+ch)
Unmodelled opcodes ($9e-$a2 pitch bends, $b6 portamento) switch the channel to 'unmodelled' for the rest of that run.
usage: predict_kc.py out/rt_04.log [...]
"""
import sys, os, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import songs as S
F827 = [0x0e, 0x00, 0x01, 0x02, 0x04, 0x05, 0x06, 0x08, 0x09, 0x0a, 0x0c, 0x0d]
F836 = [-1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

def kc_of(p):
    p &= 0xff
    return (((p // 12) + F836[p % 12]) & 0xf) << 4 | F827[p % 12]

def run(path):
    st = {}
    last = {}
    pred = collections.defaultdict(list)      # ch -> [(KC, KF, pos)]
    seen = collections.defaultdict(list)      # ch -> [(KC, KF)]
    regs = {}
    kc = {}
    unmod = collections.Counter()
    opcount = collections.Counter()
    for l in open(path):
        p = l.split()
        if not p: continue
        k = p[0]
        if k in ('F', 'G'):
            ch = int(p[1]); pos = int(p[2], 16) + int(p[3]); b = int(p[4], 16)
            last[ch] = (pos, b)
            s = st.setdefault(ch, dict(oct=4, tr=0, kf=0))
            if 0x70 <= b < 0x90 or b >= 0xe0:
                nib = (b - 0x70) & 0xf if b < 0x90 else (b - 0xc0) & 0xf
                if ch < 8:
                    pred[ch].append((kc_of(nib + 12 * s['oct'] + s['tr']), s['kf'], pos))
        elif k == 'D':
            ch = int(p[1]); idx = int(p[2])
            pos, b = last[ch]
            s = st.setdefault(ch, dict(oct=4, tr=0, kf=0))
            a1, a2 = S.rb(pos + 1), S.rb(pos + 2)
            opcount[idx] += 1
            if idx == 1: s['oct'] = min(7, s['oct'] + 1)
            elif idx == 2: s['oct'] = max(0, s['oct'] - 1)
            elif idx == 3: s['oct'] = a1 if a1 < 8 else 7
            elif idx == 71: s['kf'] = a1; s['tr'] = a2
            elif idx in (14, 15, 16, 17, 18, 38): unmod[(ch, idx)] += 1
        elif k == 'E' and p[1] == 'ym2151':
            if p[2] == 'a': regs['a'] = int(p[3], 16)
            else:
                r = regs.get('a', -1); v = int(p[3], 16)
                if 0x28 <= r < 0x30: kc[r - 0x28] = v
                elif 0x30 <= r < 0x38 and (r - 0x30) in kc: seen[r - 0x30].append((kc.pop(r - 0x30), v))
    return pred, seen, unmod

if __name__ == '__main__':
    tot = ok = 0
    for path in sys.argv[1:]:
        pred, seen, unmod = run(path)
        for ch in sorted(pred):
            P = [(a, b) for a, b, _ in pred[ch]]
            O = seen.get(ch, [])
            # the observed list starts with the writes of the $d7 / $93 pitch-apply calls of the channel's setup opcodes (KC=$fe, $20): align on the tail
            extra = len(O) - len(P)
            O2 = O[extra:] if extra >= 0 else O
            P2 = P if extra >= 0 else P[-len(O):] if O else []
            n = len(P2)
            m = sum(1 for i in range(n) if P2[i] == O2[i])
            tot += n; ok += m
            bad = [i for i in range(n) if P2[i] != O2[i]]
            flag = '' if not bad else '   MISMATCH first at %d: pred %s obs %s' % (bad[0], P2[bad[0]], O2[bad[0]])
            print('%s ch%d notes %3d observed KC/KF pairs %3d (leading extra %d) equal %3d/%d%s%s' % (os.path.basename(path), ch, len(P), len(O), extra, m, n, ' unmodelled-ops=%s' % dict((k[1], v) for k, v in unmod.items() if k[0] == ch) if any(k[0] == ch for k in unmod) else '', flag))
    print('TOTAL compared %d equal %d' % (tot, ok))
