"""Header table for every LSD! file on the disk: file size, U (unpacked), P (packed field), and whether the depacker ends exactly at dest 0 and source 8."""
import sys, struct, os
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
from lsd import depack
from huff import expand
print(f'{"file":14s} {"size":>6s} {"U":>6s} {"P":>6s} {"size-4-P":>8s} {"ratio":>6s}  huffman')
for f in sorted(os.listdir(EXTR)):
    b = rd(f)
    if b[:4] != b'LSD!': continue
    U, P = struct.unpack('>II', b[4:12])
    o, a1, nl, nm = depack(b)
    h = ''
    if f.startswith(('MDATA', 'PICTURES')):
        e, used = expand(o); h = f'-> {len(e)} bytes (header N={struct.unpack(">I", o[:4])[0]}), stream {used} of {len(o)}'
    print(f'{f:14s} {len(b):6d} {U:6d} {P:6d} {len(b)-4-P:8d} {len(b)/U:6.3f}  a1={a1} lit={nl} matches={nm} {h}')
