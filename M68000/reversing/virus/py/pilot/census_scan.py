"""Census of what the pilot's nearest-record scan ($2529a, result stored at $253a4) picks.

From a demo-start snapshot it stops at every $253a4 (the instruction after `bsr $2529a`: A0 = the chosen record) with `bp`,
and dumps the tick word $32a44, the record count $32a3e, the pool $31d54 (128 records of 20 bytes), the ship $270b0 and the
target queue $27134.  Prints/saves the raw log; census_report.py reads it.  One REPL process, unpoked.
Usage (from M68000/):  uv run python <this> <hits> <out.log> [snap] [stepcap]
"""
import os, subprocess, sys
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')): d = os.path.dirname(d)
hits, out = int(sys.argv[1]), sys.argv[2]
snap = sys.argv[3] if len(sys.argv) > 3 else 'scratchpad/virus/demo/S1b.snap'
cap = sys.argv[4] if len(sys.argv) > 4 else '3000000'
cmds = []
for _ in range(hits):
    cmds += ['bp 253a4 ' + cap, 'm 32a44 2', 'm 32a3e 2', 'm 270b0 12', 'm 27134 24', 'm 31d54 2560']
cmds += ['snap %s.end.snap' % os.path.splitext(out)[0], 'q']
p = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl'], input='\n'.join(cmds) + '\n',
                   capture_output=True, text=True, cwd=d, env=dict(os.environ, ATARI_NOTRACE='1'))
open(out, 'w').write(p.stdout + p.stderr)
print('rc', p.returncode, 'bp hits', p.stdout.count('--- breakpoint'), 'gave up', p.stdout.count('gave up'), 'REPL errors', (p.stdout + p.stderr).count('REPL error'))
