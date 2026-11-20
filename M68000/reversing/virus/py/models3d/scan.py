"""scan.py <snap>: walk the model-record chain from $aa72 by its header words and print each record's counts."""
import os,sys,struct
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import vcommon, gfxview
ram,base=gfxview.load_ram(sys.argv[1])
def w(a): return struct.unpack('>H',ram[a:a+2])[0]
def l(a): return struct.unpack('>I',ram[a:a+4])[0]
found=[]
for a in range(0x8000,0x27000,2):
    fl=ram[a]; b1=ram[a+1]
    if fl>3 or b1!=0: continue
    nv=w(a+2)+1; nf=w(a+4)+1; off=w(a+6)
    if not(2<=nv<=80 and 1<=nf<=80): continue
    if off!=8+6*nv: continue
    ok=True
    for f in range(nf):
        p=a+off+22*f+6
        if p+16>len(ram): ok=False;break
        for k in range(3):
            v=l(p+4*k)-0x27154
            if v<0 or v%8 or v//8>=nv: ok=False
        if l(p+12)>=24: ok=False
        if not ok:break
    if ok: found.append((a,fl,nv,nf,a+off+22*nf))
prev=None
for f in found:
    print('%05x flags=%d nv=%d nf=%d end=%05x %s'%(f+(('' if prev is None or prev==f[0] else 'GAP'),)) if False else '%05x flags=%d nv=%d nf=%d end=%05x %s'%(f[0],f[1],f[2],f[3],f[4],'' if prev is None or prev==f[0] else 'gap'))
    prev=f[4]
print(len(found))
