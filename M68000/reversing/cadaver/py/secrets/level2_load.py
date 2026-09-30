"""Load the second level record (disk directory slot 1) of the one-disk Empire image in the live emulator.

The 'level start' verb at $010410 (its own assert string calls it SET ACTION) does: D0 = operand byte; if D0 > 9 fatal;
2524(A5) = D0 + 1 (level number byte); 2518(A5) = $ff; 2525(A5) = 1; bsr $00e53c; jmp $006890 (restart/load).
This script starts gameplay_empire.snap with PC = $010410 and A1 -> a zero byte (operand 0 => level byte 1), so
the game's own loader reads directory record 1 from sector 400, prompts 'PLACE LEVELS DISK ... PRESS A KEY', and after
a space keypress reads and expands the level's resources (4 calls of the LZHUF expander $0118ec, 5 of $00ba2e).
It writes level2_loaded.snap / level2_loaded.png.  Prints the hit census and 2524/2516(A5).

Run from M68000/:  uv run python reversing/cadaver/py/secrets/level2_load.py
Expected: $0118ec 4 hits, $00ba2e 5 hits, level byte 1, max health 200 (2516(A5)); the PNG shows a sandstone temple room.
"""
import os, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
OUT = os.path.join(os.path.abspath(os.path.join(here, '..', '..', '..', '..')), 'scratchpad/cadaver/secrets_out'); os.makedirs(OUT, exist_ok=True)
M68 = os.path.abspath(os.path.join(here, '..', '..', '..', '..')); REPO = os.path.dirname(M68)
DISK = os.path.join(REPO, 'Cadaver', 'Cadaver (1990)(Image Works)[cr Empire][one disk].st')
SNAP = os.path.join(M68, 'scratchpad/cadaver/gameplay_empire.snap')
out = os.path.join(here, 'level2_loaded.snap')
subprocess.run([sys.executable, os.path.join(here, 'patch_snap.py'), SNAP, os.path.join(here, 'level2_start.snap'), 'pc=10410', 'a1=80000'], check=True)
cmds = ['s 3000000', 'kbd 39', 's 60000', 'kbd b9', 'hits 24000000 118ec ba2e b5a8 b1e0 b3ba b44a', 'snap ' + out, 'q']
env = dict(os.environ, ATARI_NOTRACE='1')
p = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', os.path.join(here, 'level2_start.snap'), 'repl', '--disk-a', DISK],
                   input='\n'.join(cmds) + '\n', text=True, capture_output=True, cwd=M68, env=env)
print('\n'.join(l for l in p.stdout.splitlines() if l.startswith('  $')))
from ram import ram
r = ram(out); a5 = 0x18152
print('level byte 2524(A5) =', r[a5 + 2524], ' max health 2516(A5) =', int.from_bytes(r[a5 + 2516:a5 + 2518], 'big'))
subprocess.run(['uv', 'run', 'python', 'tools/snap_render.py', out, os.path.join(OUT, 'level2_loaded.png')], cwd=M68)
