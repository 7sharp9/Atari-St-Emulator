# Production-line rule of $2262c (state 1): stock(+2) -= cost(line+10 = econ+24); steps(line+4 = econ+18) -= 1; at 0 state -> 2;
# next tick state 2 emits a pool-2 packet (item=+16, qty=+22, dest=+20) and sets state -1.
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent)); _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
import re,struct,sys
ram=bytearray(ram(ANCHOR)); base=0x66ec0
def W(a): return struct.unpack('>H',ram[a:a+2])[0]
ok=bad=0; stp=0; stpbad=0
for l in open(sys.argv[1]):
    m=re.match(r'WATCH: step=(\d+) pc=\$(\w+) Write(\w+) \$(\w+) <- \$(\w+)',l)
    if not m: continue
    s,pc,sz,a,v=int(m[1]),int(m[2],16),m[3],int(m[4],16),int(m[5],16)
    k,f=divmod(a-base,50); eb=base+50*k
    if pc==0x226a8:
        pred=W(eb+2)-W(eb+24)
        if v==pred: ok+=1
        else: bad+=1; print('bad',k,W(eb+2),W(eb+24),v)
    if pc==0x2226ac and False: pass
    if pc==0x226ac:
        if v==(W(eb+18)-1)&0xffff: stp+=1
        else: stpbad+=1
    if sz=='Byte': ram[a]=v
    else: ram[a:a+2]=struct.pack('>H',v)
print('line cost writes ok',ok,'bad',bad,'; step decrements ok',stp,'bad',stpbad)
