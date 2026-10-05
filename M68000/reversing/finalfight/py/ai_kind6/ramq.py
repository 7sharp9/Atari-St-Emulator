#!/usr/bin/env python3
"""Query a work-RAM dump: ramq.py <ram.bin> [addr:len ...] ; default prints camera, stage, script record, pool-2 records."""
import sys
d = open(sys.argv[1], 'rb').read()
B = 0xff0000
w = lambda a: int.from_bytes(d[a-B:a-B+2], 'big')
l = lambda a: int.from_bytes(d[a-B:a-B+4], 'big')
b = lambda a: d[a-B]
print('stage', b(0xff80be), b(0xff80bf), 'cam x %04x y %04x' % (w(0xff8412), w(0xff8416)), 'diff168', w(0xff80a8), 'TIME', hex(b(0xff80af)))
r = 0xffb1e8
print('script rec state', b(r+2), b(r+3), b(r+4), b(r+5), 'ptr %06x mode %d w12 %d w16 %d' % (l(r+6), w(r+10), w(r+12), w(r+16)))
print('free tag2 count', w(0xff8000+20240))
for i in range(13):
    a = 0xff86e8 + 0xc0*i
    if b(a):
        print('pool2 #%d @%06x kind %d +20 %d +21 %d st %d %d %d %d x %d y %d hp %d' % (i, a, b(a+19), b(a+20), b(a+21), b(a+2), b(a+3), b(a+4), b(a+5), w(a+6), w(a+10), w(a+24)))
for i in range(2):
    a = 0xff8568 + 0xc0*i
    print('player%d @%06x on=%d x %d y %d hp %d st %d %d' % (i, a, b(a), w(a+6), w(a+10), w(a+24), b(a+2), b(a+3)))
for s in sys.argv[2:]:
    a, n = s.split(':'); a = int(a, 16); print('%06x:' % a, d[a-B:a-B+int(n)].hex())
