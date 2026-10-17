"""heli_flows.py: crash the red car (slot 1) of the live Track-1 race (ss_prep.snap) at several screen positions, via the
documented crash entry: flag -3778(A4)[car] = 1 makes $e0xx call $b3fc, which starts the pickup helicopter (-1898 bit 1 selects
the 64x26 vs 32x36 sprite, -1898 bit 0 / x,y the approach side) and the 26-frame explosion.  The positions are the safe-position
words -3754/-3762(A4) in 1/8 px ($b45x-$b4bx compare them with $a0 / $64 after >>3).  Poison all 28 candidate 1 KB blocks and
bisect; dumps every 500000 steps for 3M steps (the helicopter lasts about 100 frames)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan import *
POS = {'left_top': (20, 20), 'left_bot': (20, 180), 'right_top': (290, 20), 'right_bot': (290, 180), 'mid': (160, 100),
       'left_mid': (20, 100), 'right_mid': (290, 100), 'top_mid': (160, 12), 'bot_mid': (160, 188)}

def script(x, y, car=1, n=6):
    s = ['!pokew %x %d' % (A4 - 3754 + 2 * car, x * 8), '!pokew %x %d' % (A4 - 3762 + 2 * car, y * 8), '!pokew %x 1' % (A4 - 3778 + 2 * car)]
    for _ in range(n): s += ['s 500000', '!dump']
    return s

if __name__ == '__main__':
    names = sys.argv[1:] or list(POS)
    for n in names:
        x, y = POS[n]
        scan('heli_' + n, 'ss_prep.snap', script(x, y))
