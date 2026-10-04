"""Per level: anchors A($3f) B($3e) C($3d) in scanner pixel coordinates, door in/out ($1b/$1c), exit ($20)."""
from btsec import *
import struct
res={}
for n in range(8):
    d=open(os.path.join(WORK,'files',str(n)),'rb').read()
    w,h=struct.unpack('>HH',d[:4])
    words=struct.unpack('>%dH'%(w*h),d[4:4+2*w*h])
    pos={}
    for i,x in enumerate(words):
        mk=x>>10; col=i%w; row=i//w
        if mk in (0x3f,0x3e,0x3d): pos[mk]=(col*16,row*16+16)
        elif mk in (0x1b,0x1c,0x20): pos[mk]=(col*16+8,row*16+16)
    res[n]=pos
    print('file',n,'w',w,'h',h,{hex(k):v for k,v in pos.items()})
