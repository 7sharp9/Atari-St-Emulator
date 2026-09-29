"""Stand the hero (no input) on a chosen map cell and log where the floor carries it.

    uv run python <this dir>/conveyor_test.py <snap> <world x dec> <hero y dec> [n_samples] [every]

STAGING IS POKED: camera $227b6 and $227b8 (limit) = world x + $20 - 144, hero x = 144, hero y = <hero y> (a few px
above the floor), state $227f3 = 3 (falling; it lands and settles to 0). No key is sent. Samples hero world x
(x - $20 + camera), y, feet cells $227e8/9 with their $25000 categories and state every `every` steps (default 10,000).
"""
import os, subprocess, sys
from pathlib import Path
ROOT = Path(os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))))
sys.path.insert(0, str(ROOT / 'tools'))
from pm_export import ram_from_snap
DISK = 'scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st'
snap, wx, hy = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
n = int(sys.argv[4]) if len(sys.argv) > 4 else 16
every = int(sys.argv[5]) if len(sys.argv) > 5 else 10000
r = ram_from_snap(Path(snap))
cls = r[0x25000:0x25100]
cam = wx + 32 - 144
b = bytes(r[0x227f0:0x227f4])
L = ['w 227b6 %04x%04x' % (cam, cam), 'w 1a574 %04x%04x' % (144, hy), 'w 227f0 %02x%02x%02x03' % (b[0], b[1], b[2])]
for i in range(n):
    L += [f's {every}', 'm 1a574 4', 'm 227b6 2', 'm 227e8 2', 'm 227f3 1']
L += ['quit']
p = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl', '--disk-a', DISK],
                   input='\n'.join(L) + '\n', capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE='1'))
rows = [l.split() for l in (p.stdout + p.stderr).splitlines() if l and all(len(t) == 2 and all(c in '0123456789abcdef' for c in t) for t in l.split())]
prev = None
for i in range(n):
    xy, c, cells, st = rows[4 * i:4 * i + 4]
    x, y = int(xy[0] + xy[1], 16), int(xy[2] + xy[3], 16)
    w = x - 32 + int(c[0] + c[1], 16)
    e8, e9 = int(cells[0], 16), int(cells[1], 16)
    print(f'{(i + 1) * every:7d}: world x {w:5d} (d {0 if prev is None else w - prev:+d}) y {y:3d} feet cat {cls[e8]}/{cls[e9]} state {int(st[0], 16)}')
    prev = w
