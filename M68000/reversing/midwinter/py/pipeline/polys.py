"""Decode the terrain draw list of a snapshot taken at $19ce2 entry. usage: polys.py snap"""
import sys; sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from mw import R
def decode(r):
    A3,A2,A1,A0 = r.l(0x12ce6),r.l(0x12cea),r.l(0x12cee),r.l(0x12cf2)
    end=r.l(0x18bda)
    L=[r.sw(a) for a in range(0x18be2,end,2)]
    # walk in draw order = reverse
    out=[]; i=len(L)-1
    while i>=0:
        d0=L[i]
        if d0<0: out.append(('obj',d0,L[i-1])); i-=2
        else: out.append(('poly',d0)); i-=1
    polys=[]
    for k in out:
        if k[0]!='poly': polys.append(k); continue
        h=k[1]
        col=r.w(A0+h); first=r.w(A0+h+2)
        ring=[]; e=first
        while True:
            edge=r.w(A1+e); ring.append(edge)
            e=r.w(A1+e+2)
            if e==first or len(ring)>64: break
        edges=[(r.w(A2+x),r.w(A2+x+2),r.w(A2+x+4),r.w(A2+x+6)) for x in ring]
        # vertex chain as the filler walks it
        pts=lambda o:(r.sw(A3+o),r.sw(A3+o+2))
        polys.append(('poly',h,col,len(ring),edges,[(pts(a),pts(b)) for a,b,_,_ in edges]))
    return out,polys
if __name__=='__main__':
    r=R(sys.argv[1]); out,polys=decode(r)
    P=[p for p in polys if p[0]=='poly']
    print('draw order entries',len(out),'polys',len(P),'objs',len(out)-len(P))
    print('total ring entries',sum(p[3] for p in P), 'hist', sorted({n:sum(1 for p in P if p[3]==n) for n in {p[3] for p in P}}.items()))
    print('colours',sorted({p[2] for p in P}))
    for p in P[:3]: print(p)
