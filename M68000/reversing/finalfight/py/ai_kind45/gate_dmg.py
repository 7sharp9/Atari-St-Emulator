"""gate_dmg.py: for every drop of Cody's health word while a spawned fighter's attack box (+45) is active, compare the drop with the
damage-table byte (92(A6)'s source: data base + $60 + level + box row) computed from the ROM (chars.py). usage: gate_dmg.py <trace> <rec> <kind> <sub> [level]"""
import sys
from fr import *
from chars import rom,box
from chars import w as rw
path=sys.argv[1]; r=int(sys.argv[2],16); kind=int(sys.argv[3]); sub=int(sys.argv[4]); lvl=int(sys.argv[5]) if len(sys.argv)>5 else 0
if kind==4: anim=0x3307c+rw(0x3307c+2*sub); dat=0x33082+rw(0x33082+2*sub)
else: anim=0x36e0a+rw(0x36e0a+2*sub); dat=0x36e0e+rw(0x36e0e+2*sub)
ok=bad=0; prev=None; badl=[]
for f,buf in frames(path):
    if b(buf,r)==0 or b(buf,r+19)!=kind or b(buf,r+20)!=sub: prev=None; continue
    ch=w(buf,0xff8580)
    a=b(buf,r+45)
    if prev is not None and ch<prev and prev-ch<200:
        if a:
            exp=rom[dat+0x60+lvl+box(anim,a)[1][4]]
            if exp==prev-ch: ok+=1
            else: bad+=1; badl.append((f,a,prev-ch,exp))
        else: badl.append((f,'nobox',prev-ch))
    prev=ch
print(path,'kind',kind,'sub',sub,'drops matching table',ok,'mismatch',bad,badl[:5])
