"""Capture the corpus for the pilot-tick gate (reversing/virus/demo.md, "The pilot").

From a demo-start snapshot (default scratchpad/virus/demo/S1b.snap, demo flag $62a5f = $ff) it stops at every entry of
$2538c (Input_Autopilot) with `bp`, dumps the state the routine reads (pilot words $270a2..$270af, ship $270b0..$270bb,
matrix $270d4, tick $32a44, record count $32a3e, countdown $62a60, the record pool $31d54..) and runs
`callcap 2538c` from that state (callcap restores the state afterwards, so the flight is unpoked).  One REPL process.
Usage (from M68000/):  uv run python <this> <ticks> <out.log> [snap]
"""
import os, subprocess, sys
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')): d = os.path.dirname(d)
ROOT = d
ticks, out = int(sys.argv[1]), sys.argv[2]
snap = sys.argv[3] if len(sys.argv) > 3 else 'scratchpad/virus/demo/S1b.snap'
POOL = 3292   # $31d54..$32a2f: the pool's extent in the data map ($32a2e is the next word)
cmds = []
for _ in range(ticks):
    cmds += ['bp 2538c 3000000', 'm 270a2 14', 'm 270b0 12', 'm 270d4 18', 'm 32a3e 2', 'm 32a44 2', 'm 62a60 1',
             'm 31d54 %d' % POOL, 'callcap 2538c 200000 -']
cmds.append('snap %s.end.snap' % os.path.splitext(out)[0])
cmds.append('q')
env = dict(os.environ, ATARI_NOTRACE='1')
p = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl'], input='\n'.join(cmds) + '\n',
                   capture_output=True, text=True, cwd=ROOT, env=env)
open(out, 'w').write(p.stdout + p.stderr)
print('rc', p.returncode, 'bytes', len(p.stdout), 'breakpoints', p.stdout.count('--- breakpoint'), 'callcaps', p.stdout.count('--- callcap'),
      'gave up', p.stdout.count('gave up'), 'REPL errors', (p.stdout + p.stderr).count('REPL error'))
