# check the $32c4 box derivation against per-frame records (run/rec.bin from recdump.lua)
import os,sys
from rd import rom
here=os.path.dirname(os.path.abspath(__file__))
d=open(os.environ.get('REC', os.path.join(here,'../../../scratchpad/finalfight/run/rec.bin')),'rb').read()
VIC=os.environ.get('VIC','cody')
S=4+8+192+192
def w(r,o): return int.from_bytes(r[o:o+2],'big')
def l(r,o): return int.from_bytes(r[o:o+4],'big')
def sw(v): return v-65536 if v&0x8000 else v
def romw(a): return int.from_bytes(rom[a:a+2],'big')
def expect(r):
    A0=l(r,56); e={}
    d45=r[45]
    if d45==0 or (d45&0x80 and w(r,14)!=w(r,10)): e['112']=0
    else:
        ab=(A0+((d45&0x7f)<<4)+romw(A0))&0xffffffff
        e['112']=ab; e['118']=(w(r,10)+romw(ab+2))&0xffff
    if r[97] or r[44]==0: e['120']=0
    else:
        hb=A0+(r[44]<<3); e['120']=hb; e['126']=(w(r,10)+romw(hb+2))&0xffff
    flip=r[46]
    if e['112']:
        o=romw(ab); e['116']=(w(r,6)-o if flip else w(r,6)+o)&0xffff
    if e['120']:
        o=romw(hb); e['124']=(w(r,6)-o if flip else w(r,6)+o)&0xffff
    return e
tot={}; bad={}
for who,off in (('cody',12),('bred',12+192)):
    n=0; ok={k:0 for k in ('112','116','118','120','124','126')}; cnt={k:0 for k in ok}
    for i in range(len(d)//S):
        r=d[i*S+off:i*S+off+192]
        if r[0]==0: continue
        e=expect(r); n+=1
        for k,v in e.items():
            cnt[k]+=1
            have=l(r,int(k)) if k in('112','120') else w(r,int(k))
            ok[k]+= have==v
    print(who,'frames in use',n,'match/checked',{k:'%d/%d'%(ok[k],cnt[k]) for k in ok})

def aabb(att, vic):
    """$7932 test: attacker 112/116/118 vs victim 120/124/126; descriptor +4 half width, +6 half height"""
    a=l(att,112); h=l(vic,120)
    if not a or not h: return None
    sx=romw(a+4)+romw(h+4); sy=romw(a+6)+romw(h+6)
    dx=sw((w(vic,124)-w(att,116))&0xffff); dy=sw((w(vic,126)-w(att,118))&0xffff)
    return abs(dx)<=sx and abs(dy)<=sy, dx,sx,dy,sy
print('frame overlap(bred->cody) / cody hp / hp drop')
prev=None
hits=[];ov=[]
for i in range(len(d)//S):
    f=int.from_bytes(d[i*S:i*S+4],'big')
    c=d[i*S+12:i*S+12+192]; b=d[i*S+12+192:i*S+12+384]
    if VIC=='bred': c,b=b,c   # attacker is the other record
    hp=w(c,24)
    if prev is not None and hp<prev: hits.append((f,prev,hp))
    prev=hp
    r=aabb(b,c)
    if r and r[0]: ov.append((f,)+r[1:])
print('hp drops (frame,old,new):',hits)
print('frames with predicted overlap attacker->victim:',len(ov), [o[0] for o in ov][:40])
