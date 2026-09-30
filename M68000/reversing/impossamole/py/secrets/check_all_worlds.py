"""LSD! + Huffman check for every world: depack the world's three files and compare with that world's gameplay snapshot.
MDATAn: LSD! -> Huffman expand -> RAM $25000..$31800 (51200 bytes).  *22.DAT -> $40600, *33.DAT -> $4c400; common files to $24000/$3b600/$42e00."""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
from lsd import depack
from huff import expand
A = ROOT + '/scratchpad/impossamole/agents/'
worlds = [('MINES', 1, A+'world12/klondike_gameplay.snap'), ('ORIENT', 2, A+'world12/orient_gameplay.snap'),
          ('JUNGLE', 3, GAME), ('ICELND', 4, A+'world34/snaps/ice_gameplay.snap'), ('BRMUDA', 5, A+'world34/snaps/bermuda_gameplay.snap')]
tot = totm = 0
for nm, w, snap in worlds:
    r = ram(snap)
    print('world', w, nm, 'bb76 =', r[0xbb76], snap.split('/agents/')[1])
    items = [(f'MDATA{w}.DCH', 0x25000, True), (f'{nm}22.DAT', 0x40600, False), (f'{nm}33.DAT', 0x4c400, False),
             ('CHARS11.DAT', 0x24000, False), ('SPRTS22.DAT', 0x3b600, False), ('SPRTS33.DAT', 0x42e00, False)]
    for f, addr, huf in items:
        o, a1, *_ = depack(rd(f))
        if huf: o, _ = expand(o)
        m = sum(1 for x, y in zip(o, r[addr:addr+len(o)]) if x == y)
        tot += len(o); totm += m
        print(f'   {f:14s} -> ${addr:05x} len {len(o):6d} match {m}/{len(o)}')
print('TOTAL', totm, '/', tot)
