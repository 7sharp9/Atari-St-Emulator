#!/usr/bin/env python3
"""Prove the carrier physics model ($1e4a0 speed/heading/position) against the emulator.
usage: carrier_proof.py <snap> <N ticks> <pokes...>   (pokes are REPL 'w' lines, e.g. 'w 648 00280000')
Runs REPL: pokes, then N times (s 1; bp 1e4a0; dump state), parses, and compares tick-to-tick."""
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent)); _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
import sys, subprocess, struct, os, re
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from atan_port import atan2
R=str(ROOT)
snap=sys.argv[1]; N=int(sys.argv[2]); pokes=sys.argv[3:]
ram=globals()['ram'](ANCHOR)
SIN=[struct.unpack('>h',ram[0x1864+2*i:0x1864+2*i+2])[0] for i in range(4096)]
lines=list(pokes)
for k in range(N+1):
    lines += ['s 1','bp 1e4a0 400000','m 5e95a 64','m 642 14','m 8e8 2','m cf8 4','m 65a 6','m af6 2','m 122c 1','m 62cda 56','m 459 1','m 650 10']
env=dict(os.environ,ATARI_NOTRACE='1')
out=subprocess.run(['dotnet','exec',R+'/bin/Debug/net8.0/M68000.dll','resume',snap,'repl'],input='\n'.join(lines)+'\n',capture_output=True,text=True,env=env,cwd=R).stdout
hexl=[l for l in out.split('\n') if re.fullmatch(r'([0-9a-f]{2} )*[0-9a-f]{2}',l.strip())]
per=10
assert len(hexl)>=per*(N+1), (len(hexl), out[-500:])
def B(l): return bytes(int(t,16) for t in l.split())
S=[]
for k in range(N+1):
    e,f,ph,fu,rg,pw,dk,isl,ui,dst=[B(hexl[k*per+j]) for j in range(per)]
    S.append(dict(x=struct.unpack('>l',e[10:14])[0],y=struct.unpack('>l',e[18:22])[0],H=struct.unpack('>H',e[6:8])[0],
      isl=struct.unpack('>L',e[60:64])[0], flags=f[0], r=struct.unpack('>h',f[2:4])[0], s=struct.unpack('>h',f[4:6])[0], t=struct.unpack('>h',f[6:8])[0],
      prox=struct.unpack('>h',f[10:12])[0], c64e=struct.unpack('>h',f[12:14])[0], f643=f[1], ix=struct.unpack('>l',isl[2:6])[0], iy=struct.unpack('>l',isl[10:14])[0], w48=struct.unpack('>h',isl[48:50])[0], w50=struct.unpack('>h',isl[50:52])[0], ui=ui[0], dx_=struct.unpack('>l',dst[0:4])[0], dy_=struct.unpack('>l',dst[4:8])[0], cruise=struct.unpack('>h',dst[8:10])[0],
      ph=struct.unpack('>H',ph)[0], fuel=struct.unpack('>L',fu)[0], c65c=struct.unpack('>h',rg[2:4])[0], c65e=struct.unpack('>h',rg[4:6])[0],
      af6=struct.unpack('>h',pw)[0], c122c=dk[0]))
def s16(v): v&=0xffff; return v-65536 if v&0x8000 else v
def step(a):
    """predict the state at the next $1e4a0 call from the state at this call (manual mode / recovery; no autopilot destination, no key or chevron held, $459 set)"""
    s=a['s']; t=a['t']; r=a['r']; H=a['H']; f=a['flags']; f643=a['f643']; c64e=a['c64e']
    fuel=a['fuel']
    r_in=r
    if f&1:                                   # $1e692
        if f643==0:                           # recovery after grounding: controls locked for $64e ticks
            c64e=(c64e-1)&0xffff
            if c64e==0: f&=0x7e; f643=1
        elif not (f&2):                       # autopilot engaged with no course: brake
            f|=0x80; t=0
        else:                                 # $1e6ca: steer to ($650,$654) at cruise speed $658
            ddx=a['dx_']-a['x']; ddy=a['dy_']-a['y']
            dist=max(abs(ddx),abs(ddy))
            d4=a['cruise']
            if dist<=0x7d0 and d4>0x20: d4=0x20
            t=d4
            if dist<0x3e8:                    # arrival
                f&=0xfc; f|=0x80; t=0
            else:
                d0=s16(atan2(ddx,ddy)-H)
                if abs(d0)>0x100: t=0x10
                d0>>=2
                d0=max(-255,min(255,d0))
                dd=s16(d0-r); 
                if abs(dd)>32: dd=32 if dd>0 else -32
                r=s16(r+dd)
    if a['fuelflag']:
        fuel=max(0,fuel-abs(s)*4)
    af=a['af6']
    d1=min((af&0xffff)>>1,0x70)
    if a['c65e'] or a['c122c'] or a['isl']: d1=min(d1,0x3c)
    d2=(-af)>>3
    d0=t if fuel else 0
    if fuel:
        if d0>d1: d0=d1
        elif d0<d2: d0=d2
    diff=d0-s
    if diff:
        st=diff>>5
        if st==0: st=1
        s=s16(s+st)
    if f&0x80:                                # $1e58a braking: yaw rate decays
        if r==0: f&=0x7f
        else:
            d=r>>3
            if d==0: d=1
            r=r-d      # $1e490: D0=D1; D0>>=3 (asr), if 0 -> 1; D0=-D0; D0+=D1
    H=(H+int(r/6))&0xffff
    sp=s
    if not (a['c65c'] or a['c65e'] or a['isl']): sp=s16(sp*2)
    sn=SIN[((H&0xfff0)>>3)>>1]; cs=SIN[(((H&0xfff0)+0x4000)&0xffff)>>4]
    dx=s16(((4*sp*sn)&0xffffffff)>>16); dy=s16(((4*sp*cs)&0xffffffff)>>16)
    x=a['x']+dx; y=a['y']+dy
    prox=a['prox']; hit=False
    if not a['isl']: prox=0x24   # observed: no island pointer -> $64c = $24 (set outside $1e4a0)
    if a['isl']:
        D=max(abs(a['ix']-x)-a['w48'],abs(a['iy']-y)-a['w50'])-10000
        q=int(D/256)
        if q>=0: prox=min(q,0x24)
        else:
            if (f&1) and f643==0: prox=0
            elif (f&1) and f643!=0 and False: pass
            else:
                hit=True; prox=0
                f|=0x81; f643=0; c64e=0x32
                t=-0x20 if s>=0 else 0x20      # $1e640: D1=$20; tst.w $646; bmi -> keep, else neg
                s=0
    return dict(x=x,y=y,H=H,s=s,t=t,r=r,fuel=fuel,prox=prox,flags=f,f643=f643,c64e=c64e,hit=hit)
ok=0; bad=0; hits=[]; isl_changes=[]
for k in range(N):
    a=S[k]; b=S[k+1]
    a['fuelflag']=((a['ph']&0xf)==0)
    p=step(a)
    m=all(p[q]==b[q] for q in ('x','y','H','s','t','r','fuel','prox','flags','f643','c64e'))
    if not m and a.get('isl')!=b.get('isl'): isl_changes.append(k)
    if p['hit']: hits.append(k)
    if m: ok+=1
    else:
        bad+=1
        if bad<=6: print('MISMATCH tick',k,'obs',{q:b[q] for q in('x','y','H','s','t','r','fuel','prox','flags','f643','c64e')},'pred',p,'state',{q:a[q] for q in('x','y','H','s','t','r','ph','isl','c65c','c65e','c122c','af6','fuel')})
print('grounded events at ticks',hits); print('island-pointer changes at mismatch ticks',isl_changes); print('branch census: ticks with isl==0 (open sea, speed doubled):',sum(1 for q in S[:N] if not q['isl']),' autopilot-engaged ticks (flags&1, $643!=0):',sum(1 for q in S[:N] if q['flags']&1 and q['f643']),' max |speed|:',max(abs(q['s']) for q in S),' min prox:',min(q['prox'] for q in S),' final flags %02x'%S[N]['flags']); print('ticks',N,'match',ok,'mismatch',bad)
print('first',{q:S[0][q] for q in('x','y','H','s','t','r','ph','fuel','isl')}); print('last',{q:S[N][q] for q in('x','y','H','s','t','r','ph','fuel','isl')})
dxy=(S[N]['x']-S[0]['x'],S[N]['y']-S[0]['y']); print('displacement over run (world units, display/1678)',dxy)
if os.environ.get('CP_TRACE'):
    for k in range(0,N+1,int(os.environ['CP_TRACE'])): print('tick',k,'speed $646',S[k]['s'],'target $648',S[k]['t'],'engines effect $af6',S[k]['af6'],'heading',S[k]['H'],'yaw $644',S[k]['r'],'x',S[k]['x'],'z',S[k]['y'])
