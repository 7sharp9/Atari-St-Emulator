"""Tiny memory dump helper: uv run python rd.py <snap> <hexaddr> <len> [w|l]"""
import os, sys, struct
from pathlib import Path
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))
sys.path.insert(0, os.path.join(ROOT, 'reversing/impossamole/py'))
from tiles import ram_from_snap
snap, a, n = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3])
ram = ram_from_snap(Path(snap))
mode = sys.argv[4] if len(sys.argv) > 4 else 'b'
step = {'b': 1, 'w': 2, 'l': 4}[mode]
for o in range(0, n, 16):
    row = ram[a + o:a + min(o + 16, n)]
    print(f'{a+o:06x}: ' + ' '.join(row[i:i + step].hex() for i in range(0, len(row), step)))
