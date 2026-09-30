"""List the functions (by ss.asm address ranges from ss.c headers) that reference given A4 offsets.
usage: xref_a4.py -98 -102 ..."""
import sys, os, re, bisect
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
funcs = []
for l in open(os.path.join(sscfg.WORK, 'ss.c')):
    m = re.match(r'// ==== ([0-9a-f]{8}) (\S+)', l)
    if m: funcs.append((int(m.group(1), 16), m.group(2)))
funcs.sort()
starts = [f[0] for f in funcs]
lines = open(os.path.join(sscfg.WORK, 'ss.asm')).read().split('\n')
for off in sys.argv[1:]:
    pat = re.compile(r'[ (,]%s\(A4\)' % re.escape(off))
    hits = {}
    for l in lines:
        m = re.match(r'\s+\$([0-9a-f]{6}):', l)
        if m and pat.search(l):
            a = int(m.group(1), 16)
            i = bisect.bisect_right(starts, a) - 1
            hits.setdefault(funcs[i][0], []).append(a)
    print('%s(A4): ' % off + ', '.join('$%x(%d)' % (k, len(v)) for k, v in sorted(hits.items())))
