"""fightcheck.py <snap> <nfights> : force Armageddon ($3d524=1) so walkers meet, then for each call of the
combat routine $1063a capture entity state at entry and at return ($ed30) and compare with the
Python model of one combat round (fight_round). Also checks the win bookkeeping of $108b8."""
import sys,struct
from repl import Repl
ENT=0x3b278; ESZ=0x16
def rng(seed):
    s=((seed*0x24a1)&0xffff); s=(s+0x24df)&0xffff; s&=0x7fff; return s
def tdiv(a,b): q=abs(a)//abs(b); return q if (a>=0)==(b>0) else -q
def w16(v): return ((v+0x8000)&0xffff)-0x8000
def fight_round(S,O,seed):
    """S=(str,b3) attacker (flags==8 entity), O=(str,b3) its opponent (entity S.+6). returns new strs, seed"""
    seed=rng(seed); r1=seed%3+1; seed=rng(seed); r2=seed%3+1
    X=r1*O[0]; Y=r2*S[0]
    m=Y if X>Y else X
    newO=w16(O[0]-(tdiv(m,100)*S[1]+10)); newS=w16(S[0]-(tdiv(m,100)*O[1]+10))
    return newS,newO,seed
def ent(b,i):
    a=i*ESZ; f,side,b2,b3,st,t6,cell=struct.unpack_from('>BBBBhhh',b,a); return dict(fl=f,side=side,b3=b3,str=st,t6=t6,cell=cell)
if __name__=='__main__':
    r=Repl(sys.argv[1]); n=int(sys.argv[2])
    r.cmd('w 3d524 00010820')
    ok=tot=0; wins=[0,0]; deaths=0
    for k in range(n):
        out,g=r.cmd('u 1063a 40000000')
        if g['PC']!=0x1063a: print('no more fights'); break
        a7=g['A7']; stk=r.mem(a7,10); ptr=struct.unpack_from('>I',stk,4)[0]; idx=struct.unpack_from('>h',stk,8)[0]
        assert ptr==ENT+ESZ*idx
        pre=r.mem(ENT,0xd3*ESZ); seed=struct.unpack('>H',r.mem(0x3d52e,2))[0]
        mpre=[struct.unpack('>i',r.mem(0x3b232+16*s,4))[0] for s in range(2)]
        bw=struct.unpack('>hh',r.mem(0x3c514,4))
        out,g=r.cmd('u ed30 2000000')
        post=r.mem(ENT,0xd3*ESZ); seed2=struct.unpack('>H',r.mem(0x3d52e,2))[0]
        mpost=[struct.unpack('>i',r.mem(0x3b232+16*s,4))[0] for s in range(2)]
        bw2=struct.unpack('>hh',r.mem(0x3c514,4))
        S=ent(pre,idx); oi=S['t6']; O=ent(pre,oi)
        nS,nO,sd=fight_round((S['str'],S['b3']),(O['str'],O['b3']),seed)
        pS=ent(post,idx); pO=ent(post,oi)
        if nS>0 and nO>0:
            good = pS['str']==nS and pO['str']==nO and sd==seed2
            tot+=1; ok+=good
            if not good: print('MISMATCH',k,S,O,'pred',nS,nO,'post',pS['str'],pO['str'],hex(seed),hex(seed2),hex(sd))
        else:
            deaths+=1
            win,lose=(idx,oi) if nO<=0 and nS>0 else (oi,idx) if nS<=0 and nO>0 else (None,None)
            print('RESOLVE k=%d S#%d%s O#%d%s pred S=%d O=%d post S=%d(fl%02x) O=%d(fl%02x) mana %s->%s battles %s->%s'%(k,idx,(S['side'],S['str'],S['b3'],S['fl']),oi,(O['side'],O['str'],O['b3'],O['fl']),nS,nO,pS['str'],pS['fl'],pO['str'],pO['fl'],mpre,mpost,bw,bw2))
    print('fight rounds (both survive): %d/%d matched; resolutions seen: %d'%(ok,tot,deaths))
    r.close()
