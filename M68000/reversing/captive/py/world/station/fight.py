#!/usr/bin/env python3
"""Do the hand keys hurt group 78 at the final base's lift arrival? From scratchpad/captive/station/trill/l2.snap (trill.py
goto 61,1 then lift up; party (45,1), group 78 = $1ceca hostile and aware at (46,0)). Two arms from one fork, 40
cycles each: turn to face the group whenever it is adjacent, then 'fight' presses scan codes $06-$0d (the eight
per-hand counters at 338(A6), dispatcher $8912 -> $b16e, read) and steps 300k; 'control' steps the same time with no
hand key. Prints party, group cell, flags, member hit points, 410 and 14800 every 4 cycles.
  uv run python -I reversing/captive/py/world/station/fight.py"""
import os, sys, struct
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
    nd = os.path.dirname(d)
    if nd == d: sys.exit('repo root not found')
    d = nd
R = os.environ.get('M68000_ROOT') or d
sys.path.insert(0, os.path.join(R, 'tools')); from stclient import StServer
A6=0x1b5ce; G=0x1ceca
s=StServer(R); s('load', snapshot=os.path.join(R, 'scratchpad', 'captive', 'station', 'trill', 'l2.snap'))
w16=lambda o: struct.unpack('>h', s.read(A6+o,2))[0]
VEC=((0,-1),(-1,0),(0,1),(1,0))
base=s('fork')['id']
def key(k, settle=60000):
    s('kbd',bytes=[k]); s('step',n=60000); s('kbd',bytes=[k|0x80]); s('step',n=settle)
for arm in ('fight','control'):
    s('restore', id=base); hits={}
    for i in range(40):
        g=s.read(G,16); gx,gy=g[0],g[1]; px,py=w16(26),w16(28)
        d=(gx-px,gy-py)
        if d in VEC:
            f=VEC.index(d)
            while (w16(30)&3)!=f: key(0x67 if (f-(w16(30)&3))&3==1 else 0x69, 200000)
        if arm=='fight':
            for k in range(6,14): key(k, 20000)
        s('step', n=300000 if arm=='fight' else 300000+8*80000)
        if i%4==3:
            g=s.read(G,16); print(arm, i, 'party',(w16(26),w16(28)),'face',w16(30),'group',(g[0],g[1]),'flags',g[4:6].hex(),'hp',int.from_bytes(g[10:12],'big'),'size',int.from_bytes(g[2:4],'big'),'410',w16(410),'14800',w16(14800), flush=True)
        if w16(14800): break
s.close()
