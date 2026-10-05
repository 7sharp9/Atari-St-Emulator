# decode the P1 HUD bar tiles to a health value and compare with Cody's +24/+26 words per frame (hpbar.txt)
import re,sys,os
here=os.path.dirname(os.path.abspath(__file__))
rows=[]
for l in open(os.environ.get('HPFILE', os.path.join(here,'../../../scratchpad/finalfight/run/hpbar.txt'))):
    m=re.match(r'f=(\d+) cody=(\w+),(\w+),(\w+) bred=(\w+),(\w+),(\w+) r0=(\S+) r2=(\S+)',l)
    if not m or m.group(1)=='0': continue
    f=int(m.group(1)); c=[int(m.group(i),16) for i in (2,3,4)]; b=[int(m.group(i),16) for i in (5,6,7)]
    r0=[int(x,16) for x in m.group(8).split(',')]; r2=[int(x,16) for x in m.group(9).split(',')]
    rows.append((f,c,b,r0,r2))
# partial tiles from the ROM table at $2078: remainder r (1..7) -> tile
from rd import rom
part={int.from_bytes(rom[0x2078+2*r:0x2078+2*r+2],'big'):r for r in range(1,8)}
lost={int.from_bytes(rom[0x2088+2*r:0x2088+2*r+2],'big'):r for r in range(1,8)}  # damaged-tile variants
def decode(r):
    n=0
    while n<18 and r[n]==0x4560: n+=1
    if n<18 and r[n] in part: return n*8+part[r[n]]
    if n<18 and r[n] in lost: return n*8+lost[r[n]]
    return n*8
exact={'c24':0,'c26':0,'b24':0,'b26':0}; tot=0; shown=0; bshown=0; changes=[]
prev=None
for f,c,b,r0,r2 in rows:
    d0=decode(r0); d2=decode(r2); tot+=1; bshown+= r2[0]==0x4560
    exact['c24']+= d0==c[0]; exact['c26']+= d0==c[1]; exact['b24']+= (d2==b[0] and r2[0]==0x4560); exact['b26']+= d2==b[1]
    if prev!=(c,b,d0,d2): changes.append((f,c,b,d0,d2)); prev=(c,b,d0,d2)
print('frames',tot,exact,'bred bar shown in',bshown)
for x in changes: print(x[0],'cody %04x/%04x/%04x'%tuple(x[1]),'bred %04x/%04x/%04x'%tuple(x[2]),'HUD cody',x[3],'HUD bred',x[4])
