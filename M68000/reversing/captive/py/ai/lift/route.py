"""Lift-route survey from a snapshot: route.py <snap> [tx,ty ...]
Prints the block floor table 9206(A6) (4x4 blocks of 16x8), the lift tiles ($30-$34) with plane-2 bytes and block floor,
and a BFS path over open cells (tile > $1a) from the party to each target (default: every lift tile)."""
import os, sys, collections
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
    d = os.path.dirname(d)
sys.path.insert(0, os.path.join(d, 'reversing', 'captive', 'py', 'ai')); from cap import *  # noqa
from gfxview import load_ram
ram, base = load_ram(snappath(sys.argv[1]))
rd = lambda a, n: ram[a - base:a - base + n]
g = rd(A6 + 9242, 2048); p = rd(A6 + 11322, 2048)
w = lambda o: int.from_bytes(rd(A6 + o, 2), 'big', signed=True)
floors = rd(A6 + 9206, 16)
print('floors by block row:', [list(floors[i * 4:i * 4 + 4]) for i in range(4)])
print('lift offsets x', [w(9222 + 2 * k) for k in range(4)], 'y', [w(9230 + 2 * k) for k in range(4)])
print('party', w(26), w(28), 'face', w(30), 'floor word 15688', w(15688), '15552', w(15552))
fl = lambda x, y: floors[((y & 0x18) << 3 | x) >> 4] if 0 <= x < 64 and 0 <= y < 32 else None
lifts = [(i % 64, i // 64) for i in range(2048) if (g[i] & 0x7f) in (0x30, 0x31, 0x32, 0x33, 0x34)]
for x, y in lifts:
    i = y * 64 + x
    print(f'lift tile ({x},{y}) {g[i] & 0x7f:02x} p2 {p[i]:02x} lo {p[i] & 7} hi {(p[i] >> 3) & 7} floor {fl(x, y)}')
targets = [tuple(int(v) for v in a.split(',')) for a in sys.argv[2:]] or lifts
start = (w(26), w(28))
openc = lambda x, y: 0 <= x < 64 and 0 <= y < 32 and (g[y * 64 + x] & 0x7f) > 0x1a
prev = {start: None}; q = collections.deque([start])
while q:
    c = q.popleft()
    for dx, dy in ((0, -1), (-1, 0), (0, 1), (1, 0)):
        n = (c[0] + dx, c[1] + dy)
        if n not in prev and openc(*n) and fl(*n) == fl(*start):
            prev[n] = c; q.append(n)
for t in targets:
    if t not in prev:
        print('target', t, 'unreachable on the party floor'); continue
    path = [t]
    while prev[path[-1]]:
        path.append(prev[path[-1]])
    path.reverse()
    print('target', t, 'steps', len(path) - 1, ' '.join(f'({x},{y}){g[y * 64 + x] & 0x7f:02x}' for x, y in path))
