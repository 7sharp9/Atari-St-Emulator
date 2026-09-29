"""Walk right with real input and log world x and the feet-cell categories, to read what a $25000 category does.

    uv run python <this dir>/walk_test.py <snap> [hold_steps] [sample_every] [n_samples]

Holds joystick right (kbd 08) for hold_steps (default 240,000), sampling every sample_every steps (default 10,000):
hero x ($1a574), camera ($227b6), y ($1a576), the feet cells $227e8/$227e9 (raw 8px ids; category via $25000 of
the snapshot), state $227f3. World x = x - $20 + camera. No pokes. Prints one line per sample.
"""
import os, subprocess, sys
from pathlib import Path
ROOT = Path(os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))))
sys.path.insert(0, str(ROOT / 'tools'))
from pm_export import ram_from_snap
DISK = 'scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st'
snap = sys.argv[1]
hold = int(sys.argv[2]) if len(sys.argv) > 2 else 240000
every = int(sys.argv[3]) if len(sys.argv) > 3 else 10000
n = int(sys.argv[4]) if len(sys.argv) > 4 else hold // every
cls = ram_from_snap(Path(snap))[0x25000:0x25100]
L = ['kbd ff', 's 30', 'kbd 08']
for i in range(n):
    L += [f's {every}', 'm 1a574 4', 'm 227b6 2', 'm 227e8 2', 'm 227f3 1']
L += ['kbd ff', 'kbd 00', 'quit']
p = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl', '--disk-a', DISK],
                   input='\n'.join(L) + '\n', capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE='1'))
rows = [l.split() for l in (p.stdout + p.stderr).splitlines() if l and all(len(t) == 2 and all(c in '0123456789abcdef' for c in t) for t in l.split())]
prev = None
for i in range(n):
    xy, cam, cells, st = rows[4 * i:4 * i + 4]
    x, y = int(xy[0] + xy[1], 16), int(xy[2] + xy[3], 16)
    c = int(cam[0] + cam[1], 16)
    wx = x - 32 + c
    e8, e9 = int(cells[0], 16), int(cells[1], 16)
    print(f'{(i + 1) * every:7d} steps: world x {wx:5d} (d {0 if prev is None else wx - prev:+d})  y {y:3d}  feet cells {e8:3d}/{e9:3d} = cat {cls[e8]}/{cls[e9]}  state {int(st[0], 16)}')
    prev = wx
