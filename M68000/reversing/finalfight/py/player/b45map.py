"""b45map.py <log...>: per (st,sub,m66) the attack-box ids (+45) seen and frame counts."""
import sys,collections
c=collections.defaultdict(collections.Counter)
for fn in sys.argv[1:]:
    for l in open(fn):
        if l[0] in 'EQ': continue
        p=l.split(); d={t.split('=')[0]:t.split('=')[1] for t in p[2:] if '=' in t}
        c[(d['st'],d['sub'],d['m66'])][d['b45']]+=1
for k in sorted(c): print('st=%s sub=%s m66=%s: %s'%(k+(' '.join('%s:%d'%(a,n) for a,n in sorted(c[k].items())),)))
