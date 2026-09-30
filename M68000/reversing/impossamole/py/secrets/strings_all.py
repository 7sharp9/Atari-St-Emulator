"""All printable strings (>= 5 chars) of every disk file, of the LSD!-depacked and Huffman-expanded payloads and of the resident game image."""
import sys, re
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
from lsd import depack
from huff import expand
import os
def strs(b, n=5):
    return [(m.start(), m.group().decode('latin1')) for m in re.finditer(rb'[\x20-\x7e]{%d,}' % n, b)]
out = open(WORK + '/data/strings_all.txt', 'w')
for f in sorted(os.listdir(EXTR)):
    if f.startswith('__') or f == 'DESKTOP.INF': continue
    b = rd(f)
    srcs = [(f, b)]
    if b[:4] == b'LSD!':
        o, *_ = depack(b); srcs.append((f + ' [LSD!]', o))
        if f.startswith('MDATA') or f.startswith('PICTURES'):
            e, _ = expand(o); srcs.append((f + ' [LSD!+huff]', e))
    for name, data in srcs:
        for off, s in strs(data):
            out.write(f'{name}\t{off:#x}\t{s}\n')
r = ram()
for off, s in strs(r[0x2000:0x43000]):
    out.write(f'RESIDENT\t{off+0x2000:#x}\t{s}\n')
out.close()
