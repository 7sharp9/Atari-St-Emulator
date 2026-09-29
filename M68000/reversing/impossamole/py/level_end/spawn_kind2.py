"""List the kind-2 (boss) spawn record(s) and the type histogram of a snapshot's spawn list ($27200), tolerating
descriptor pointers outside RAM (spawn_list.py raises IndexError on the Klondike snapshot).

    uv run python reversing/impossamole/py/level_end/spawn_kind2.py <snap>
"""
import collections, os, struct, sys
from pathlib import Path
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))
sys.path.insert(0, ROOT + '/tools')
from pm_export import ram_from_snap
ram = ram_from_snap(Path(sys.argv[1]))
w = lambda a: struct.unpack_from('>H', ram, a)[0]
l = lambda a: struct.unpack_from('>I', ram, a)[0]
print('world $bb76 =', ram[0xbb76], ' boss type word $10370[world-1] =', f'{w(0x10370 + 2 * (ram[0xbb76] - 1)):04x}')
a = 0x27200
while ram[a:a + 4] == b'\0\0\0\0':
    a += 4
hist = collections.Counter(); n = 0; bad = 0
while w(a) != 0x7fff and a < 0x27200 + 0x2000:
    col, row, typ = w(a), ram[a + 2], ram[a + 3]
    d = l(0x10474 + 4 * typ)
    hist[typ] += 1; n += 1
    if d >= len(ram):
        bad += 1
    elif ram[d] == 2:
        print(f'kind-2 record: col {col} blk {col//4} y {row*8+8} type {typ} descriptor ${d:05x} handler ${l(d+48):06x} hp {ram[d+5]}')
    a += 4
print(f'{n} records, {bad} with a descriptor pointer outside RAM')
print('types (count):', ' '.join(f'{t}:{c}' for t, c in sorted(hist.items())))
