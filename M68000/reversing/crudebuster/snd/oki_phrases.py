#!/usr/bin/env python3
"""OKI6295 phrase tables of the two Crude Buster sample ROMs (fu12-.16k = oki1, fu13-.21e = oki2) from the zip: 128 entries x 8 bytes
(start 24-bit BE, end 24-bit BE inclusive, 2 pad bytes) in the first 1024 bytes.  Only the entries before the first sample are table entries (the rest of the first 1024 bytes is sample data). Writes data/oki_phrases.tsv.
Duration: 4-bit ADPCM, 2 samples per byte, sample rate = clock/132 (MAME PIN7_HIGH): oki1 32.22 MHz/32/132 = 7627.3 Hz, oki2 /16 = 15254.6 Hz."""
import os, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
z = zipfile.ZipFile(os.path.expanduser('~/mame-roms/cbuster.zip'))
rates = {'oki1': 32.22e6 / 32 / 132, 'oki2': 32.22e6 / 16 / 132}
rows = []
for chip, name in (('oki1', 'fu12-.16k'), ('oki2', 'fu13-.21e')):
    d = z.read(name)
    used = 0
    # the table ends where the sample data begins: lowest plausible start among the first entries / 8 (oki1 $178 -> 47 entries, oki2 $1f0 -> 62 entries)
    cand = [int.from_bytes(d[i * 8:i * 8 + 3], 'big') for i in range(20)]
    nent = min(c for c in cand if 0 < c < 0x20000) // 8
    print(chip, 'table entries:', nent)
    for i in range(nent):
        e = d[i * 8:i * 8 + 8]
        st = int.from_bytes(e[0:3], 'big'); en = int.from_bytes(e[3:6], 'big')
        if st == 0 and en == 0: continue
        ln = en - st + 1 if en >= st else 0
        dur = ln * 2 / rates[chip]
        rows.append((chip, i, st, en, ln, dur, e[6:8].hex()))
        used += 1
    print(chip, name, 'phrases', used, 'rom size', len(d))
with open(os.path.join(HERE, 'data', 'oki_phrases.tsv'), 'w') as f:
    f.write('chip\tphrase\tstart\tend\tlength_bytes\tduration_s\tpad\n')
    for r in rows: f.write('%s\t%d\t%06x\t%06x\t%d\t%.3f\t%s\n' % r)
