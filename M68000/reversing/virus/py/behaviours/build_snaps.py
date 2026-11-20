"""Build the start snapshots the behaviours gate needs, in ONE REPL pass over game 50 of the 100-game chain
(chain/long100/starts/main_g050.snap, unpoked; py/chain/chain.py makes it), about 1.07 billion steps (4-5 minutes).

    python3 build_snaps.py <out dir>

At each mark the run goes on to the next arrival at $255d4 (`bp 255d4`) and writes a snapshot there (a snapshot at an arbitrary PC, for
example inside the ROM wait loop, makes stserver's run_to_tick time out):
  p135 p255 p415 p495   about 135M, 255M, 415M, 495M steps: shortly before the provoking scans (`$20206`) of game 50
  w5                    about 995M: the start of wave index 5, the mothership waiting as record 18 of 19 (life $1e)
  c1065                 about 1065M: wave 5 with chasers hatched and a two-hit pursuer fighting
The marks are step counts after the previous snapshot's arrival, so the arrival offsets are deterministic for a given build.
Writes only <out dir>/<name>.snap (and the .prov.json sidecars the emulator writes)."""
import os, subprocess, sys
import bh
out = os.path.abspath(sys.argv[1]); os.makedirs(out, exist_ok=True)
MARKS = [('p135', 135), ('p255', 255), ('p415', 415), ('p495', 495), ('w5', 995), ('c1065', 1065)]
lines = []; last = 0
for name, m in MARKS:
    lines += [f's {(m - last) * 1_000_000}', 'bp 255d4 40000000', f'snap {out}/{name}.snap']
    last = m
lines.append('q')
snap = os.path.join(bh.STARTS, 'main_g050.snap')
r = subprocess.run(['dotnet', 'exec', os.path.join(bh.ROOT, 'bin/Debug/net8.0/M68000.dll'), 'resume', snap, 'repl'],
                   input='\n'.join(lines) + '\n', capture_output=True, text=True, cwd=bh.ROOT, env=dict(os.environ, ATARI_NOTRACE='1'))
w = [l for l in r.stdout.splitlines() if l.startswith('Snapshot written')]
print('\n'.join(w))
if len(w) != len(MARKS) or r.returncode:
    sys.exit('snapshot build failed: ' + r.stdout[-500:] + r.stderr[-500:])
