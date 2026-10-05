#!/usr/bin/env python3
"""corpus2.py <run names...>: like corpus.py for the mode-6 reaction handlers, using the reaction id (129(A6)) of the
previous frame to pick the sub-state table.  Runs are out/<name>.log with out/<name>.hits (forced reaction runs f_<id>)."""
import os, sys, collections, importlib.util, io, contextlib
REACT = {
 'A': {0: 0x3c80e, 2: 0x3c816, 4: 0x3c826, 6: 0x3c838},
 'B': {0: 0x3c8a2, 2: 0x3c816, 4: 0x3c826, 6: 0x3c838},
 'C': {0: 0x3c8c2, 2: 0x3c8ca, 4: 0x3c906, 6: 0x3c978, 8: 0x3c9b8, 10: 0x3c9d8},
 'D': {0: 0x3c9fc, 2: 0x3ca40, 4: 0x3caa4, 6: 0x3caee, 8: 0x3cb2e},
 'E': {0: 0x3cb50, 2: 0x3cb94, 4: 0x3cc00, 6: 0x3cc40},
 'F': {0: 0x3cc66, 2: 0x3c8ca, 4: 0x3c906, 6: 0x3c978, 8: 0x3c9b8, 10: 0x3c9d8}}
IDMAP = {0: 'A', 2: 'A', 1: 'B', 3: 'C', 7: 'C', 5: 'D', 6: 'E', 8: 'F'}
ENTRY = {'A': 0x3c7f6, 'B': 0x3c88a, 'C': 0x3c8aa, 'D': 0x3c9e6, 'E': 0x3cb3c, 'F': 0x3cc4e}
OUT = os.environ.get('FF_E_OUT') or os.path.join(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..')), 'scratchpad/finalfight/p3/e/out')
def load(log):
    sys.argv = ['anal', log]
    spec = importlib.util.spec_from_file_location('anal', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'anal.py')); a = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(a)
    return a
exp = collections.Counter(); hit = collections.Counter()
for name in sys.argv[1:]:
    a = load(os.path.join(OUT, '%s.log' % name))
    prev = None
    for fr in a.frames:
        rec = [b for b in fr['recs'].values() if b[19] == 8]
        if prev is not None:
            s2, s3, s4, s5, ident = prev
            if s2 == 2 and s3 == 6 and s4 == 2 and ident in IDMAP:
                g = IDMAP[ident]; exp[ENTRY[g]] += 1
                if s5 in REACT[g]: exp[REACT[g][s5]] += 1
        prev = (rec[0][2], rec[0][3], rec[0][4], rec[0][5], rec[0][129]) if rec else None
    for l in open(os.path.join(OUT, '%s.hits' % name)):
        ad, c = l.split(); hit[int(ad, 16)] += int(c)
allad = set(a for g in REACT.values() for a in g.values()) | set(ENTRY.values())
ok = bad = 0
for ad in sorted(allad):
    if hit[ad] == exp[ad]: ok += 1; fl = 'OK  '
    else: bad += 1; fl = 'DIFF'
    print('%s %06x expected %d live %d' % (fl, ad, exp[ad], hit[ad]))
print('match', ok, 'mismatch', bad)
