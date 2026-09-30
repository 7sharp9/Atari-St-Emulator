"""Depack every LSD! file with py/lsd.py and compare with the RAM the game holds (Amazon gameplay snapshot)."""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
from lsd import depack
r = ram()
tests = [('CHARS11.DAT', 0x24000), ('SPRTS22.DAT', 0x3b600), ('SPRTS33.DAT', 0x42e00),
         ('JUNGLE22.DAT', 0x40600), ('JUNGLE33.DAT', 0x4c400), ('MDATA3.DCH', 0x53000)]
for name, addr in tests:
    o, a1, nl, nm = depack(rd(name))
    live = r[addr:addr + len(o)]
    m = sum(1 for x, y in zip(o, live) if x == y)
    print(f'{name:14s} -> ${addr:05x} unpacked {len(o):6d} match {m}/{len(o)} ({100*m/len(o):.2f}%) final a1={a1}')
