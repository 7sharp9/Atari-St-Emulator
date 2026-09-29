"""Print the level-end / world-select state bytes of one or more snapshots side by side.

    uv run python reversing/impossamole/py/level_end/state_dump.py a.snap b.snap ...

Fields (addresses from README "Rooms"/"Boss" and the $f0ee/$17c9c disassembly): $bb6e score long,
$bb72 weapon, $bb73 (weapon counter), $bb74/$bb75 health/max, $bb76 world index (1 Klondike .. 5 Bermuda),
$bb77, $bb78, $bb79 world mask, $bb7a-$bb7d, $22800 (victory counter), $22803 boss flag, $22804 125-frame
counter, $227f3, $1a338 (cursor icon 78(A0) of slot 0), slot 0 word +0/+2/+4, hero base $1a572 x/y.
"""
import os, struct, sys
from pathlib import Path
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))
sys.path.insert(0, ROOT + '/tools')
from pm_export import ram_from_snap

rams = [(p, ram_from_snap(Path(p))) for p in sys.argv[1:]]
b = lambda r, a: r[a]
w = lambda r, a: struct.unpack_from('>H', r, a)[0]
l = lambda r, a: struct.unpack_from('>I', r, a)[0]
rows = [
    ('score bb6e (long)', lambda r: f'{l(r, 0xbb6e):08x}'),
    ('weapon bb72', lambda r: f'{b(r, 0xbb72):02x}'),
    ('bb73', lambda r: f'{b(r, 0xbb73):02x}'),
    ('health bb74', lambda r: f'{b(r, 0xbb74):02x}'),
    ('max bb75', lambda r: f'{b(r, 0xbb75):02x}'),
    ('world bb76', lambda r: f'{b(r, 0xbb76):02x}'),
    ('bb77', lambda r: f'{b(r, 0xbb77):02x}'),
    ('bb78', lambda r: f'{b(r, 0xbb78):02x}'),
    ('mask bb79', lambda r: f'{b(r, 0xbb79):02x}'),
    ('bb7a', lambda r: f'{b(r, 0xbb7a):02x}'),
    ('bb7b', lambda r: f'{b(r, 0xbb7b):02x}'),
    ('bb7d', lambda r: f'{b(r, 0xbb7d):02x}'),
    ('22800', lambda r: f'{b(r, 0x22800):02x}'),
    ('boss 22803', lambda r: f'{b(r, 0x22803):02x}'),
    ('22804', lambda r: f'{b(r, 0x22804):02x}'),
    ('227f3', lambda r: f'{b(r, 0x227f3):02x}'),
    ('227f4', lambda r: f'{b(r, 0x227f4):02x}'),
    ('cursor 78(slot0) $1a338', lambda r: f'{b(r, 0x1a338):02x}'),
    ('slot0 type/x/y', lambda r: f'{w(r, 0x1a2ea):04x}/{w(r, 0x1a2ec):04x}/{w(r, 0x1a2ee):04x}'),
    ('hero $1a572 type/x/y', lambda r: f'{w(r, 0x1a572):04x}/{w(r, 0x1a574):04x}/{w(r, 0x1a576):04x}'),
    ('camera 227b6', lambda r: f'{w(r, 0x227b6):04x}'),
    ('227b4', lambda r: f'{w(r, 0x227b4):04x}'),
    ('1a2e4 screen ptr', lambda r: f'{l(r, 0x1a2e4):08x}'),
]
print(f'{"":26}' + ''.join(f'{Path(p).name[:22]:>24}' for p, _ in rams))
for name, f in rows:
    print(f'{name:26}' + ''.join(f'{f(r):>24}' for _, r in rams))
