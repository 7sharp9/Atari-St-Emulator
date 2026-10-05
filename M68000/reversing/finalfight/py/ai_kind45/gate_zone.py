"""gate_zone.py <kind> <trace>...: kind 5: in state 3=0 with a player in the attack zone of $36aec (|dx|<=64: (px-x+$40)<=$80 unsigned; |dy|<=9:
(py-y+9)<=$12 unsigned; player record live and +137 == 0), the next frame must be in 3=2 (attack chosen). Counts hits/misses."""
import sys
from fr import *
r=0xff8c28; P1=0xff8568
ok=bad=0; badl=[]
for p in sys.argv[2:]:
    prev=None
    for f,buf in frames(p):
        if b(buf,r)==0 or b(buf,r+19)!=5 or b(buf,r+2)!=2: prev=None; continue
        if prev is not None:
            pb,pf=prev
            # evaluate at previous frame state: 3==0, 66==0
            if b(pb,r+3)==0 and b(pb,r+66)==0 and b(pb,r+2)==2:
                px=w(pb,P1+6); py=w(pb,P1+10); x=w(pb,r+6); y=w(pb,r+10)
                inzone = b(pb,P1)!=0 and b(pb,P1+137)==0 and ((px-x+0x40)&0xffff)<=0x80 and ((py-y+9)&0xffff)<=0x12
                # $3656e is called once per frame at the end of the 3=0 handler; the effect shows in the next frame's state
                if inzone:
                    if b(buf,r+3)==2: ok+=1
                    else: bad+=1; badl.append((pf,b(buf,r+3),b(buf,r+4)))
        prev=(buf,f)
print('frames in zone with 3==0: next frame 3==2:',ok,'other:',bad,badl[:8])
