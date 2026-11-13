"""[reversing/captive/py/phoopel/panel2/items.py; run from M68000 as `uv run python -I reversing/captive/py/phoopel/panel2/items.py <args>`; output under scratchpad/captive/phoopel/panel2/]
List the object-list records (x, y, size, 4-byte items: flags, type, word) of a snapshot: object list = at $1bf3a
(mapgen.md 'The object list'). usage: items.py <snap> [type_hex]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
snap = sys.argv[1]; want = int(sys.argv[2], 16) if len(sys.argv) > 2 else None
s = StServer(R); s('load', snapshot=snap)
p = 0x1bf3a   # mapgen.md output-region table: object list
hdr = s.read(p, 4); print('list at', hex(p), 'header', hdr.hex())
b = s.read(p + 4, 0x800)
i = 0; tile = lambda x, y: s.read(TILES + y*64 + x, 1)[0]
n = 0
while i + 4 <= len(b):
    x, y, size = b[i], b[i+1], int.from_bytes(b[i+2:i+4], 'big')
    if size < 8 or size > 0x40 or x > 63 or y > 31: break
    its = [(b[i+4+4*k], int.from_bytes(b[i+5+4*k:i+7+4*k], 'big'), b[i+7+4*k]) for k in range((size - 4) // 4)]   # type, word, flags
    n += 1
    if want is None or any(t == want for t, _, _ in its):
        print(f'({x},{y}) tile ${tile(x,y):02x} size {size}:', ' '.join(f'type ${t:02x} word ${w:04x}({w}) flags ${f:02x}' for t, w, f in its))
    i += size
print('records', n)
s.close()
