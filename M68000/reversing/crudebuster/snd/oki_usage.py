#!/usr/bin/env python3
"""data/oki_usage.tsv: every OKI6295 phrase (from oki_phrases.py), the table entries of the HuC6280 OKI tables that select it and the latch ids that
started it in the MAME sweep (out/sw_all.log).  Table A ($9E56, oki1), B ($9F12, oki2), C ($A012, oki2 alternate, identity); entry = [phrase+1, attenuation, priority, voice mask]."""
import os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import songs as S, analyze_sweep as A
rows = [l.rstrip('\n').split('\t') for l in list(open(os.path.join(HERE, 'data', 'oki_phrases.tsv')))[1:]]
ent = {'oki1': collections.defaultdict(list), 'oki2': collections.defaultdict(list)}
for name, base, n, chip in (('A', 0x9e56, 64, 'oki1'), ('B', 0x9f12, 64, 'oki2')):
    for e in range(n):
        b = [S.rb(base + 4 * e + k) for k in range(4)]
        ent[chip][b[0] - 1].append('%s%d(att%d,pri%d,mask%x)' % (name, e, b[1], b[2], b[3]))
blocks = A.parse(os.path.join(HERE, 'out', 'sw_all.log'))
ids = {'oki1': collections.defaultdict(set), 'oki2': collections.defaultdict(set)}
for i, b in blocks.items():
    r = A.summarise(b)
    for chip in ('oki1', 'oki2'):
        for x in r[chip + '_start']: ids[chip][x[0]].add(i)
with open(os.path.join(HERE, 'data', 'oki_usage.tsv'), 'w') as f:
    f.write('chip\tphrase\tstart\tend\tlength\tduration_s\ttable_entries\tstarted_by_latch_ids\n')
    for chip, ph, st, en, ln, du, pad in rows:
        ph = int(ph)
        kind = ''
        if st == '808080': kind = ' (filler)'
        elif ln == '1': kind = ' (1-byte stub)'
        f.write('%s\t%d\t%s\t%s\t%s\t%s\t%s\t%s\n' % (chip, ph, st, en, ln, du, ' '.join(ent[chip].get(ph, [])) or '-', ' '.join('%02x' % i for i in sorted(ids[chip].get(ph, []))) or '-'))
tot = collections.Counter()
for chip, ph, st, en, ln, du, pad in rows:
    if st != '808080' and ln != '1': tot[chip] += 1
print('real phrases (not filler, not 1-byte stub):', dict(tot))
