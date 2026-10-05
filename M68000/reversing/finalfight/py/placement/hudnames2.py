# hudnames2.py <tap log> : (HUD record tag, kind, +20) at each name-pointer write ($5b66e) against the name decoded from the pointer (ROM text); counts
import sys,collections
from rom import *
def name(a): return ''.join(chr(w(a+2*i)&0xff) for i in range(16) if (w(a+2*i)>>8)==0x44).strip()
hi={}; res=collections.Counter()
for l in open(sys.argv[1]):
    if 'pc=05b66e' not in l: continue
    p=l.split(); f=int(p[1]); a=int(p[3][2:],16); d=int(p[5][2:],16)
    if a in (0xff13a8,0xff14a8): hi[a]=d
    else:
        ptr=(hi.get(a-2,0)<<16)|d; r=p[6][2:]
        res[(int(r[0:2],16),int(r[2:4],16),int(r[4:6],16),name(ptr),ptr)]+=1
for k,v in sorted(res.items()): print(v,'tag %x kind %d +20=%d -> %s (@%06x)'%(k[0],k[1],k[2],k[3],k[4]))
