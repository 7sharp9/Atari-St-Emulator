#!/usr/bin/env python3
"""GUARD: where the group that kills the party in the final base comes from. Replays death.py's arm 10 (labelled poke
14794 = 10) to $b5c2 + 3M, prints the group record at $1d33a, then watches writes to its first 6 bytes (x, y, size, carry,
flags) for 14M steps and prints each write (step, pc, addr, value) and the record every 1M steps.
  uv run python -I reversing/captive/py/world/station/guard.py > scratchpad/captive/station/guard.log 2>&1"""
import os, sys, struct
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
    nd = os.path.dirname(d)
    if nd == d: sys.exit('repo root not found')
    d = nd
R = os.environ.get('M68000_ROOT') or d
sys.path.insert(0, os.path.join(R, 'tools'))
from stclient import StServer
A6 = 0x1b5ce
W = os.path.join(R, 'scratchpad', 'captive')
OUT = os.path.join(W, 'station', 'survive')
os.makedirs(OUT, exist_ok=True)
w16 = lambda s, o: struct.unpack('>h', s.read(A6 + o, 2))[0]
l32 = lambda s, o: struct.unpack('>I', s.read(A6 + o, 4))[0]
s = StServer(R)
def pin():
    for _ in range(3):
        s('mouse', action='move', dx=-127, dy=-127); s('step', n=30000)
def goto(px, py):
    pin(); x = y = 0
    while (x, y) != (px, py):
        dx, dy = min(127, px - x), min(127, py - y)
        s('mouse', action='move', dx=dx, dy=dy); s('step', n=30000); x += dx; y += dy
def click(px, py, settle):
    goto(px, py); s('mouse', action='down', button='l'); s('step', n=60000)
    s('mouse', action='up', button='l'); s('step', n=settle)
def party(): p = l32(s, 26); return (p >> 16, p & 0xffff)
def st(): return dict(party=party(), face=w16(s, 30), live410=w16(s, 410), e14800=w16(s, 14800), mode=w16(s, 13564))
def key(k):
    s('kbd', bytes=[k]); s('step', n=60000); s('kbd', bytes=[k | 0x80]); s('step', n=300000)

s('load', snapshot=os.path.join(W, 'mission1.snap'), disk=os.path.join(W, 'tmb097.st'))
click(78, 85, 300000)
s('poke', addr=A6 + 14794, width=2, value=10)        # LABELLED POKE (as station.py arm 10)
click(204, 76, 0)
for _ in range(200):
    s('step', n=500000)
    if w16(s, 14858) == 6: break
goto(252, 75)
s('mouse', action='down', button='l'); s('step', n=60000); s('mouse', action='up', button='l')
r = s('run', max_steps=25_000_000, until_pc=[0xb5c2, 0xb5c2 | 0x80000000])
print('to $b5c2:', r['reason'], 'D0', s.reg('d0') & 0xffff, 'D2', s.reg('d2') & 0xffff, st())
r = s('run', max_steps=3_000_000, until_pc=[0xb5c6, 0xb5c6 | 0x80000000])
print('to $b5c6 (max_steps = still generating):', r['reason'], st())
G = 0x1d33a
print('record at the fork:', s.read(G, 16).hex(), 'party', party())
if 'caller' in sys.argv:
    # stop on the first $d390 write to the record's +5 and print the stack: which caller ($a92a view, or a hit path)
    s('watch_add', lo=G + 5, hi=G + 5, kind='w', pc_lo=0xd390, pc_hi=0xd390, stop=True)
    r = s('run', max_steps=14_000_000)
    sp = s.reg('a7'); print('stop', r['reason'], 'pc', hex(s.reg('pc')), 'stack', s.read(sp, 32).hex(), 'record', s.read(G, 8).hex(), st())
    s.close(); sys.exit()
wid = s('watch_add', lo=G, hi=G + 5, kind='w')
for i in range(14):
    s('step', n=1_000_000)
    print(f'+{i+1}M', s.read(G, 16).hex(), st(), flush=True)
    if w16(s, 14800) != 0: break
for w in s('watch_events'):
    for e in w['events'][:80]: print('write', e['step'], e['pc'], e['addr'], e['value'])
s.close()
