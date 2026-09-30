"""watch_super1.py - who first overwrites the SUPER1.DAT load buffer tail ($61436+$2f00..) after it is loaded (cold boot 2.72M)?"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh import *
r = R(os.path.join(AGENT, 'snap', 'boot_2_72M.snap'))
print('first bytes of tail now', r.mem(0x61436 + 0x3a9a, 8).hex(), ' (expect file bytes 12 28 14 28..)')
r.cmd('watch 64ed0 4')
for k in range(200):
    r.cmd('s 500000')
    e = r.err()
    if e.strip():
        print('after %d steps:' % (500000 * (k + 1)), e.strip().splitlines()[:5])
        break
r.close()
