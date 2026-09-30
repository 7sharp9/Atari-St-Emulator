import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pl import *
r = Ram(sscfg.SNAP_RACE)
print('A4 =', hex(A4))
for name, off, n in [('-4118 dirX?', -4118, 16), ('-4150 dirY?', -4150, 16), ('x -3690', -3690, 4), ('y -3698', -3698, 4), ('head -3706', -3706, 4),
                     ('tgt -3714', -3714, 4), ('spd -3730', -3730, 4), ('cap -3874', -3874, 4), ('div -3882', -3882, 4), ('-3882..', -3882, 4)]:
    print(name, r.arr(off, n))
print('-4566 tbl (8 words per heading):')
for h in range(16):
    print(h, [r.s16(A4 - 4566 + h*8 + 2*i) for i in range(4)])
print('-4406 tbl (16 bytes per heading, 2 longs offs + 2 longs masks):')
for h in range(16):
    a = A4 - 4406 + h*16
    print(h, ['%08x' % r.u32(a + 4*i) for i in range(4)])
print('-4438 tbl', [hex(r.gu(-4438 + 2*i)) for i in range(16)])
print('ptr -1910', hex(r.gl(-1910)), ' -3682 addr', hex(A4 - 3682), ' -90', hex(r.gl(-90)), '-4944', hex(r.gl(-4944)))
