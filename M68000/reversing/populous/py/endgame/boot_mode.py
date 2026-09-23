"""boot_mode.py - pick TUTORIAL / CONQUEST / CUSTOM on the DEMO.GOD title menu (menu.snap) and
run into POPULOUS.GOD: snapshots at main's mode store ($ae36), at $b510 entry and after a
fixed run into the game.  Title menu: left click at x > 220 picks by y band (README).
usage: python boot_mode.py tutorial|custom|conquest [steps_after]"""
import sys
from eg import *
mode = sys.argv[1]
after = int(sys.argv[2]) if len(sys.argv) > 2 else 20000000
dy2 = {'tutorial': 72, 'conquest': 88, 'custom': 100}[mode]     # pointer y 160 / 176 / 188 (x 250)
L = ['u b410 10000000', 's 300000', 'mouse move 125 88', 's 200000', 'mouse move 125 %d' % dy2, 's 200000',
     'mouse down l', 's 200000', 'mouse up l',
     'bp ae36 80000000', 'm 37ebc 2', 'snap %s/boot_%s_main.snap' % (OUT, mode),
     'bp b510 80000000', 'snap %s/boot_%s_b510.snap' % (OUT, mode),
     's %d' % after, 'r', 'snap %s/boot_%s_run.snap' % (OUT, mode)]
out = repl(WORK + '/menu.snap', L, timeout=20000)
print('\n'.join(x for x in out.splitlines() if 'breakpoint' in x or x.startswith('PC') or re.fullmatch(r'[0-9a-f]{2} [0-9a-f]{2}', x.strip())))
