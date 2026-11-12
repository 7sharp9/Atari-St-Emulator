#!/usr/bin/env python3
"""callcap $aae6 over a grid of (D0=dx, D1=dz) and compare with atan_port.atan2 and with math.atan2.
usage: atan_grid.py  (writes nothing; prints match count and max error vs exact atan2 in 1/65536 turns)"""
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent)); _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
import os, sys, re, math, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atan_port import atan2
R=str(ROOT)
vals=sorted(set([0,1,-1,7,-7,100,-100,999,-999,4096,-4096,30000,-30000,32767,-32768,40000,-40000,123457,-123457,1000000,-1000000,8000000,-8000000]))
cases=[(a,b) for a in vals for b in vals]
lines=['callcap aae6 2000 D0=%08x D1=%08x'%(a&0xffffffff,b&0xffffffff) for a,b in cases]
out=subprocess.run(['dotnet','exec',R+'/bin/Debug/net8.0/M68000.dll','resume',str(ANCHOR),'repl'],input='\n'.join(lines)+'\n',capture_output=True,text=True,env=dict(os.environ,ATARI_NOTRACE='1'),cwd=R).stdout
rets=[l for l in out.split('\n') if 'callcap $00aae6: returned' in l]
rd=[l for l in out.split('\n') if l.startswith('regdelta')]
assert len(rd)==len(cases)==len(rets),(len(rd),len(cases),len(rets))
ok=0; maxerr=0; worst=None
for (a,b),l,(a0,b0) in zip(cases,rd,[(a&0xffffffff,b) for a,b in cases]):
    m=re.search(r'D0 \$[0-9a-f]+->\$([0-9a-f]+)',l)
    obs=(int(m.group(1),16) if m else a0)&0xffff
    p=atan2(a,b)
    if obs==p: ok+=1
    else: print('diff',a,b,hex(obs),hex(p))
    if (a,b)!=(0,0):
        ex=math.atan2(a,b)/(2*math.pi)*65536
        e=((obs-ex+32768)%65536)-32768
        if abs(e)>maxerr: maxerr=abs(e); worst=(a,b,obs,ex)
print('callcap $aae6 grid',len(cases),'cases; port match',ok,'; max |error| vs exact atan2(dx,dz)*65536/2pi = %.1f units (%.3f deg) at'%(maxerr,maxerr*360/65536),worst)
print('atan2(0,0) ->',hex(atan2(0,0)))
