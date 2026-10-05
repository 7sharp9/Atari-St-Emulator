#!/usr/bin/env python3
"""gate_dmg.py: every drop of Cody's health word during the forced-attack runs (run/id<ch>_<id>_frames.bin) equals
byte[data(ch) + $60 + dmg-idx(box) + d] where box = the kind-6 record's attack-box index (+45) at that frame, d = 96(A6).
The box table is read from the ROM (attack box idx n at base + word(base) + 16n; +8 = damage idx)."""
import sys, os, glob
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
rom = open(os.path.join(ROOT, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
FS = 13*192 + 2*192 + 0x200
w = lambda a: int.from_bytes(rom[a:a+2], 'big')
sw = lambda a: w(a) - 65536 if w(a) & 0x8000 else w(a)
RUN = os.environ.get('K6_RUN_DIR') or os.path.join(ROOT, 'scratchpad/finalfight/p3/d/run')
BASE = {0: (0x3c036, 0x3c286), 1: (0x3c15e, 0x3c366)}
ok = bad = 0; rows = []
for ch in (0, 1):
    for p in sorted(glob.glob(os.path.join(RUN, 'id%d_*_frames.bin' % ch))):
        d = open(p, 'rb').read(); n = len(d)//FS
        for fr in range(1, n):
            c0 = d[(fr-1)*FS + 13*192: (fr-1)*FS + 14*192]; c1 = d[fr*FS + 13*192: fr*FS + 14*192]
            h0 = int.from_bytes(c0[24:26], 'big'); h1 = int.from_bytes(c1[24:26], 'big')
            if h0 >= 0x8000 or h1 >= 0x8000 or h1 >= h0: continue
            # the attacker: the kind-6 record, attack box at the previous or this frame
            for ff in (fr-1, fr):
                r = None
                for i in range(13):
                    q = d[ff*FS + i*192: ff*FS + (i+1)*192]
                    if q[0] and q[19] == 6 and q[45]: r = q
                if r: break
            if not r: continue
            base, dat = BASE[ch]
            e = base + sw(base) + 16*r[45]
            exp = rom[dat + 0x60 + w(e+8) + r[96]]
            got = h0 - h1
            if exp == got: ok += 1
            else: bad += 1; rows.append((os.path.basename(p), fr, r[45], r[96], exp, got))
print('Cody damage drops equal to the table value: %d of %d' % (ok, ok + bad)); print(rows[:8])
