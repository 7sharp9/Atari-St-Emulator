"""Snapshots at fixed step marks of a chain game, each at the next $255d4 arrival (as behaviours/build_snaps.py).
    uv run python reversing/virus/py/behaviours/build_marks.py <start snap> <out dir> <prefix> <step_M> <count>"""
import os, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import vcommon
snap, out, pre, every, n = sys.argv[1], os.path.abspath(sys.argv[2]), sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
lines = []
for i in range(1, n + 1):
    lines += [f's {every * 1_000_000}', 'bp 255d4 40000000', f'snap {out}/{pre}_{i * every}.snap']
lines.append('q')
r = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl'], input='\n'.join(lines) + '\n',
                   capture_output=True, text=True, cwd=vcommon.ROOT, env=dict(os.environ, ATARI_NOTRACE='1'))
w = [l for l in r.stdout.splitlines() if l.startswith('Snapshot written')]
print(len(w), 'of', n, r.returncode); print('\n'.join(w))
