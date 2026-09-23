"""s1_start.py - custom game: from c2.snap (custom-mode world briefing) click START GAME -> cg0.snap."""
from aicfg import *
from popdrive import click_lines, run
from popmem import ram, sw
m = ram(P('c2.snap'))
px, py = sw(m, 0x24748), sw(m, 0x2474a)
L = click_lines(px, py, 85, 176)
out = run(P('c2.snap'), L, P('cg0.snap'), extra=['s 30000000'])
