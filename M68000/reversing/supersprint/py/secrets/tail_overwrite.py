"""tail_overwrite.py - is the SUPER1.DAT tail (file 0x2e60..0x4280 at $61436+) still intact in RAM at cold-boot step N?  Reports the
fraction of tail bytes equal to the file, every 2M steps, from the 2.72M boot snapshot."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh import *
d = open(os.path.join(sscfg.FILES, 'SUPER1.DAT'), 'rb').read()
lo, hi = 0x2e60, 0x4280
r = R(os.path.join(AGENT, 'snap', 'boot_2_72M.snap'))
for k in range(0, 22):
    cur = r.mem(0x61436 + lo, hi - lo)
    same = sum(1 for i in range(hi - lo) if cur[i] == d[lo + i])
    print('step %5.2fM: %5d / %d bytes still equal to file' % (2.72 + 2 * k, same, hi - lo), flush=True)
    r.cmd('s 2000000')
r.close()
