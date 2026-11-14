#!/usr/bin/env python3
"""Drive the party through the final base to Trill by play: keypad steps, view clicks on doors, lock panels set by
clicks, the coded door's corner presses, the lift icon. No pokes. Each leg starts from a snapshot and saves one.
  uv run python -I reversing/captive/py/world/station/trill.py <in.snap> <out.snap> <leg> [args]
Legs:
  goto X,Y        shortest path over open tiles (> $1a), doors handled on the way
  lift up|down    click the lift icon on the lift cell
  route X,Y       follow the generator's dig arrows (plane 2 bits 0-2) from X,Y back to the party's cell, reversed
  wait N          step N million steps, logging Trill's group and the end-screen state
Snapshots are relative to scratchpad/captive/station/trill/ unless absolute. Start: ../fin_safe.snap (survive.py save).
Keys: $68 forward, $67 facing + 1, $69 facing - 1 (0 N, 1 W, 2 S, 3 E). View click (105,110) = the cell ahead.
The run stops (and still saves) on a step it cannot make or explain, or when 14800(A6) becomes nonzero."""
import os, sys, struct, collections
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
    nd = os.path.dirname(d)
    if nd == d: sys.exit('repo root not found')
    d = nd
R = os.environ.get('M68000_ROOT') or d
sys.path.insert(0, os.path.join(R, 'tools'))
from stclient import StServer
A6 = 0x1b5ce
TILES, P2, LOCKS, CODED = A6 + 9242, A6 + 11322, A6 + 8628, A6 + 2330
VEC = ((0, -1), (-1, 0), (0, 1), (1, 0))
OUT = os.path.join(R, 'scratchpad', 'captive', 'station', 'trill')
os.makedirs(OUT, exist_ok=True)
sp = lambda p: p if os.path.isabs(p) else os.path.join(OUT, p)
s = StServer(R)
s('load', snapshot=sp(sys.argv[1]))
w16 = lambda o: struct.unpack('>h', s.read(A6 + o, 2))[0]
tile = lambda x, y: s.read(TILES + y * 64 + x, 1)[0] & 0x7f
pos = lambda: (w16(26), w16(28))
def st(): return f'party {pos()} face {w16(30)} 410={w16(410)} 14798={w16(14798)} 14800={w16(14800)} mode={w16(13564)}'
def key(k, settle=300000):
    s('kbd', bytes=[k]); s('step', n=60000); s('kbd', bytes=[k | 0x80]); s('step', n=settle)
def click(x, y, settle=300000):
    for _ in range(3):
        s('mouse', action='move', dx=-127, dy=-127); s('step', n=30000)
    while x or y:
        mx, my = min(x, 127), min(y, 127)
        s('mouse', action='move', dx=mx, dy=my); s('step', n=30000); x -= mx; y -= my
    s('mouse', action='down', button='l'); s('step', n=60000); s('mouse', action='up', button='l'); s('step', n=settle)
def face(f):
    for _ in range(4):
        c = w16(30) & 3
        if c == f: return
        key(0x67 if (f - c) & 3 == 1 else 0x69)
    raise SystemExit(f'cannot face {f}: {st()}')
def locks():
    out = {}
    for i in range(32):                                  # 13270(A6) is not the count here (18 against 32 records)
        r = s.read(LOCKS + 10 * i, 10)
        if r[9] != 0x20: break
        out[(r[6], r[7])] = dict(i=i, W=(r[0], r[1]), code=int.from_bytes(r[2:4], 'big'), key=r[8] & 3, door=(r[8] >> 2) & 3)
    return out
def coded():
    out = {}
    for i in range(8):
        r = s.read(CODED + 4 * i, 4)
        if r[0] != 0xff: out[(r[0], r[1])] = (int.from_bytes(r[2:4], 'big') >> 4) & 0x1f
    return out
def bfs(a, b, ok):
    prev = {a: None}; q = collections.deque([a])
    while q:
        c = q.popleft()
        if c == b: break
        for dx, dy in VEC:
            n = (c[0] + dx, c[1] + dy)
            if 0 <= n[0] < 64 and 0 <= n[1] < 32 and n not in prev and (n == b or ok(*n)):
                prev[n] = c; q.append(n)
    if b not in prev: return None
    path = []; c = b
    while c: path.append(c); c = prev[c]
    return path[::-1]
OPEN = lambda x, y: tile(x, y) > 0x1a and tile(x, y) != 0x26 and not (0x40 <= tile(x, y) < 0x60 and not tile(x, y) & 0x10)
def log(*a): print(*a, flush=True)
def open_lock(L, back):
    wx, wy = L['W']; side = tile(wx, wy) & 3
    P = (wx - VEC[side][0], wy - VEC[side][1])
    log(f'  lock {L["i"]} key kind {L["key"]} door kind {L["door"]} code {L["code"]:#x}: panel W {L["W"]} side {side}, stand at {P}')
    path = bfs(pos(), P, OPEN)
    if path is None: raise SystemExit(f'no open path to panel front {P}: {st()}')
    walk(path, doors=False); face(side)
    click(100, 110)                                       # the cover
    k = L['key']; bits = [b for b in range(16) if L['code'] >> b & 1]
    if k == 0: pts = {0: (103, 110)}
    elif k == 1: pts = {b: (94 + 10 * b, 110) for b in range(3)}
    elif k == 2: pts = {b: (92 + 8 * (b & 3), 106 + 10 * (b >> 2)) for b in range(8)}
    else:
        table = s.read(0x12c12, 25)
        pts = {t - 1: (92 + 5 * (i % 5), 100 + 5 * (i // 5)) for i, t in enumerate(table) if t}
    for b in bits: click(*pts[b])
    rec = s.read(LOCKS + 10 * L['i'], 10)
    log(f'  panel state word {int.from_bytes(rec[4:6], "big"):#x} byte8 {rec[8]:#x}; door tile now {tile(rec[6], rec[7]):#x}')
    s('step', n=300000)
    path = bfs(pos(), back, OPEN)
    if path is None: raise SystemExit(f'no path back to {back}: {st()}')
    walk(path, doors=False)
def corners(code):
    b = s.read(0xe358 + code, 1)[0]
    seq = [(b >> 2) & 3, (b >> 4) & 3, (b >> 6) & 3]
    seq.append(({0, 1, 2, 3} - set(seq)).pop())
    return seq
CXY = {0: (71, 80), 1: (135, 80), 2: (71, 145), 3: (135, 145)}
def handle(n):
    t = tile(*n); L = locks().get(n); C = coded().get(n)
    if L is not None and not (t == 0x20 or (0x40 <= t < 0x60 and t & 0x10)):
        here = pos(); open_lock(L, here); face(direction(here, n)); return 'lock'
    if C is not None and 0x40 <= t < 0x60 and t & 7 == 4:
        seq = corners(C); log(f'  coded door {n} code {C}: corners {seq}')
        for c in seq: click(*CXY[c])
        s('step', n=300000); return 'coded'
    if 0x40 <= t < 0x60 or t == 0x1b:
        click(105, 110); s('step', n=300000); return 'door'
    return None
def direction(a, b):
    return VEC.index((b[0] - a[0], b[1] - a[1]))
def walk(path, doors=True):
    for n in path[1:]:
        c = pos()
        if c == n: continue
        face(direction(c, n))
        for attempt in range(4):
            key(0x68)
            if pos() == n: break
            if w16(14800): raise SystemExit(f'end screen {w16(14800)}: {st()}')
            how = handle(n) if doors else None
            log(f'  blocked at {c} -> {n} tile {tile(*n):#x}: {how}')
            if how is None and attempt: raise SystemExit(f'stuck at {c} -> {n}: {st()}')
        else: raise SystemExit(f'stuck after 4 tries at {c} -> {n}: {st()}')
        log(f'{n} tile {tile(*n):#x} {st()}')
leg = sys.argv[3]
log('start', st())
try:
    if leg == 'goto':
        b = tuple(int(v) for v in sys.argv[4].split(','))
        path = bfs(pos(), b, lambda x, y: tile(x, y) > 0x1a)
        if path is None: raise SystemExit('no path')
        walk(path)
    elif leg == 'at':                                     # LABELLED POKE: party cell and facing (x,y,f)
        x, y, f = (int(v) for v in sys.argv[4].split(','))
        s('poke', addr=A6 + 26, width=2, value=x); s('poke', addr=A6 + 28, width=2, value=y)
        s('poke', addr=A6 + 30, width=2, value=f); s('step', n=600000)
    elif leg == 'corners':                                # the coded door ahead, by its listed code
        n = tuple(int(v) for v in sys.argv[4].split(',')); C = coded()[n]; seq = corners(C)
        log(f'coded door {n} tile {tile(*n):#x} code {C}: corners {seq}')
        for c in seq: click(*CXY[c])
        s('step', n=600000); log(f'door tile now {tile(*n):#x}')
    elif leg == 'lift':
        click(202 if sys.argv[4] == 'up' else 251, 112, settle=3_000_000)
    elif leg == 'route':
        c = tuple(int(v) for v in sys.argv[4].split(',')); chain = [c]
        while c != pos():
            dd = s.read(P2 + c[1] * 64 + c[0], 1)[0] & 7
            if dd > 3: raise SystemExit(f'chain hits a lift at {c} before the party')
            c = (c[0] + VEC[dd][0], c[1] + VEC[dd][1]); chain.append(c)
            if len(chain) > 2000: raise SystemExit('chain does not reach the party')
        walk(chain[::-1])
    elif leg == 'wait':
        for i in range(int(sys.argv[4])):
            s('step', n=1_000_000); g = s.read(0x1c782, 8)
            log(f'+{i + 1}M Trill ({g[0]},{g[1]}) flags {g[4:6].hex()}', st())
            if w16(14800) or w16(13564) != 3: break
finally:
    log('end', st())
    s('save', path=sp(sys.argv[2]))
    s('render', path=sp(sys.argv[2]).replace('.snap', '.png'))
    s.close()
