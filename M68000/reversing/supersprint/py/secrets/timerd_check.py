import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
r = R(sscfg.SNAP_RACE)
a = Acc(r, [0x13254, 0x12b32, 0x12a56, 0x12a8c, 0x12c10, 0x12dec])
a.run(3000000); a.show('race 3M')
print('Timer D vector $110 = %x, MFP: TCDCR $fffa1d=%x TDDR $fffa25=%x IERB $fffa09=%x IMRB $fffa15=%x' % (r.w32(0x110), r.w8(0xfffa1d), r.w8(0xfffa25), r.w8(0xfffa09), r.w8(0xfffa15)))
r.close()
