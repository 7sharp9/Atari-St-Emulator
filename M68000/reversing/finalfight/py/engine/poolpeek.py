#!/usr/bin/env python3
"""poolpeek.py <ram.bin> : print the live records of pools 2, 4, 6, 8, a, 12, 14 of a work RAM dump ($ff0000-$ffffff) plus stage/area/camera/player."""
import sys
ram = open(sys.argv[1], 'rb').read()
def r(a, n=1): return int.from_bytes(ram[a - 0xff0000:a - 0xff0000 + n], 'big')
print('stage %d area %d pos193 %d 290=%d 297=%d TIME %02x cam %04x,%04x P1 x %04x y %04x hp %04x' % (r(0xff80be), r(0xff80bf), r(0xff80c1), r(0xff8122), r(0xff8129), r(0xff80af), r(0xff8412, 2), r(0xff8416, 2), r(0xff856e, 2), r(0xff8572, 2), r(0xff8580, 2)))
for name, base, n, stride in (('2', 0xff86e8, 13, 0xc0), ('4', 0xff9528, 8, 0xc0), ('6', 0xff90a8, 6, 0xc0), ('8', 0xff9b28, 30, 0xc0), ('a', 0xffb2e8, 16, 0xc0), ('12', 0xffbee8, 10, 0xc0)):
    for i in range(n):
        a = base + stride * i
        if r(a):
            print('pool %-2s #%2d %06x b0=%02x st=%02x/%02x kind=%02x c20=%02x c21=%02x x=%04x y=%04x hp=%04x/%04x' % (name, i, a, r(a), r(a + 2), r(a + 3), r(a + 19), r(a + 20), r(a + 21), r(a + 6, 2), r(a + 10, 2), r(a + 24, 2), r(a + 28, 2)))
