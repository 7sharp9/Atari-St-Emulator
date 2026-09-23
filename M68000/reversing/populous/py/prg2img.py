# relocate a GEMDOS PRG to a given base; write text+data+bss image
import struct,sys
src,dst,base=sys.argv[1],sys.argv[2],int(sys.argv[3],16)
d=open(src,'rb').read()
_,tl,dl,bl,sl=struct.unpack('>HIIII',d[:18])
img=bytearray(d[28:28+tl+dl])+bytearray(bl)
r=28+tl+dl+sl
off=struct.unpack('>I',d[r:r+4])[0]; r+=4
n=0
if off:
  p=off
  while True:
    v=struct.unpack('>I',img[p:p+4])[0]; img[p:p+4]=struct.pack('>I',(v+base)&0xffffffff); n+=1
    while True:
      b=d[r]; r+=1
      if b==0: p=None; break
      if b==1: p+=254; continue
      p+=b; break
    if p is None: break
open(dst,'wb').write(bytes(base and b'' or b'')+img)
print('text %x data %x bss %x sym %x relocs %d'%(tl,dl,bl,sl,n))
