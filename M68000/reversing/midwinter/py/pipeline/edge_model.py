"""Model of the edge scanner $19f20 and compare with the emulator's edge tables at $1b1bc entry.
usage: edge_model.py f1_build.snap tables.log"""
import sys,re; sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from mw import R
import polys
r=R(sys.argv[1])
# ---- emulator ground truth
chunks=re.split(r'--- breakpoint',open(sys.argv[2]).read())[1:]
truth=[]
for ch in chunks:
    bs=[]
    for ln in ch.split('\n'):
        if re.fullmatch(r'([0-9a-f]{2} ?)+',ln.strip()) and ln.strip(): bs+= [int(x,16) for x in ln.split()]
    assert len(bs)==816,len(bs)
    h=(bs[0]<<8)|bs[1]; ymax=(bs[2]<<8)|bs[3]; ymin=(bs[4]<<8)|bs[5]
    tab=[(bs[14+2*i]<<8)|bs[15+2*i] for i in range(400)]  # left 200 words then right 200 words
    col=(bs[814]<<8)|bs[815]
    truth.append(dict(h=h,ymax=ymax,ymin=ymin,left=tab[:200],right=tab[200:],col=col))
# ---- model
def s16(v): v&=0xffff; return v-0x10000 if v&0x8000 else v
def edge(tabs,st,x1,y1,x2,y2):
    """$19f20: st = dict(ymin,ymax); tabs = (left,right); mutate. returns nothing"""
    if y2==y1: return
    if y2>y1: tab=tabs[1]; init=0xc000
    else:
        x1,y1,x2,y2=x2,y2,x1,y1; tab=tabs[0]; init=0x4000
        if y2>st['ymax'] or st['ymax']==0x9000-0x10000: pass
        if y2>=st['ymax']: st['ymax']=y2
        if y1<st['ymin']: st['ymin']=y1
    dx=s16(x2-x1); dy=y2-y1
    a=abs(dx); q=a//dy; rem=a%dy; frac=((rem<<16)//dy)&0xffff
    F=init; x=x1&0xffff; out=[]
    if dx>=0:
        F+=frac; X=F>>16; F&=0xffff
        for k in range(dy):
            out.append(x)
            F+=frac; c=F>>16; F&=0xffff
            x=(x+q+X)&0xffff; X=c   # addx.l: low word x + int + X ; carry of high word becomes next X
    else:
        F-=frac; X=1 if F<0 else 0; F&=0xffff
        for k in range(dy):
            out.append(x)
            F-=frac; c=1 if F<0 else 0; F&=0xffff
            x=(x-q-X)&0xffff; X=c
    for k,v in enumerate(out): tab[y1+k]=v
out_,P=polys.decode(r)
Pt=[p for p in P if p[0]=='poly']
# terrain polygon order in the emulator = draw order; objects' polys interleave: align by $19e70==h and ymin/ymax
ti=0; matched=rows=rowsok=0; res=[]; MT={}
terr=[t for t in truth]
# polygons in draw order (P is in draw order; already reversed in decode)
ti=0
for p in Pt:
    _,h,col,n,edges,pts=p
    # find next truth with h (terrain) in order
    while ti<len(truth) and truth[ti]['h']!=h: ti+=1
    if ti==len(truth): print('no truth for',h); break
    T=truth[ti]; ti+=1
    st=dict(ymin=0x7000,ymax=-0x7000)
    left=[None]*200; right=[None]*200
    # filler logic from $19d6a: for each ring entry choose edge direction
    ring=p[4]
    A=r.l(0x12cea); A1=r.l(0x12cee)
    A3=r.l(0x12ce6)
    # reconstruct the ring walk exactly as the code
    first=r.w(r.l(0x12cf2)+h+2)
    D7=first; D6=D7
    while True:
        D5=r.w(A1+D6); nxt=r.w(A1+D6+2); D4=r.w(A1+nxt); 
        s3,s4=r.w(A+D4),r.w(A+D4+2)
        D0=r.w(A+D5+2)
        if s3==D0 or s4==D0:
            a=r.w(A+D5); b=r.w(A+D5+2)      # $19dcc: shared endpoint is the edge's 2nd: run first -> second
        else:
            a=r.w(A+D5+2); b=r.w(A+D5)      # $19db0: run second -> first
        x1,y1=r.sw(A3+a),r.sw(A3+a+2); x2,y2=r.sw(A3+b),r.sw(A3+b+2)
        edge((left,right),st,x1,y1,x2,y2)
        D6=nxt
        if D6==D7: break
    ok = st['ymin']==T['ymin'] and st['ymax']==T['ymax']
    rr=0; rok=0
    for y in range(T['ymin'],T['ymax']):
        rr+=1
        if left[y] is not None and right[y] is not None and left[y]==T['left'][y] and right[y]==T['right'][y]: rok+=1
    res.append((h,ok,rr,rok,T['col'],col)); MT[h]=dict(left=left,right=right,ymin=st['ymin'],ymax=st['ymax'])
    if len(res)<=0:
        print('poly',h,'y',T['ymin'],T['ymax']); 
        for y in range(T['ymin'],T['ymax']+1): print('  y',y,'model',left[y],right[y],'emu',T['left'][y],T['right'][y])
    rows+=rr; rowsok+=rok
print('terrain polygons aligned',len(res),'of',len(Pt))
print('y-range (ymin,ymax) match',sum(1 for x in res if x[1]),'/',len(res))
print('polygons with every row (left,right) equal',sum(1 for x in res if x[2]==x[3]),'/',len(res))
print('rows ymin..ymax-1 equal (ymax row never written by the polygon: model unwritten at ymax in', sum(1 for _ in [0]) ,'checked below)'); print('rows equal',rowsok,'/',rows)
print('colour word $1a942 == header colour',sum(1 for x in res if x[4]==x[5]),'/',len(res))
bad=[x for x in res if x[2]!=x[3]]; print(bad[:8])

if len(sys.argv)>3:
    h=int(sys.argv[3]); 

import json; json.dump({str(k):v for k,v in MT.items()},open('scratchpad/midwinter/pipeline/model_tables.json','w'))
