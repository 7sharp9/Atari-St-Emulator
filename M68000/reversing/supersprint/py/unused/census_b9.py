"""census_b9.py ANIM: from pre_winner.snap (winner's circle entered) force the prize animation index (poke -2(A6) at $1ad80), then
census every call of the prize-frame blitter $1617a (src pointer = 8(A7) at entry) for N hits / MAX steps.  Prints the B9 frame index
(src - (SUPER.DAT base + 0x29c4e)) / 0x300 of each call.  B9 frame = 3*anim + img (the $1b4e4 wrapper)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uc import *
B9 = BUF + 0x29c4e

def census(anim, maxhits=400, maxsteps=40000000, snap='pre_winner.snap'):
    r = Repl2(snapath(snap))
    o, regs = r.cmd2('bpc 1ad80 1 60000000')
    a6 = regs['A6']; old = r.mem(a6 - 2, 4)
    r.cmd('w %x %04x%s' % (a6 - 2, anim, old[2:].hex()))
    seen = []; steps_used = 0
    for _ in range(maxhits):
        o, regs = r.cmd2('bpc 1617a 1 %d' % maxsteps)
        if regs['PC'] != 0x1617a: break
        src = int.from_bytes(r.mem(regs['A7'] + 8, 4), 'big')
        seen.append((src - B9) / 0x300)
    r.close()
    return seen

if __name__ == '__main__':
    for a in [int(x) for x in sys.argv[1:]] or [0, 1, 2, 3]:
        s = census(a)
        print('anim', a, 'hits', len(s), 'distinct B9 frames', sorted(set(int(x) for x in s)), 'first 40:', [int(x) for x in s[:40]])
