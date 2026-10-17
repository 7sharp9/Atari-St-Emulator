"""Script length per entry: sum of wait arguments (what sound.md's table lists) vs real sequencer steps (each wait w holds w+1 steps, see Driver.seq_step)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rcommon import *
from tune import W, ISR_HZ
STARTS = {0: 'A', 14: 'H', 28: 'C', 74: 'I', 88: 'E', 166: 'D', 180: 'F', 194: 'J0', 208: 'J1', 222: 'J2', 236: 'O', 242: 'K', 272: 'L', 302: 'G', 316: 'B/T', 322: 'M',
          336: 'N', 906: 'Q', 2580: 'S', 3398: 'P0', 4488: 'P1', 5302: 'P2', 5916: 'P3', 6794: 'P4', 7780: 'R'}
f = open(os.path.join(OUT, 'durations.txt'), 'w')
for off, name in STARTS.items():
    p = off; tot = 0; n = 0
    while True:
        op = W(p); p += 2
        if op < 7:
            a = W(p); p += 2
            if op == 6: tot += a; n += 1
        else: break
    s = '%-4s off %5d waits %4d  sum(arg) %5d = %6.2f s   steps %5d = %6.2f s' % (name, off, n, tot, tot * 9 / ISR_HZ, tot + n, (tot + n) * 9 / ISR_HZ)
    print(s); f.write(s + '\n')
