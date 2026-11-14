"""Check the projection+outcode stage against RAM: for every vertex of every cell record in the
$18f02 list (snapshot at $19ce2 entry): proj = (cam.x divs cam.z + CX, -(cam.y divs cam.z) + CY, z, code)."""
import sys; sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from mw import R
r=R(sys.argv[1])
A3=r.l(0x12ce6); cx=r.sw(0x17218); cy=r.sw(0x1721a)
xl,xr,yt,yb=r.sw(0x171f0),r.sw(0x171f2),r.sw(0x171f4),r.sw(0x171f6)
def divs(n,d):  # 68000 DIVS: 32/16 -> 16 signed, trunc toward zero; None on overflow
    q=abs(n)//abs(d)
    if (n<0)!=(d<0): q=-q
    return None if not -32768<=q<=32767 else q
def code(x,y):
    c=0
    if x<xl: c|=1
    elif x>xr: c|=2
    if y<yt: c|=4
    elif y>yb: c|=8
    return c
cells=[r.l(a) for a in range(0x18f02,r.l(0x18bde),4)]
tot=ok=behind=bad=0; seen=set(); examples=[]
for A5 in cells:
    for pi,ci in ((0,14),(16,30),(336,350),(352,366)):
        p=r.w(A5+pi); c=r.w(A5+ci)
        if (p,c) in seen: continue
        seen.add((p,c))
        cam=A3+c; X=r.sl(cam); Y=r.sl(cam+4); Z=r.sw(cam+10)  # D5 long: z is the low word
        tot+=1
        if p==0xffff:
            behind+= (Z<=1); ok+=(Z<=1) ; 
            if Z>1:
                q1,q2=divs(X,Z),divs(Y,Z)
                ok+= (q1 is None or q2 is None); 
            continue
        pr=A3+p
        sx,sy,sz,sc=r.sw(pr),r.sw(pr+2),r.sw(pr+4),r.w(pr+6)
        q1,q2=divs(X,Z),divs(Y,Z)
        if q1 is None or q2 is None: bad+=1; continue
        ex=(q1+cx)&0xffff; ey=(-q2+cy)&0xffff   # neg.w then add.w : 16-bit wrap
        ex=(ex+0x8000)%0x10000-0x8000; ey=(ey+0x8000)%0x10000-0x8000
        ec=code(ex,ey)
        if (sx,sy,sc)==(ex,ey,ec) and sz==Z: ok+=1
        else:
            bad+=1
            if len(examples)<5: examples.append((hex(A5),p,c,X,Y,Z,(sx,sy,sz,sc),(ex,ey,ec)))
print('cells',len(cells),'unique (proj,cam) vertex pairs',tot,'match',ok,'behind-camera(-1)',behind,'mismatch',bad)
print(examples)
