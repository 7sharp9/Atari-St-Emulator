"""Boss descriptors, per-world boss type words and the five `$22803 := $ff` writers of a snapshot.

    uv run python reversing/impossamole/py/level_end/boss_writers.py <snap>

Reads: the per-world boss type word table at $10370 (5 words, index = $bb76-1, read by the kind-2 allocator
$1021a), the descriptor pointer table at $10474 (256 longs; descriptor byte 0 = allocator kind, kind 2 = boss,
descriptor +48 long = per-frame handler copied to 86(A0) by $1021a at $0102fe), and the enclosing routine of each
`move.b #$ff,$22803.l` (found by scanning the disassembly for the write and walking back to the last rts/jmp/bra
boundary is NOT done: it prints the handler start as the nearest lower descriptor handler address).
"""
import os, struct, sys
from pathlib import Path
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))
sys.path.insert(0, ROOT + '/tools')
from pm_export import ram_from_snap
ram = ram_from_snap(Path(sys.argv[1]))
w = lambda a: struct.unpack_from('>H', ram, a)[0]
l = lambda a: struct.unpack_from('>I', ram, a)[0]
print('boss type words $10370 (world index 1..5):', [f'{w(0x10370 + 2 * i):04x}' for i in range(5)])
seen = {}
for t in range(256):
    d = l(0x10474 + 4 * t)
    if d < 0x24000 and ram[d] == 2:
        print(f'type {t:3} descriptor ${d:05x} kind 2 hp={ram[d+5]} dmg={ram[d+6]} +8 word={w(d+8):04x} handler(+48)=${l(d+48):06x} anim(+28)=${l(d+28):06x}')
        seen[t] = d
# raw search for the writer instructions: 13fc 00ff 0002 2803 (move.b #$ff,$22803.l)
pat = bytes.fromhex('13fc00ff00022803')
a = 0
while True:
    a = ram.find(pat, a)
    if a < 0:
        break
    print(f'writer $ff at ${a:06x}')
    a += 2
