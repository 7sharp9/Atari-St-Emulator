#!/usr/bin/env python3
"""Prove the carrier repair model ($1713c repair step, $171d4 per-system effect) against the emulator.
Samples the 10 system records at $af0 (stride 8: +0 level, +2 max, +4 priority 0/1/2, +6 effect) at each
entry to $1713c, predicts the next entry's records, and counts matches.
usage: repair_proof.py <snap> <calls> <REPL poke lines...>"""
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent)); _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
import sys, os, re, subprocess, struct
R=str(ROOT)
snap=sys.argv[1]; N=int(sys.argv[2]); pokes=sys.argv[3:]
NAMES=['ENGINES','RADAR','COMMUNICATIONS','OBSERVATION TURRET','LASER CANNON','FLARE LAUNCHER','SURFACE TO SURFACE MISSILES','LIFT','AUTOMATIC REPAIR SYSTEMS','SUPERSTRUCTURE']
KIND=['lin2','bin','bin','bin','lin2','bin','bin','bin','lin','lin']   # handler table $171ee
lines=list(pokes)
for k in range(N+1): lines+=['s 1','bp 1713c 30000000','m af0 80','m b58 6']
out=subprocess.run(['dotnet','exec',R+'/bin/Debug/net8.0/M68000.dll','resume',snap,'repl'],input='\n'.join(lines)+'\n',capture_output=True,text=True,env=dict(os.environ,ATARI_NOTRACE='1'),cwd=R).stdout
hexl=[l.split() for l in out.split('\n') if re.fullmatch(r'([0-9a-f]{2} )*[0-9a-f]{2}',l.strip())]
recs=[];
for k in range(N+1):
    b=bytes(int(t,16) for t in hexl[2*k]); g=bytes(int(t,16) for t in hexl[2*k+1])
    recs.append(([struct.unpack('>4H',b[8*i:8*i+8]) for i in range(10)], struct.unpack('>3H',g)))
def effect(kind,cur,mx):                      # $17216 / $1723c / $1724e
    if kind=='lin2':
        if cur==mx: return 0x100
        v=((cur<<8)//(mx>>1))&0xffff; v=(v-0x100)&0xffff
        return 0 if v&0x8000 else v
    if kind=='bin': return 0xff00 if cur>(mx>>1) else 0x0000   # st/sf on the high byte of +6
    return ((cur<<8)//mx)&0xffff
def repair(S):                                  # $1713c
    cnt=[0,0,0]
    for cur,mx,pr,ef in S:
        if cur!=mx: cnt[min(pr,2) if pr in (0,1) else 2]+=1
    lvl=0 if cnt[0] else (1 if cnt[1] else 2); n=cnt[lvl]
    out=[list(r) for r in S]
    if n:
        rate=((0x96*S[8][3])>>8)//n
        for r in out:
            if r[2]==lvl and r[0]!=r[1]: r[0]=min(r[0]+rate,r[1])
    else: rate=None
    for i,r in enumerate(out):                  # $171d4 runs every frame after; effect from the new level
        e=effect(KIND[i],r[0],r[1])
        r[3]=(e&0xff00)|(r[3]&0xff) if KIND[i]=='bin' else e
    return [tuple(r) for r in out],lvl,n,rate
ok=0
for k in range(N):
    p,lvl,n,rate=repair(recs[k][0]); obs=recs[k+1][0]
    m=(p==obs); ok+=m
    print('call',k,'level',['HIGH','MEDIUM','LOW'][lvl],'n',n,'rate',rate,' b58/b5a/b5c',recs[k+1][1],'levels',[r[0] for r in obs],'OK' if m else 'MISMATCH pred %s'%[r for r in p])
print('repair calls',N,'match',ok)
