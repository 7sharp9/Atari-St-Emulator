"""Poke the boss-dead flag $22803 := $ff in a boss-room snapshot and watch the level-complete chain.

    uv run python <this dir>/end_level_poke.py <in.snap> <out.snap> [--bb79 HEX] [--steps N]

STAGING IS POKED: $22803 = $ff (what the boss's death routine writes: $016958 Ice Land, $0176a6 Bermuda Triangle,
$01602e Amazon) and optionally the locked-icon mask $bb79. Then runs N steps (default 14,000,000) printing hits on
$fbb4 (the 125-frame counter), $b0b2 (level-complete), $b0ca (world 5 goes to $183c0, else $17c9c world-select),
$183c0 (the ending screen) and $17c9c, and $bb79 and PC at the end. Requires the snapshot to be in the boss room.
"""
import os, subprocess, sys
from pathlib import Path
ROOT = Path(os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))))
sys.path.insert(0, str(ROOT / 'tools'))
from pm_export import ram_from_snap
DISK = 'scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st'
a = sys.argv[1:]
src, dst = a[0], a[1]
steps = int(a[a.index('--steps') + 1]) if '--steps' in a else 14000000
r = ram_from_snap(Path(src))
L = ['w 22800 %02x%02x%02x%02x' % (r[0x22800], r[0x22801], r[0x22802], 0xff)]
if '--bb79' in a:
    L.append('w bb78 %02x%02x%02x%02x' % (r[0xbb78], int(a[a.index('--bb79') + 1], 16), r[0xbb7a], r[0xbb7b]))
L += ['m bb76 4', f'hits {steps} fbb4 b0b2 b0ca 183c0 17c9c', 'r', 'm bb76 4', f'snap {dst}', 'quit']
rp = Path(ROOT, dst).with_suffix('.repl'); rp.write_text('\n'.join(L) + '\n')
p = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', src, 'repl', '--disk-a', DISK],
                   stdin=open(rp), capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE='1'))
print('\n'.join(l for l in (p.stdout + p.stderr).splitlines() if not l.startswith('enqueued')))
