"""s3_ava.py - from cg1.snap (custom, evil options all on) open GAME SETUP and click ATARI VS ATARI, OK -> cg2.snap."""
from aicfg import *
from s2_custom import Drv, item
from popdrive import icon_point
d = Drv(P('cg1.snap'))
d.recs('start')
d.click(*icon_point('game_setup'), after=8)
d.click(*item(0x22286, 8))                        # ATARI VS ATARI
x0, y0, x1 = d.btn(0x22a9a)
d.click((x0 + x1) // 2, y0 + 8, after=8)
d.recs('after ATARI VS ATARI')
d.r.cmd('snap ' + P('cg2.snap'))
d.r.close()
