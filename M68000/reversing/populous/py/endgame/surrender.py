"""surrender.py - lose for real through the UI: GAME SETUP icon, SURRENDER THIS GAME ($1bafe sets
$2287e = $3affe), then $db4c's end check calls $1c858(1). Snapshots at the menu wait, at $1c858
entry and at the score screen.  usage: python surrender.py [src.snap] [tag]"""
import sys
from eg import *
from popdrive import Game, plan_icon, click_lines
src = sys.argv[1] if len(sys.argv) > 1 else WORK + '/game_start.snap'
tag = sys.argv[2] if len(sys.argv) > 2 else 'surr'
g = Game(ram(src))
L, info = plan_icon(g, 'game_setup')
x0, y0 = info['point']
# SURRENDER THIS GAME: item 16 of $22286 (x 80, y 145, w 128): hit box x 96..224, y 161..169 ($1b2e0)
L += ['bp 1b2d0 20000000', 'snap %s/%s_menu.snap' % (OUT, tag)]
L += click_lines(x0, y0, 150, 165)[:-3]          # up to `mouse down`: the menu returns within the hold
L += ['bp 1c858 40000000', 'mouse up l', 'r', 'snap %s/%s_entry.snap' % (OUT, tag), 'bp 1cfe2 30000000', 'snap %s/%s_score.snap' % (OUT, tag)]
out = repl(src, L)
print('\n'.join(x for x in out.splitlines() if 'breakpoint' in x))
