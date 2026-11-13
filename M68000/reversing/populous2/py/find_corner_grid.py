"""Search a Populous II snapshot's RAM for a 65x65 corner-height grid (byte or word, every
even base $2000..$80000) whose Populous 1 cell derivation (terrain.md section 1, without
the shore rule, as corners.py shows Populous II uses it) reproduces byte 1 of the cell records at $3979e. Prints the best five candidates; a
real grid matches every non-rock cell; the all-sea cells alone give about 2870. Run beside corners.py, which shows the
heights are implied by the cells themselves.

--control plants the corner grid corners.py builds as bytes at $70000 first (the positive
control: it must come out on top with every non-rock cell).

usage: uv run python reversing/populous2/py/find_corner_grid.py <snap> [--control]
"""
import os, sys
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, "tools", "rdis.py")): d = os.path.dirname(d)
sys.path.insert(0, os.path.join(d, "tools"))
from gfxview import load_ram
import numpy as np
ram,_=load_ram(sys.argv[1]); ram=bytearray(ram)
if '--control' in sys.argv:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import corners
    H,_,_=corners.corner_grid(ram)
    for y in range(65):
        for x in range(65): ram[0x70000+y*65+x]=H[x,y]
R=np.frombuffer(bytes(ram),dtype=np.uint8)
cells=R[0x3979e:0x3979e+0x4000].reshape(64,64,4)
shape=cells[:,:,1].astype(int)
def derive(h):
    a=h[:-1,:-1];b=h[:-1,1:];c=h[1:,1:];d=h[1:,:-1]
    s=(a+b+c+d)>>2
    bits=(a>s)*1|(b>s)*2|(c>s)*4|(d>s)*8
    flat=(s>0)&(bits==0); bits=np.where(flat,15,bits); s=np.where(flat,s-1,s)
    return bits,s
mask=shape!=0x2f
best=[]
for es in (1,2):
    for base in range(0x2000,0x80000-65*65*es,2):
        raw=R[base:base+65*65*es]
        h=(raw.reshape(65,65) if es==1 else (raw[0::2].astype(int)*256+raw[1::2]).reshape(65,65)).astype(int)
        if h.max()>16 or h.max()==0: continue
        bits,s=derive(h)
        m=int(((bits==shape)&mask).sum())
        best.append((m,hex(base),es,int(h.max())))
best.sort(reverse=True); print('non-rock cells',int(mask.sum()),'candidates',len(best)); print('best (matched cells, base, element size, max height):',best[:5])
