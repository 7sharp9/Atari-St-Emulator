#!/usr/bin/env python3
"""YM2151 patch loader check: opcode $d2 n on channels 0-7 loads FM patch n through the bank-6 loader ($4203 -> $448D).  Prediction from the ROM:
  record = 4 bytes at bank6 $4600+4n : image pointer (lo hi), then 2 bytes (stored in $2748/$2758,x);  logical $4000-$5fff = bank 6, $6000-$7fff = bank 7.
  image: byte0 = RL/FB/CON (written | $c0 to reg $20+ch), byte1 unused, then 4 operators x 7 bytes in the order M1,C1,M2,C2 (slot offsets $00,$10,$08,$18):
         DT1/MUL ($40) TL ($60) KS/AR ($80) AMS/D1R ($a0) DT2/D2R ($c0) D1L/RR ($e0) + 1 unused byte;  then 3 bytes: slot mask, KC, KF.
Compared with the first 25 YM2151 register writes MAME saw after each dispatch (rtrace logs).   usage: check_patch.py 'out/rt_*.log'"""
import sys, glob, os
HERE = os.path.dirname(os.path.abspath(__file__))
D = open(os.path.join(HERE, '..', '..', '..', 'scratchpad', 'crudebuster', 'rom', 'cbuster_huc.bin'), 'rb').read()
def lphys(a):
    if 0x4000 <= a < 0x6000: return 0xc000 + a - 0x4000
    if 0x6000 <= a < 0x8000: return 0xe000 + a - 0x6000
    raise ValueError('pointer %04x outside banks 6/7' % a)
def predict(n, ch):
    rec = 0xc000 + 0x600 + 4 * n
    ptr = D[rec] | D[rec + 1] << 8
    img = lphys(ptr)
    out = [(0x20 + ch, D[img] | 0xc0)]
    for k, off in enumerate((0x00, 0x10, 0x08, 0x18)):
        for g in range(6):
            out.append((0x40 + 0x20 * g + off + ch, D[img + 2 + 7 * k + g]))
    return out, (D[img + 30], D[img + 31], D[img + 32])
tot = ok = 0; bad = []
for path in sorted(glob.glob(sys.argv[1])):
    ev = [l.split() for l in open(path)]
    i = 0
    while i < len(ev):
        p = ev[i]
        if p[0] == 'D' and p[2] == '66' and int(p[1]) < 8:
            ch = int(p[1])
            # the operand: last F/G fetch of this channel gives the opcode position
            k = i - 1
            while not (ev[k][0] in ('F', 'G') and int(ev[k][1]) == ch): k -= 1
            pos = int(ev[k][2], 16) + int(ev[k][3])
            import songs as S
            n = S.rb(pos + 1)
            pred, extra = predict(n, ch)
            last = None; w = []
            j = i + 1
            while j < len(ev) and ev[j][0] not in ('F', 'G', 'D') and len(w) < 25:
                q = ev[j]
                if q[0] == 'E' and q[1] == 'ym2151':
                    if q[2] == 'a': last = int(q[3], 16)
                    else: w.append((last, int(q[3], 16)))
                j += 1
            tot += 1
            if w == pred: ok += 1
            else: bad.append((os.path.basename(path), ch, n))
        i += 1
print('d2 patch loads on YM2151 channels: %d, first 25 register writes == ROM image prediction: %d' % (tot, ok))
print('mismatches:', bad[:10])
