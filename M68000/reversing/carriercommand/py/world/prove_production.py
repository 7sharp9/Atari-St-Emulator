# Replays the WATCH log of the econ table ($66ec0, 64 x 50 bytes) from c_s30 and checks every $220b0 stock write
# against the production rule of $2205a: stock = min(stock + rate, cap), rate by type byte & 3.
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent)); _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
import re,sys,struct
ram=bytearray(ram(ANCHOR))      # c_s30 flat RAM
own=ram[0x69b40:0x69b80]
base=0x66ec0
ev=[]
for l in open(sys.argv[1] if len(sys.argv)>1 else str(WORK / 'world' / 'w60_err.txt')):
    m=re.match(r'WATCH: step=(\d+) pc=\$(\w+) Write(\w+) \$(\w+) <- \$(\w+)',l)
    if m: ev.append((int(m[1]),int(m[2],16),m[3],int(m[4],16),int(m[5],16)))
def W(a): return struct.unpack('>H',ram[a:a+2])[0]
ok=bad=0; steps=set(); detail=[]
for s,pc,sz,a,v in ev:
    off=a-base; k,f=divmod(off,50); eb=base+50*k
    if pc==0x220b0:
        t=ram[eb]&3; cap=W(eb+4); st=W(eb+2)
        if own[k]!=0:
            rate={0:100,1:ram[eb+6]*100,2:W(eb+12)*25,3:0}[t]
        else:
            rate=(cap>>4) if ram[eb+7] else 0
        pred=min(st+rate,cap)
        if pred==v: ok+=1
        else: bad+=1; detail.append((s,k,t,st,rate,cap,v))
        steps.add(s//200000)
    if sz=='Byte': ram[a]=v
    else: ram[a:a+2]=struct.pack('>H',v)
print('production writes matching rule:',ok,'mismatch:',bad)
for d in detail[:10]: print(d)
