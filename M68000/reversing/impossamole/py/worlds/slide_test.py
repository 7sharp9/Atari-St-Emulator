"""Ice (category 7) vs ordinary ground (category 4): does the hero keep sliding after the stick is released?

    uv run python <this dir>/slide_test.py <snap> <camera hex> [<hero x dec>]

STAGING IS POKED: camera $227b6 (hero world x = x - $20 + camera) so the hero stands on the chosen part of the
map; hero y, state and facing stay as in the snapshot. Then: hold right (kbd 08) for 60,000 steps (2 polls), release,
and print hero x ($1a574) and the two feet-cell ids ($227e8/9) every 5,000 steps for 100,000 steps. Sliding =
x keeps increasing with no key held.
"""
import os, subprocess, sys
from pathlib import Path
ROOT = Path(os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))))
sys.path.insert(0, str(ROOT / 'tools'))
from pm_export import ram_from_snap
DISK = 'scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st'
snap, cam = sys.argv[1], int(sys.argv[2], 16)
r = ram_from_snap(Path(snap))
L = ['w 227b6 %04x%04x' % (cam, int.from_bytes(r[0x227b8:0x227ba], 'big')), 's 20000', 'm 1a574 4', 'm 227e8 2', 'kbd ff', 's 30', 'kbd 08', 's 60000', 'm 1a574 2', 'kbd ff', 'kbd 00']
for i in range(int(os.environ.get("SLIDE_SAMPLES", "20"))):
    L += ['s 5000', 'm 1a574 2']
L += ['m 227e8 2', 'm 227f3 1', 'quit']
p = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl', '--disk-a', DISK],
                   input='\n'.join(L) + '\n', capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE='1'))
rows = [l.split() for l in (p.stdout + p.stderr).splitlines() if l and all(len(t) == 2 and all(c in '0123456789abcdef' for c in t) for t in l.split())]
print('raw m outputs:', [' '.join(x) for x in rows])
xs = [int(x[0] + x[1], 16) for x in rows if len(x) == 2][2:]
print('hero x after release, every 5000 steps:', xs)
