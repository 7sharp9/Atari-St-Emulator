import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
from lsd import depack
from huff import expand
r = ram()
o, *_ = depack(rd('MDATA3.DCH'))
e, used = expand(o)
print('LSD unpacked', len(o), 'huffman N', len(e), 'stream bytes consumed', used)
live = r[0x25000:0x25000+len(e)]
m = sum(1 for a, b in zip(e, live) if a == b)
print('match vs RAM $25000..: %d/%d' % (m, len(e)))
# per region
regs = [('class table $25000', 0x25000, 0x27200), ('spawn list $27200', 0x27200, 0x27600), ('block map $27600', 0x27600, 0x29000),
        ('block defs $29000', 0x29000, 0x29800), ('tile bank $29800', 0x29800, 0x31800)]
for n, lo, hi in regs:
    mm = sum(1 for i in range(lo, hi) if e[i-0x25000] == r[i])
    print('  %-20s %d/%d' % (n, mm, hi-lo))
