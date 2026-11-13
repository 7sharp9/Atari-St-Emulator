"""From the emulator's own capture of base (D0=13, D2=0) (capture_final.py's f_0_0.bin 'ret' state, the returned
output), read: the lock list 13720, the object list 13724 records at given cells, the tile layer and plane 2 around
the Phoopel lock, and compare with chain_run.generate. Then flood-fill the emulator's tile layer from the entrance."""
import sys
import os as _os
_M = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '../../../..'))  # M68000/
from collections import deque
sys.path.insert(0, _M + '/reversing/captive/py/mapgen/full')
import chain_run as CR
import os
cap = os.path.join(CR.DATA, 'final', 'f_0_0.bin')
rec = next(r for r in CR.records(cap) if r['d0'] == 13 and r['d2'] == 0)
m, f = rec['ret']
m, f = bytearray(m), bytearray(f)
gm, gf, regs = CR.generate(13, 0)
print('chain == emulator for D0=13 D2=0:', gm == m and gf == f)
w = lambda b, o: (b[o] << 8) | b[o + 1]
P = lambda slot: int.from_bytes(m[slot:slot + 4], 'big') - CR.FED
n = w(m, 13270)
q = P(13720)
print('locks', n)
for i in range(n):
    e = f[q + 10 * i:q + 10 * i + 10]
    if (e[6], e[7]) == (7, 9):
        print(f' lock {i}: W ({e[0]},{e[1]}) code {w(e,2)} D ({e[6]},{e[7]}) kinds byte ${e[8]:02x} (key kind {e[8]&3}, door kind {(e[8]>>2)&3}, $10 {bool(e[8]&0x10)}) then ${e[9]:02x}')
# object list: header (size, free), records (x, y, size, items...)
o = P(13724)
size, free = w(f, o), w(f, o + 2)
p = o + 8
print(f'object list header size ${size:x} free ${free:x}')
cells = {}
while p < o + size:
    x, y, sz = f[p], f[p + 1], w(f, p + 2) if False else f[p + 2]
    if x == 0x88 or sz == 0:
        break
    items = [f[p + 4 + 4 * k:p + 8 + 4 * k].hex() for k in range((sz - 4) // 4)] if sz >= 4 else []
    cells[(x, y)] = items
    p += sz
print('object record at (7,9):', cells.get((7, 9)))
print('records parsed', len(cells))
# tile layer: 13684 pointer -> layer in f (federation block + outa)
t = P(13684)
tile = lambda x, y: f[t + 64 * y + x]
pl2 = P(13688)
print('tile layer around (7,9), rows 5..14, cols 2..12 (hex, & $7f):')
for y in range(5, 15):
    print(f'  y={y:2d} ' + ' '.join(f'{tile(x,y)&0x7f:02x}' for x in range(2, 13)))
ent = w(m, 32); ent = (ent % 64, ent // 64)
print('entrance', ent, 'tile', hex(tile(*ent)))
print('object list raw head:', f[o:o + 48].hex())
# find every 4-byte item 5d xx 85 20 (type $5d word 34080) anywhere in the list
needle = (34080).to_bytes(2, 'big')
for k in range(o, o + size):
    if f[k + 1] == 0x5d and f[k + 2:k + 4] == needle:
        print(f'item $5d word 34080 at list offset {k - o}: bytes {f[k:k+4].hex()} ; preceding 8 bytes {f[k-8:k].hex()}')
