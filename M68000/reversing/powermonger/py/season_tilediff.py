"""Season dissolve check: compare the live tileset ([$ff9e]+3712, 2304 bytes) with the three source
tilesets at [$ff9e]+$1aba2[k], per snapshot. Usage: tilediff.py a.ram b.ram ...  (py/snap2ram.py makes .ram)."""
import struct, sys
def pix(b):  # 288 groups of 16 px: 4 planes x word
    out=[]
    for g in range(288):
        ws=struct.unpack('>4H',b[g*8:g*8+8])
        for x in range(16):
            out.append(sum(((ws[p]>>(15-x))&1)<<p for p in range(4)))
    return out
for f in sys.argv[1:]:
    R=open(f,'rb').read()
    w=lambda a:struct.unpack('>H',R[a:a+2])[0]
    base=struct.unpack('>I',R[0xff9e:0xffa2])[0]
    offs=[w(0x1aba2+2*i) for i in range(4)]
    live=pix(R[base+3712:base+3712+2304])
    res=[]
    for name,o in zip(('winter','spring','summer','autumn'),offs):
        src=pix(R[base+o:base+o+2304])
        res.append(f"{name}(+{o:#x}) differs {sum(a!=b for a,b in zip(live,src))}/4608")
    print(f, f"season={w(0x57fd0)} count={w(0x57fec)} lcg={w(0x57ff6):#x}", "; ".join(res))
