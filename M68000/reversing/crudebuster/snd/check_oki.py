#!/usr/bin/env python3
"""OKI trigger check: every OKI table lookup of $F651 (rtrace `O` line = read of entry byte 3 at ROM offset `off`) is followed by an OKI phrase
start on the chip chosen by $53 (0 = oki1, 1 = oki2).  Predict phrase = table[entry].byte0 - 1 and compare with the first data byte (bit 7 set) the HuC6280
writes to that chip afterwards.   usage: check_oki.py out/rt_*.log"""
import sys, glob, os, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
D = open(os.path.join(HERE, '..', '..', '..', 'scratchpad', 'crudebuster', 'rom', 'cbuster_huc.bin'), 'rb').read()
TAB = [(0x7e56, 0x7f12), (0x7f12, 0x8012), (0x8012, 0x8112)]
tot = ok = 0
per = collections.Counter()
for path in sorted(sum((glob.glob(a) for a in sys.argv[1:]), [])):
    pend = None
    for l in open(path):
        p = l.split()
        if not p: continue
        if p[0] == 'O':
            off = int(p[3]); oki = int(p[2])
            for t, (lo, hi) in enumerate(TAB):
                if lo <= off < hi:
                    e = (off - 3 - lo) // 4
                    ent = D[lo + 4 * e: lo + 4 * e + 4]
                    pend = (t, e, oki, ent[0] - 1, ent[1])
        elif p[0] == 'E' and p[1].startswith('oki') and pend:
            v = int(p[3], 16)
            if v & 0x80:
                t, e, oki, ph, att = pend
                chip = 'oki%d' % (oki + 1)
                good = (chip == p[1]) and (v & 0x7f) == ph
                tot += 1; ok += good; per[(chip, t)] += 1
                if not good: print('MISMATCH', path, pend, p)
                pend = None
print('OKI starts checked %d, phrase and chip as predicted by table lookup: %d; per (chip, table): %s' % (tot, ok, dict(per)))
