import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
ADDRS = [0x1399e, 0x139ac, 0x13a5e, 0x18b54, 0x1a4ca, 0xdf18, 0xf9ea, 0x18c60]
for tag, key in (('A no key', None), ('B F1', ['3b'])):
    r = R(sscfg.SNAP_ATTRACT)
    r.cmd('s 500000')
    a = Acc(r, ADDRS)
    if key: a.press(key, 60000)
    a.run(2500000)
    a.show(tag); print('m8070=%x' % r.g16(-8070), 'F1cell=%02x' % r.g8(-4743), 'ch', [r.g16(o) for o in (-4810,-4808,-4806)])
    r.close()
