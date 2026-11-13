"""Map-tile and party changes between a view_tiles.py snapshot and the same state after keys.py stepped forward.
Usage: step_diff.py <before.snap> <after.snap>"""
import sys, pathlib
here = pathlib.Path(__file__).resolve()
root = next(p for p in here.parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(root / 'tools'))
from gfxview import load_ram
A6 = 0x1b5ce
def st(p):
    ram, b = load_ram(p)
    g = lambda a, n: bytes(ram[a - b:a - b + n])
    return g(A6 + 9242, 2048), [int.from_bytes(g(A6 + o, 2), 'big') for o in (26, 28, 30)], int.from_bytes(g(A6 + 15690, 2), 'big')
m0, p0, f0 = st(sys.argv[1]); m1, p1, f1 = st(sys.argv[2])
ch = [(i % 64, i // 64, m0[i], m1[i]) for i in range(2048) if (m0[i] & 0x7f) != (m1[i] & 0x7f)]
print('party', p0, '->', p1, '15690(A6)', f0, '->', f1, 'tile changes (bit 7 ignored):',
      ' '.join(f'({x},{y}) ${a:02x}->${b:02x}' for x, y, a, b in ch) or 'none')
