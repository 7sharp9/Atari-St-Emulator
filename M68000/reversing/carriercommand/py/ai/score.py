"""Re-implementation of Carrier Command's enemy target scoring ($2337a) from a flat RAM image (dumpram.py output).
usage: score.py <snap or flat RAM>   -> prints python scores vs the game's table at $232fa, and argmax vs $11ba"""
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent)); _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
import struct, sys
def S(d):
    sw=lambda a:struct.unpack('>h',d[a:a+2])[0]
    w=lambda a:struct.unpack('>H',d[a:a+2])[0]
    l=lambda a:struct.unpack('>i',d[a:a+4])[0]
    def oct_(dx,dy):
        dx=abs(dx);dy=abs(dy)
        if dy<dx: dx,dy=dy,dx   # cmp.l D0,D1 ; bcs ; exg  => D1 = larger?
        return None
    def octd(x1,y1,x2,y2):
        a=abs(x1-x2); b=abs(y1-y2)
        # code: D0=a,D1=b; cmp.l D0,D1 (D1-D0); bcs skip (D1<D0) ; else exg => D0=max? 
        # if b<a unsigned: keep D0=a(max),D1=b ; else swap => D0=b(max),D1=a. result = max + min/2
        mx,mn=(a,b) if b<a else (b,a)
        return mx+(mn>>1)
    ex,ey=l(0x5f4a4),l(0x5f4ac)
    hx,hy=l(0x6fe70),l(0x6fe74)      # island 63 (enemy base)
    cur=w(0x11bc)
    owner=d[0x69b40:0x69b40+64]
    sc=[]
    for i in range(64):
        b=0x69b80+402*i
        x,y=l(b+2),l(b+6)
        de=octd(x,y,ex,ey)
        s=-15000 if de>0x2dc6c0 else ((-de)>>11)  # neg.l; asr #8; asr #3 (floors)
        dh=octd(x,y,hx,hy)>>14
        o=owner[i]
        s+= dh if o==2 else -dh
        area=w(b+14)
        if o==0: s+= 2000 if area<=0x7d0 else 3000
        elif o==2: s+= -4000
        else: s+= 1000 if area<=0x7d0 else 1500
        if o!=2:
            base=0x22afa+32*i
            n=w(base)
            cnt=0
            for k in range(n):
                idx=w(base+4+4*k-0)&0x3fff if False else w(base+2+4*k+2)&0x3fff
                if sw(0x69ac0+2*idx)>=0: cnt+=1
            if cnt: s+=4000
        sc.append(s)
    if owner[0]!=2:
        if octd(l(0x69b82),l(0x69b86),ex,ey)<=0x2dc6c0: sc[0]+=5000
    sc[cur]=-32767
    return sc,cur
if __name__=='__main__':
    d=ram(sys.argv[1])
    sc,cur=S(d)
    sw=lambda a:struct.unpack('>h',d[a:a+2])[0]
    tbl=[sw(0x232fa+2*i) for i in range(64)]
    wrap=lambda v:((v+32768)%65536)-32768
    sc=[wrap(v) for v in sc]
    print('match',sum(a==b for a,b in zip(sc,tbl)),'/64')
    for i,(a,b) in enumerate(zip(sc,tbl)):
        if a!=b: print(i,a,b)
    # argmax: first max (cmp.w (A0)+,D0 ; bge keep) -> ties keep earliest? 'bge $23504' skips update if D0>=entry
    best=-32768;bi=0
    for i,v in enumerate(sc):
        if v>best: best=v;bi=i
    print('argmax',bi,best,'game $11ba=',struct.unpack('>H',d[0x11ba:0x11bc])[0])
