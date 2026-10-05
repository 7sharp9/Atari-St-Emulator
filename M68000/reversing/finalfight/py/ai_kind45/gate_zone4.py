"""gate_zone4.py <trace>...: kind 4 ($32a88): in 3=2 (4=2 loop) with a player in the near zone of $32cba (|dx|<=64, |dy|<=9: (px-x+$40)<=$80 and (py-y+9)<=$12,
player live, +137==0) the machine goes to 3=4 with +157=1 on that frame; in the mid zone of $32c44 ((px-x+$50)<=$a0, same dy) to 3=4 with +157=0.
Prints how many frames of each zone were followed by 3=4 on the next frame."""
import sys
from fr import *
r=0xff8c28; P1=0xff8568
res={'near':[0,0],'mid':[0,0]}
for p in sys.argv[1:]:
    prev=None
    for f,buf in frames(p):
        if b(buf,r)==0 or b(buf,r+19)!=4 or b(buf,r+2)!=2: prev=None; continue
        if prev is not None and b(prev,r+3)==2 and b(prev,r+4)==2 and b(prev,r+66)==0:
            px=w(prev,P1+6); py=w(prev,P1+10); x=w(prev,r+6); y=w(prev,r+10)
            live = b(prev,P1)!=0 and b(prev,P1+137)==0 and w(prev,P1+90)==0
            dyok = ((py-y+9)&0xffff)<=0x12
            near = live and dyok and ((px-x+0x40)&0xffff)<=0x80
            mid = live and dyok and ((px-x+0x50)&0xffff)<=0xa0
            if near: res['near'][0 if b(buf,r+3)==4 and b(buf,r+157)==1 else 1]+=1
            elif mid: res['mid'][0 if b(buf,r+3)==4 and b(buf,r+157)==0 else 1]+=1
        prev=buf
print('kind 4 zone gate  near: expected(3=4,157=1) %d other %d | mid: expected(3=4,157=0) %d other %d'%(res['near'][0],res['near'][1],res['mid'][0],res['mid'][1]))
