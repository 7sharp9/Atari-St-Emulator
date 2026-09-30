import sys; sys.path.insert(0,'.')
from tkcommon import *
r = Repl(sscfg.SNAP_SELECT)
LO, HI = 0x1bfd0, 0x1f100
def dump(): return r.mem(LO, HI-LO)
a = dump()
for pkt in ('ff 08','ff 04','ff 02','ff 01'):
    r.cmd('kbd '+pkt); r.cmd('s 60000'); r.cmd('kbd ff 00'); r.cmd('s 400000')
    b = dump()
    d = [(LO+i, a[i], b[i]) for i in range(len(a)) if a[i]!=b[i]]
    print(pkt, len(d), [(hex(x),hex(y),hex(z)) for x,y,z in d[:40]])
    a = b
r.close()
