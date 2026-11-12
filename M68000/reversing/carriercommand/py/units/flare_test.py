#!/usr/bin/env python3
"""Flare-decoy test: hand-built type-17 homing missile (slot 24 $5fada) vs the player carrier ($5e95a), with flares in slots 17/18
($5f21a, $5f35a) placed at chosen Chebyshev distances. Samples the missile before each handler call ($1a3b2).
usage: flare_test.py <label> <d17|none> <d18|none> [ticks]"""
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent)); _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
import sys, os, subprocess, struct, re
R=str(ROOT)
snap=str(ANCHOR)
label=sys.argv[1]; d17=sys.argv[2]; d18=sys.argv[3]; N=int(sys.argv[4]) if len(sys.argv)>4 else 14
MX,MY=-8009664,-7795440          # open sea, >600000 from any island
def L(v): return '%08x'%(v&0xffffffff)
lines=[]
# missile, type 17, state 2, timers: +27=100 life, +28=1 (reload fires on first call), target ptr +30 = carrier
lines+=['w 5fada 01010011','w 5fade 00000000','w 5fae2 00000000','w 5fae4 '+L(MX),'w 5fae8 000000a0','w 5faec '+L(MY),
        'w 5faf4 02640100','w 5faf8 0005e95a','w 5fafc 00000000','w 5fb00 00000000','w 5fb16 0000000a']
# flares: only byte +1 bit0 is tested by the scan; keep $114e (flares aloft) = 0 so $1ef5c does not move them
if d17!='none': lines+=['w 5f21a 81010000','w 5f224 '+L(MX+int(d17)),'w 5f22c '+L(MY+0)]
if d18!='none': lines+=['w 5f35a 81010000','w 5f364 '+L(MX),'w 5f36c '+L(MY+int(d18))]
for k in range(N):
    lines+=['s 1','bp 1a3b2 400000','m 5fada 64']
env=dict(os.environ,ATARI_NOTRACE='1')
out=subprocess.run(['dotnet','exec',R+'/bin/Debug/net8.0/M68000.dll','resume',snap,'repl'],input='\n'.join(lines)+'\n',capture_output=True,text=True,env=env,cwd=R).stdout
hexl=[l for l in out.split('\n') if re.fullmatch(r'([0-9a-f]{2} )*[0-9a-f]{2}',l.strip()) and len(l.split())==64]
rows=[]
for l in hexl:
    b=bytes(int(t,16) for t in l.split())
    rows.append((b[26],b[27],b[28],struct.unpack('>L',b[30:34])[0],struct.unpack('>h',b[34:36])[0],struct.unpack('>h',b[36:38])[0],struct.unpack('>l',b[10:14])[0]-MX,struct.unpack('>l',b[18:22])[0]-MY,struct.unpack('>H',b[0:2])[0]))
print('==',label,'d17',d17,'d18',d18,'samples',len(rows))
for i,r in enumerate(rows): print(i,'state %d timer %d sub %d  tgt %08x  pitchT %d yawT %d  dx %d dy %d  w0 %04x'%r)
