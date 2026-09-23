"""livecov.py SCEN - per call site: calls, model matches, and what the model posted (livecheck records)."""
import collections, json, os, sys
from aicfg import *
from join import dedup, ALLSITES
from strategy import cname
scen = sys.argv[1]
for s in ALLSITES:
    p = os.path.join(AI, 'live', '%s_%s.jsonl' % (scen, s))
    if not os.path.exists(p): continue
    L = [json.loads(l) for l in open(p)]
    for r in L: r['abs'] = r['step']
    L = dedup(L, 'abs')
    c = collections.Counter()
    for r in L:
        k = ','.join('s%d:%s' % (x[0], cname(x[1:4]) if x[1] else 'busy-only') for x in r['model_cmd']) or 'none'
        if r.get('edit'): k += '(' + r['edit'] + ')'
        c[k] += 1
    m = sum(1 for r in L if r['match'] is True); sk = sum(1 for r in L if r['match'] is None)
    print('%s %-6s calls %5d match %5d skip %3d  %s' % (scen, s, len(L), m, sk, dict(c.most_common())))
