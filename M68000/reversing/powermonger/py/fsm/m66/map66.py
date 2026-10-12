#!/usr/bin/env python3
"""map66.py <snap> [radius]: ASCII terrain around the records with prev $66 (half-cell samples, '~' = terrain byte 0 = water,
the $1648e veto). Overlays: L lead of the chase (word 28 == 0), 6 a man in mode $36, 8 in $38, 0 in $00/$0a, b afloat ($8c),
o other mode, S the target 48(A1). Rows are y, columns x, two samples per cell."""
import sys
from pathlib import Path
ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(ROOT / 'tools'))
import pm_fsm_ref as P
from disassemble import ram_from_snap
OBJ = 0x51b66
sn = sys.argv[1]; rad = int(sys.argv[2]) if len(sys.argv) > 2 else 6
m = P.Mem(ram_from_snap(sn))
men = []; tgt = None
for k in range(1, 512):
    b = OBJ + 50 * k
    if m.bu(b + 30) == 0x66:
        men.append((k, m.wu(b + 8), m.wu(b + 10), m.bu(b + 31), m.wu(b + 28)))
        tgt = OBJ + m.ws(b + 48)
if not men: print('no prev $66'); sys.exit()
tx, ty = m.wu(tgt + 8), m.wu(tgt + 10)
cx = sum(x for _, x, _, _, _ in men) // len(men) >> 8; cy = sum(y for _, _, y, _, _ in men) // len(men) >> 8
sym = {}
def put(x, y, c): sym[(x >> 7, y >> 7)] = c
for k, x, y, md, w28 in men:
    put(x, y, 'L' if w28 == 0 else {0x36: '6', 0x38: '8', 0: '0', 0xa: '0', 0x8c: 'b'}.get(md, 'o'))
put(tx, ty, 'S')
print(sn, 'target', hex(tgt), 'at', hex(tx), hex(ty), 'men', len(men), 'centre cell', cx, cy)
for hy in range((cy - rad) * 2, (cy + rad) * 2):
    row = ''
    for hx in range((cx - rad) * 2, (cx + rad) * 2):
        if (hx, hy) in sym: row += sym[(hx, hy)]
        else: row += '~' if P.terrain_sample(m, hx * 128 + 64, hy * 128 + 64) == 0 else '.'
    print(f'{hy // 2:3d} {row}')
for k, x, y, md, w28 in men: print(f'  slot {k} ({x:04x},{y:04x}) mode {md:02x} w28 {w28:04x}')
