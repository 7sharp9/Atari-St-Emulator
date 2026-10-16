"""poolscan.py <snap>... : list byte6-6 camp markers in the marker pool $4cff8..$4d250 (10-byte slots,
byte 5 side (0 = free), byte 6 category, byte 7 kind, word 8 cell). One line per snapshot:
n_lit($12) n_out($11) and the slots."""
import sys, os
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')): d = os.path.dirname(d)
sys.path.insert(0, os.path.join(d, 'tools'))
from disassemble import ram_from_snap
for p in sys.argv[1:]:
    try: r = ram_from_snap(p)
    except Exception as e: print('ERR', p, e); continue
    recs = [(a, r[a+5], r[a+7], (r[a+8] << 8) | r[a+9]) for a in range(0x4cff8, 0x4d250, 10) if r[a+5] and r[a+6] == 6]
    lit = sum(1 for x in recs if x[2] == 0x12); out = sum(1 for x in recs if x[2] == 0x11)
    print(lit, out, p, ' '.join('%x:s%d:k%02x:c%04x' % x for x in recs))
