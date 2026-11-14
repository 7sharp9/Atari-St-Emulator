#!/usr/bin/env python3
"""Does a party that moves off (53,0) survive the final base? Replays death.py's arm 10 (labelled poke 14794 = 10) to
$b5c2 + 3M steps (the generator is still running: $b5c6 comes within the next 2M), forks there, then per arm: step T steps, send a key sequence, run to 40M steps after
the fork in 1M chunks, logging party, 410 (live droids), 14800 (failed) and hits on the attack path. Arm 'none' is the
same-fork, same-budget control.
  uv run python -I reversing/captive/py/world/station/survive.py [T_millions,...] > scratchpad/captive/station/survive.log 2>&1
Keys facing S (Known traps): $68 forward, $6e back, $6c strafe W, $6a strafe E; make, 60k steps, break, 300k steps."""
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
base = s('fork')['id']
HITS = ['$10e4a', '$f884', '$9a9a', '$876a']
G = 0x1d33a                                             # the attacking group (death.py 'trace'; guard.py)
if 'save' in sys.argv:
    # fwd1 at T = 4, run to +12M, save scratchpad/captive/station/fin_safe.snap (party (53,1), view up, group passed)
    s('step', n=4_000_000); key(0x68); s('step', n=7_640_000)
    print('save', st()); s('save', path=os.path.join(W, 'station', 'fin_safe.snap')); s.close(); sys.exit()
if 'track' in sys.argv:
    # fwd1 at T = 4M; group record, party and a render every 1M steps to +20M
    VIEW = 'view' in sys.argv                            # 'track view': no key, 250k renders from +6M to +8M
    if VIEW: s('step', n=6_000_000); total = 6_000_000
    else: s('step', n=4_000_000); key(0x68); total = 4_360_000
    while total < (8_000_000 if VIEW else 20_000_000):
        n = 250_000 if VIEW else 1_000_000
        s('step', n=n); total += n
        print(f'+{total}', 'group', s.read(G, 8).hex(), st(), flush=True)
        s('render', path=os.path.join(OUT, f'track{"v" if VIEW else ""}_{total / 1e6:g}M.png'))
    s.close(); sys.exit()
ARMS = {'none': [], 'fwd1': [0x68], 'fwd3': [0x68, 0x68, 0x68], 'strafeW': [0x6c], 'fwd1W': [0x68, 0x6c, 0x6c]}
Ts = [float(x) for x in sys.argv[1].split(',')] if len(sys.argv) > 1 and sys.argv[1][0].isdigit() else [4, 7]
for T in Ts:
    for name, keys in ARMS.items():
        if os.environ.get('ARMS') and name not in os.environ['ARMS'].split(','): continue
        if T != Ts[0] and name == 'none': continue          # the control does not depend on T
        s('restore', id=base)
        s('step', n=int(T * 1_000_000))
        pre = st()
        for k in keys: key(k)
        post = st(); used = int(T * 1_000_000) + len(keys) * 360000
        total = used; agg = {}; died = None
        while total < 40_000_000:
            n = min(1_000_000, 40_000_000 - total)
            h = s('hits', steps=n, addrs=HITS); total += n
            for x in h['hits']:
                if x['count']: agg[x['addr']] = agg.get(x['addr'], 0) + x['count']
            if died is None and w16(s, 14800) != 0: died = total; break
        s('render', path=os.path.join(OUT, f'T{T}_{name}.png'))
        print(f'T={T}M arm {name}: before keys {pre} after keys {post} end +{total} {st()} died_by {died} hits {agg}', flush=True)
s.close()
