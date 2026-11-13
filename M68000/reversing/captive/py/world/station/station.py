#!/usr/bin/env python3
"""Station landing (world.md section 1, "Final target"): select map slot 0, ORBIT, LAND with the exit count
14794(A6) poked to 0, 9 and 10 (the only difference between arms), and count what $2f5f4's tail does.

  uv run python -I reversing/captive/py/world/station/station.py            (from M68000/)

Start: scratchpad/captive/mission1.snap + tmb097.st (no sidecar). Pointer pinned top-left (three mouse move -127 -127),
then 1:1: the station dot is at pixel (78,85) at zoom 8 (cursor (6656,6656) = -13566(A6) table slot 0 at $1b5ce+13566).
Per arm: select, labelled poke 14794, ORBIT (202,72), run to 14858 = 6, LAND (251,70), then
  (1) 25M steps of `hits` on $2f66e $2f676 $2f4f0 $2f5f4 $885e + a write watch on 14788(A6) (request word);
  (2) from the same pre-LAND state, run to the fed_MapGen call $b5c2 (budget 25M) and read D0/D1/D2, 14788, 32(A6), mode.
Renders and station.log (the stdout below) under scratchpad/captive/station/."""
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
OUT = os.path.join(W, 'station'); os.makedirs(OUT, exist_ok=True)

class _Tee:
    def __init__(self, *f): self.f = f
    def write(self, x): [f.write(x) for f in self.f]
    def flush(self): [f.flush() for f in self.f]
sys.stdout = _Tee(sys.stdout, open(os.path.join(OUT, 'station.log'), 'w'))
w16 = lambda s, o: struct.unpack('>h', s.read(A6 + o, 2))[0]
BEGIN = 25_000_000
ADDRS = ['$2f66e', '$2f676', '$2f4f0', '$2f5f4', '$885e', '$b5c2']

s = StServer(R)
s('load', snapshot=os.path.join(W, 'mission1.snap'), disk=os.path.join(W, 'tmb097.st'))
mission1 = s('fork')['id']

def pin():
    for _ in range(3):
        s('mouse', action='move', dx=-127, dy=-127); s('step', n=30000)

def goto(px, py):
    """pointer from the pinned (0,0) to (px,py): one mouse move is clamped to +-127 per axis, so split it"""
    pin()
    x = y = 0
    while (x, y) != (px, py):
        dx, dy = min(127, px - x), min(127, py - y)
        s('mouse', action='move', dx=dx, dy=dy); s('step', n=30000)
        x += dx; y += dy

def click(px, py, settle):
    goto(px, py)
    s('mouse', action='down', button='l'); s('step', n=60000)
    s('mouse', action='up', button='l'); s('step', n=settle)

def st(): return {k: w16(s, o) for k, o in (('slot14782', 14782), ('slot14856', 14856), ('req14788', 14788), ('cnt14794', 14794), ('mode13564', 13564), ('ship14858', 14858), ('land14820', 14820))}

res = {}
for cnt in (0, 9, 10):
    s('restore', id=mission1)
    click(78, 85, 300000)                                           # select the station
    print(f'--- arm 14794 = {cnt}: after select {st()}, cursor ({w16(s,14852)},{w16(s,14854)})')
    s('poke', addr=A6 + 14794, width=2, value=cnt)                  # LABELLED POKE: exit count
    click(204, 76, 0)                                               # ORBIT
    for _ in range(200):
        s('step', n=500000)
        if w16(s, 14858) == 6: break
    print(f'    in orbit: {st()}')
    goto(252, 75)   # LAND: pointer on the icon
    pre = s('fork')['id']
    wid = s('watch_add', lo=A6 + 14788, hi=A6 + 14789, kind='w')
    wid = wid.get('id') if isinstance(wid, dict) else wid
    s('mouse', action='down', button='l')
    h = s('hits', steps=60000, addrs=ADDRS)
    s('mouse', action='up', button='l')
    h2 = s('hits', steps=BEGIN, addrs=ADDRS)
    cnts = {a['addr']: a['count'] + b['count'] for a, b in zip(h['hits'], h2['hits'])}
    ev = s('watch_events', id=wid)
    print('    hits', cnts)
    print('    writes to 14788:', [(e['pc'], e['value']) for w in ev for e in w['events'] if w['id'] == wid])
    print(f'    after {BEGIN} steps: {st()}, 32(A6) = {w16(s,32)}')
    s('render', path=os.path.join(OUT, f'arm{cnt}_after.png'))
    s('watch_remove', id=wid)
    # phase 2: same pre-LAND state, same click and budget, stop at the fed_MapGen call
    s('restore', id=pre)
    s('mouse', action='down', button='l'); s('step', n=60000); s('mouse', action='up', button='l')
    r = s('run', max_steps=BEGIN, until_pc=[0xb5c2, 0xb5c2 | 0x80000000])
    if r['reason'] == 'until':
        print(f'    $b5c2 reached: D0 = {s.reg("d0") & 0xffff:#x}, D1 = {s.reg("d1") & 0xffff:#x}, D2 = {s.reg("d2") & 0xffff}, '
              f'request 14788 = {w16(s,14788)}, 32(A6) = {w16(s,32)}, 14790 = {w16(s,14790)}')
    else:
        print(f'    $b5c2 not reached in {BEGIN} steps ({r["reason"]}); 14788 = {w16(s,14788)}')
    res[cnt] = cnts
s.close()
