# Replays the econ watch log (w_err.txt, c_s30 +15M steps) and checks the +8 write at $22490 (packet landing in the
# pool-2 handler $2239a): new = min(old + packet qty, cap(+10)), qty = $ff from the packet created at $226c0..$226e0.
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent)); _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
import re,struct
ram=bytearray(ram(ANCHOR))
base=0x66ec0
def W(a): return struct.unpack('>H',ram[a:a+2])[0]
for l in open(__import__('sys').argv[1]):
    m=re.match(r'WATCH: step=(\d+) pc=\$(\w+) Write(\w+) \$(\w+) <- \$(\w+)',l)
    if not m: continue
    s,pc,sz,a,v=int(m[1]),int(m[2],16),m[3],int(m[4],16),int(m[5],16)
    k,f=divmod(a-base,50); eb=base+50*k
    if pc==0x22490:
        old=W(eb+8); cap=W(eb+10); print('landing: island',k,'old +8 =',old,'-> new',v,'cap',cap,'predicted',min(old+255,cap),'MATCH' if v==min(old+255,cap) else 'NO')
    if sz=='Byte': ram[a]=v
    else: ram[a:a+2]=struct.pack('>H',v)
