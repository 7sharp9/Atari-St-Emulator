import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh import *
r = R(sscfg.SNAP_ATTRACT)
print('resvalid $426 = %08x   resvector $42a = %08x' % (r.w32(0x426), r.w32(0x42a)))
print('IKBD vector $118 = %08x   VBL $70 = %08x  TimerB $120 = %08x  TimerC $114=%08x' % (r.w32(0x118), r.w32(0x70), r.w32(0x120), r.w32(0x114)))
print('hz_200 $4ba', r.w32(0x4ba))
print('$10544 hdr-pending byte', r.w8(0x10544), ' $10546 saved A4 = %08x' % r.w32(0x10546))
r.close()
