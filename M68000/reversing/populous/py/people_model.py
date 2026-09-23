"""people_model.py - Python re-implementation of the Populous settlement/mana rules in the per-frame
entity update $db4c, checked against emulator captures from capframes.py.
Usage: python people_model.py fr/run400.bin"""
import struct,sys
from capframes import REGIONS,RECLEN
ENT=0x3b278; ESZ=0x16; SIDE=0x3b226
DOFF=[0,-64,1,64,-1,-63,65,63,-65,-128,2,128,-2,-126,130,126,-130]   # $22b4e[0..16]
# LAND-header tables (loaded by $14be8 from LANDn; values from game_start.snap, land 0)
GROWTH=[0,1,1,2,2,3,3,3,4,4,5]        # $24998 population growth per 8 frames by level
MANA_T=[0,0,0,0,1,2,3,4,5,6,20]       # $3b20c mana per 8 frames by level
B3_T=[0,1,2,3,4,5,6,7,8,10,20]        # $3b248 walker weapon class by level
DEC=1                                 # $37eb0 strength lost per walker step
class Mem:
    def __init__(s,b):
        s.m={}; o=0
        for a,n in REGIONS: s.m[a]=bytearray(b[o:o+n]); o+=n
    def _loc(s,a):
        for base,buf in s.m.items():
            if base<=a<base+len(buf): return buf,a-base
        raise KeyError(hex(a))
    def b(s,a): buf,o=s._loc(a); return buf[o]
    def sb(s,a): v=s.b(a); return v-256 if v>127 else v
    def w(s,a): buf,o=s._loc(a); return struct.unpack_from('>h',buf,o)[0]
    def uw(s,a): buf,o=s._loc(a); return struct.unpack_from('>H',buf,o)[0]
    def l(s,a): buf,o=s._loc(a); return struct.unpack_from('>i',buf,o)[0]
    def setw(s,a,v): buf,o=s._loc(a); struct.pack_into('>h',buf,o,((v+0x8000)&0xffff)-0x8000)
    def setb(s,a,v): buf,o=s._loc(a); buf[o]=v&0xff
    def setl(s,a,v): buf,o=s._loc(a); struct.pack_into('>i',buf,o,v)
MAP=0x36e78; OBJ=0x3c522; OCC=0x37fd4
def check(m,cell,off):                       # $18198
    if off==0: return 0
    c=cell+off
    if c<0 or c>=0x1000: return 1
    dx=off&0x3f
    if dx>3: dx-=64
    x=(cell&0x3f)+dx
    if x<0 or x>63: return 1
    t=m.b(MAP+c)
    return 3 if t==0 else 2 if t==0x2f else 0
def land_value(m,side,cell):                 # $18206
    mine=(side+0x1f)&0xff; v=0
    for k,off in enumerate(DOFF):
        r=check(m,cell,off)
        if r:
            if r==2: v-=15
            continue
        c=cell+off; t=m.b(MAP+c)
        if t==mine or t==0x0f:
            if v==0: v=50
            v+=15
        elif k==0: return 0
        d1=m.sb(OBJ+c)
        if k<9 and m.b(OBJ+cell)==0x2a and 0x29<=d1<=0x2c: continue
        if k!=0 and 0x20<d1<=0x2c: return 0
    if v<35: v=0
    if v==305: v=3050
    return v
def level_sprite(v): return 0x2a if v>=0xbea else v*10//0x131+0x20
def ent(m,i):
    a=ENT+ESZ*i
    return dict(fl=m.b(a),side=m.b(a+1),b2=m.b(a+2),b3=m.b(a+3),str=m.w(a+4),t6=m.w(a+6),cell=m.w(a+8),
                off=m.w(a+10),anim=m.w(a+12),tgt=m.l(a+14),last=m.w(a+18))
def run(path):
    data=open(path,'rb').read(); nrec=len(data)//RECLEN
    tabs=None
    stats={}
    def tally(k,ok):
        a=stats.setdefault(k,[0,0]); a[0]+=ok; a[1]+=1
    bad=[]
    for f in range(nrec//2):
        P=Mem(data[(2*f)*RECLEN:(2*f+1)*RECLEN]); Q=Mem(data[(2*f+1)*RECLEN:(2*f+2)*RECLEN])
        growth,mana_t,b3_t,dec=GROWTH,MANA_T,B3_T,DEC
        frame=(P.uw(0x3c4c8)+1)&0xffff; n=P.w(0x3c4e2); b222=P.w(0x3b222)
        # side baseline mana
        mana=[P.l(SIDE+16*s+12)+(1 if b222 else 0) for s in range(2)]
        pop=[0,0]; towns=[0,0]
        events=False; spawned={}
        E=[ent(P,i) for i in range(max(n,Q.w(0x3c4e2)))]
        QE=[ent(Q,i) for i in range(Q.w(0x3c4e2))]
        occupied=set(i for i in range(len(E)) if E[i]['str']>0)
        for i in range(n):
            e=E[i]
            if e['str']<=0: continue
            pop[e['side']]+=e['str']
            if e['fl']==1:
                # skip settlements touched by walker events this frame (merge/attack)
                v=land_value(P,e['side'],e['cell'])
                if v<1: tally('settle_vacate',QE[i]['fl']==2 and QE[i]['anim']==0); continue
                spr=level_sprite(v); lvl=spr-0x20
                if spr!=0x2a: towns[e['side']]+=1
                s=e['str']; newchild=None
                if frame&7==0:
                    mana[e['side']]+=mana_t[lvl]
                    cap=v
                    if s>cap:
                        # first free slot
                        j=next((k for k in range(0xd0) if (E[k]['str'] if k<len(E) else 0)<=0),None)
                        newchild=(j,s-(cap>>1)); s=cap>>1
                        if j is not None:
                            while len(E)<=j: E.append(dict(str=0,fl=0,side=0))
                            E[j]=dict(fl=2,side=e['side'],str=newchild[1],anim=0,b3=b3_t[lvl],cell=e['cell'])
                            if j>i: pass  # processed later in this frame (anim 0->1); pop added below
                    s+=growth[lvl]
                q=QE[i] if i<len(QE) else None
                ok_str = q is not None and q['str']==s
                if not ok_str: bad.append((f,i,'settle str',e['str'],s,q and q['str'],frame&7))
                tally('settle_str',ok_str); tally('settle_sprite',q is not None and q['anim']==spr)
                if frame&7==0: tally('settle_b3',q is not None and q['b3']==b3_t[lvl])
                if newchild and newchild[0] is not None:
                    j=newchild[0]; qc=QE[j] if j<len(QE) else None
                    tally('spawn',qc is not None and qc['str']==newchild[1] and qc['side']==e['side'] and qc['cell']==e['cell'])
                    if j>i: pass
            elif e['fl']==2:
                q=QE[i] if i<len(QE) else None
                step = e['anim']>6
                if not step:
                    tally('walker_anim',q is not None and q['anim']==e['anim']+1 and q['str']==e['str'])
                else:
                    if q is not None and q['fl']==2 and q['str']>0 and q['anim']==0:
                        tally('walker_step_str',q['str']==e['str']-dec)
                    else: events=True
        # spawned children with index > parent are also counted in pop in-loop
        for j,e in enumerate(E):
            if j>=n and e.get('str',0)>0: pop[e['side']]+=e['str']
        for s in range(2):
            qm=Q.l(SIDE+16*s+12)
            if not events: tally('mana',qm==mana[s])
            if not events: tally('pop',Q.l(SIDE+16*s+8)==pop[s])
            tally('towns',Q.w(SIDE+16*s+6)==towns[s])
    for k,(a,b) in stats.items(): print('%-16s %d/%d'%(k,a,b))
    for x in bad[:15]: print('MISMATCH',x)
if __name__=='__main__': run(sys.argv[1])
