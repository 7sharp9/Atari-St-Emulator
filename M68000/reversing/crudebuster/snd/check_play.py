#!/usr/bin/env python3
"""Compare the 68000 latch writes seen in MAME plays (LAT lines of run.lua logs: id, return address of the `jsr $e1c` read from the stack) with the static
site table callers68k.tsv (raw scan of the whole image).  usage: check_play.py out/play1b.log out/auto1.log ..."""
import sys, os, collections
HERE = os.path.dirname(os.path.abspath(__file__))
st = {}
for l in list(open(os.path.join(HERE, 'callers68k.tsv')))[1:]:
    f = l.rstrip('\n').split('\t'); st[int(f[0], 16)] = (f[1], f[2])
site_of = {s + (4 if k.endswith('.w') else 6): s for s, (k, ids) in st.items()}
obs = collections.Counter()
for fn in sys.argv[1:]:
    for l in open(fn):
        p = l.split()
        if p and p[0] == 'LAT' and len(p) >= 5: obs[(int(p[3], 16), int(p[2], 16))] += 1
cls = collections.Counter(); bad = []
pairs = collections.defaultdict(list)
for (ret, i), n in sorted(obs.items()):
    if ret in site_of:
        s = site_of[ret]; ids = st[s][1]
        if ids == '?': c = 'data-driven site (id from a table/field)'
        elif ('$%02x' % i) in ids.split(','): c = 'static site, id predicted'
        else: c = 'static site, id NOT predicted'; bad.append((ret, i, n))
        pairs[s].append((i, n))
    else:
        c = 'not a jsr $e1c (ret $%06x: direct write at $11ee)' % ret
    cls[c] += n
for k, v in cls.items(): print('%5d  %s' % (v, k))
print('distinct (site,id) pairs: %d; distinct ids %d: %s' % (len(obs), len(set(i for (r, i) in obs)), ' '.join('%02x' % i for i in sorted(set(i for (r, i) in obs)))))
print('sites reached: %d of %d' % (len(pairs), len(st)))
print('NOT predicted:', bad)
for s in sorted(pairs):
    if st[s][1] == '?': print('  data-driven site %06x ids: %s' % (s, ' '.join('%02x(x%d)' % x for x in sorted(pairs[s]))))
