"""s4_oneplayer.py - the ONE PLAYER item while in two-player mode ($1b3fe, writes at $1b472/$1b496).

There is no serial peer, so two-player mode is simulated by poking one_player_flag $219b0 = 0
*after* GAME SETUP is open (the menu busy-waits on the mouse; $1e712's serial path never runs).
From cg1.snap (custom, human side 0 ctrl 0, side 1 ctrl 1): open GAME SETUP, poke, click ONE PLAYER,
watch the god-record ctrl words, click OK -> op1.snap. Prints every write to both ctrl words."""
import re
from aicfg import *
from s2_custom import Drv, item
from popdrive import icon_point
d = Drv(P('cg1.snap'), P('op1_watch.txt'))
d.recs('start')
d.click(*icon_point('game_setup'), after=8)
d.recs('menu open')
d.r.cmd('w 219b0 00000003')                      # one_player_flag = 0, keep game flags $219b2 = 3
d.recs('poked two-player')
d.r.cmd('watch 21e12 48')                        # ctrl side 0 ($21e12) .. ctrl side 1 ($21e40)
d.click(*item(0x22286, 1))                        # ONE PLAYER
d.recs('after ONE PLAYER click')
print('menu marks: HUMAN VS ATARI %02x  ATARI VS ATARI %02x' % (d.r.mem(0x223ce, 1)[0], d.r.mem(0x223fc, 1)[0]))
x0, y0, x1 = d.btn(0x22a9a)
d.click((x0 + x1) // 2, y0 + 8, after=8)
d.recs('after OK')
d.r.cmd('snap ' + P('op1.snap'))
d.r.close()
print(open(P('op1_watch.txt')).read())
