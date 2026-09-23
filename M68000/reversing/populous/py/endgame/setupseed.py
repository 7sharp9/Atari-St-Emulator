"""setupseed.py - the custom-seed path through the UI: GAME SETUP -> CONQUEST opens the world
dialog ($1ba14 -> $1a5c4); NEW GAME, type a number, RETURN: $1a5c4 stores atoi() in $3d52e/$37ec2
and returns -1, so $21d5e=-1 and $3c4de=1; the cmd-14 handler then runs $b316(0,-1) ($1fa86) on the
custom path. Compares the built world with popgen.build_world(number, 5).
usage: python setupseed.py [number]"""
import sys
sys.setrecursionlimit(100000)
from eg import *
from popdrive import Game, plan_icon, click_lines, move_lines
from typename import key_lines
from popgen import build_world
num = sys.argv[1] if len(sys.argv) > 1 else '1234'
src = WORK + '/game_start.snap'
g = Game(ram(src))
L, info = plan_icon(g, 'game_setup')
x, y = info['point']
L += click_lines(x, y, 36, 96)                         # CONQUEST item 9: hit box x 32..40, y 92..100
L += ['bp 1afc4 40000000']
L += click_lines(36, 96, 240, 176)                     # NEW GAME in the world dialog
L += key_lines('\b' + num + '\n')
L += ['bp 1fa8c 80000000', 'r', 'snap %s/setupseed_%s.snap' % (OUT, num)]
out = repl(src, L)
print('\n'.join(x for x in out.splitlines() if 'breakpoint' in x))
m = ram(OUT + '/setupseed_%s.snap' % num)
seed = int(num)
wd = build_world(seed, 5 if seed else 4)
H = [sw(m, 0x34be4 + 2 * i) for i in range(65 * 65)]
print('21d5e', hex(w(m, 0x21d5e)), 'world_seed', w(m, 0x37ec2), 'landscape', w(m, 0x3b246),
      dict(h=wd.h == H, alt=wd.alt == list(m[0x33be4:0x33be4 + 4096]), shape=wd.shape == list(m[0x36e78:0x36e78 + 4096]),
           feat=wd.feat == list(m[0x3c522:0x3c522 + 4096]), seed=(wd.seed + 1) & 0x7fff == w(m, 0x3d52e)))
