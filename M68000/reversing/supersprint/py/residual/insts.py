"""Print the instrument records used by the unreferenced scripts (and which instruments no script uses)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rcommon import *
import proof_sound as PS, struct
from tune import W
I = [list(struct.unpack_from('>30h', PS.INS, i * 60)) for i in range(35)]
hdr = 'idx step base reload ival lvl0 seg1 seg2 seg3 start loop d1 d2 d3 glide notone w15 prio'
print(hdr)
for i in (10, 11, 12, 13, 14, 15, 17, 18, 21, 26, 27, 28):
    v = I[i]; print('%2d' % i, ' '.join('%6d' % x for x in v[:17]), ' rest nonzero:', [x for x in v[17:] if x])
# total of waits in script 906 and steps
p = 906; tot = 0; n = 0; steps = 0
while True:
    op = W(p); p += 2
    if op < 7:
        a = W(p); p += 2
        if op == 6: tot += a; n += 1
    else: break
print('script 906: %d waits, sum of wait args %d, steps incl. +1 per wait %d, ISR_HZ-based seconds: %.2f (args only) / %.2f (steps)'
      % (n, tot, tot + n, tot * 9 / 239.77, (tot + n) * 9 / 239.77))
