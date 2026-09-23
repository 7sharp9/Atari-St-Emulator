"""fieldxref.py: per function, which player-record fields ($21e0c + side*$2e + off) are read/written."""
import re,sys,collections
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from popcfg import WORK
P = WORK + '/'
funcs=sorted(int(x,16) for x in open(P+'funcs_ad58.txt').read().split())
lines=[l.rstrip() for l in open(P+'pop_ad58.asm')]
def fn(a):
    f=None
    for x in funcs:
        if x<=a: f=x
    return f
res=collections.defaultdict(set)
for i,l in enumerate(lines):
    if re.search(r'lea \$21e0c\.l,A(\d)',l):
        reg=re.search(r'A(\d)$',l).group(1)
        for j in range(i+1,min(i+4,len(lines))):
            m=re.search(r'(-?\d+)\(A%s,D\d\.[lw]\)'%reg,lines[j])
            if m:
                a=int(lines[j][:6],16)
                w='W' if re.search(r',\s*-?\d+\(A%s,'%reg,lines[j]) or lines[j].split(':')[1].strip().split()[0] in('clr.w','addq.w','subq.w','clr.b','addq.b') else 'R'
                res[fn(a)].add('+%d%s@%x'%(int(m.group(1)),w,a)); break
for f in sorted(res): print('%x'%f, ' '.join(sorted(res[f],key=lambda s:int(s[1:].split('R')[0].split('W')[0]))))
