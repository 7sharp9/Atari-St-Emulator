"""Q's one unmatched bucket in liveproof.py (tick 15559 of 15560): show that the extra PSG write is the game's own Supexec($12b9c) (noise period := 5, pc $12ba8)
executed millions of steps after the last fake ISR tick, not an ISR write."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rcommon import *
import psg_capture as PC
ticks = 15560
psg = PC.run(0x12d64, 0, ticks, 'ff8800 4', 6000 + ticks * 1200)
marks = PC.run(0x12d64, 0, ticks, '%x 2' % (sscfg.A4 - 12), 6000 + ticks * 1200)
ts = [m[0] for m in marks if m[4] != 8]
reg = None
for s, pc, k, a, v in psg:
    if a == 0xFF8800: reg = v
    elif a == 0xFF8802 and reg == 6 and s > ts[-1]:
        print('reg 6 := %d written at step %d by pc $%x; the last fake ISR tick was at step %d (%d steps earlier)' % (v, s, pc, ts[-1], s - ts[-1]))
