"""quirk.py <calls.bin>... : how often the $f2f4 rotation quirk (direction 0 scanned twice, direction
r-1 never scanned when r = (rand&7)+1 >= 2) changes a live decision, and how the real choice
distributes over the 9 offsets. Compares walker_ref.scan_f2f4 (real, 100% vs D0) with the
counterfactual ideal=True scan of all 8 neighbours.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import walker_ref as W
import capcalls as C
from livecheck import BASE, s16

tot = diff = realok = 0
for path in sys.argv[1:]:
    for r in C.load(path):
        m = C.apply(BASE, r['mem'])
        if W.uses_f6b2(m, r['e']): continue
        a = W.scan_f2f4(bytearray(m), r['e'], s16(r['idx']))
        b = W.scan_f2f4(bytearray(m), r['e'], s16(r['idx']), ideal=True)
        tot += 1; realok += (a & 0xffff) == r['d0']; diff += a != b
print('f2f4 live decisions %d (model == real %d); ideal 8-way scan would differ in %d' % (tot, realok, diff))
