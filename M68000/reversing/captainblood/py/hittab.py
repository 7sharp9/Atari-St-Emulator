import sys,struct
sys.path.insert(0,'tools')
from gfxview import load_ram
ram,_=load_ram(sys.argv[1]); ram=bytes(ram)
ptr=int(sys.argv[2],16) if len(sys.argv)>2 else None
if ptr is None: ptr=struct.unpack('>I',ram[0xd586:0xd58a])[0]
print('hit table at',hex(ptr))
n=struct.unpack('>H',ram[ptr:ptr+2])[0]
for i in range(n+1):
    e=ptr+2+8*i; x0,x1,y0,y1=ram[e:e+4]; h=struct.unpack('>I',ram[e+4:e+8])[0]
    print(f"{i:2d} x[{x0*2-4:4d}..{x1*2-4+1:4d}] (raw {x0}-{x1})  y[{y0}-{y1}]  handler {h:08x}")
