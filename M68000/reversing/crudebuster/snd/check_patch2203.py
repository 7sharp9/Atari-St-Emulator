#!/usr/bin/env python3
"""YM2203 inline patch check: opcode $97 lo hi on channels 8-10 writes the FM patch at the inline pointer ($EB39 -> $F53B).  Prediction from the ROM image:
  byte0 -> reg $B0+ch (FB/ALG); then 4 operators x 7 bytes in the slot order S1,S3,S2,S4 (offsets $00,$08,$04,$0c):
  regs $30,$40,$50,$60,$70,$80,$90 + offset + ch (DT/MUL, TL, KS/AR, AM/D1R, D2R, D1L/RR, SSG-EG).
The AM/D1R ($60) and D2R ($70) bytes are written minus 1 when their 5-bit rate is non-zero ($F63B).  Compared with the first 29 YM2203 register writes after each dispatch.   usage: check_patch2203.py 'out/rt_*.log'"""
import sys, glob, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import songs as S
tot = ok = 0; bad = []
for path in sorted(glob.glob(sys.argv[1])):
    ev = [l.split() for l in open(path)]
    for i, p in enumerate(ev):
        if p[0] == 'D' and p[2] == '7' and int(p[1]) in (8, 9, 10):
            ch = int(p[1]); k = i - 1
            while not (ev[k][0] in ('F', 'G') and int(ev[k][1]) == ch): k -= 1
            pos = int(ev[k][2], 16) + int(ev[k][3])
            ptr = S.rb(pos + 1) | S.rb(pos + 2) << 8
            fm = ch - 8
            pred = [(0xb0 + fm, S.rb(ptr))]
            for kk, off in enumerate((0x00, 0x08, 0x04, 0x0c)):
                for g in range(7):
                    v = S.rb(ptr + 1 + 7 * kk + g)
                    if g in (3, 4) and (v & 0x1f): v -= 1      # $F63B: the AM/D1R and D2R rate fields are decremented by one when non-zero (YM2203 rate scale)
                    pred.append((0x30 + 0x10 * g + off + fm, v))
            last = None; w = []; j = i + 1
            while j < len(ev) and ev[j][0] not in ('F', 'G', 'D') and len(w) < len(pred):
                q = ev[j]
                if q[0] == 'E' and q[1] == 'ym2203':
                    if q[2] == 'a': last = int(q[3], 16)
                    else: w.append((last, int(q[3], 16)))
                j += 1
            tot += 1
            if w == pred: ok += 1
            else: bad.append((os.path.basename(path), ch, '%04x' % ptr))
print('YM2203 inline patches: %d, first %d register writes == ROM image prediction: %d' % (tot, 29, ok))
print('mismatches:', bad[:10])
