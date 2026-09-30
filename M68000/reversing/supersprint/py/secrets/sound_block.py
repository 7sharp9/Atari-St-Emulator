import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh import *
r = R(sscfg.SNAP_ATTRACT)
base = r.g32(-54)
print('sound base', hex(base))
blk = r.mem(base, 9000)
for off in (0, 8, 14, 28, 74, 88, 166, 180, 194, 208, 222, 236, 242, 272, 302, 316, 322, 336, 906, 2580, 3398, 4488, 5302, 5916, 6794, 7780):
    print('%5d' % off, blk[off:off+32].hex(' '))
# is the dump the same as in SUPER.DAT?  find it
d = open(os.path.join(sscfg.FILES, 'SUPER.DAT'), 'rb').read()
i = d.find(blk[:64]); print('block in SUPER.DAT at', hex(i) if i >= 0 else None)
open(os.path.join(AGENT, 'sound_block.bin'), 'wb').write(blk)
r.close()
