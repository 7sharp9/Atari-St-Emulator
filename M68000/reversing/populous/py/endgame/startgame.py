"""startgame.py - click START GAME on a briefing snapshot and stop after the world is built.

Stops at the first of $1d0c0 (after $b316(0,-1) in the post-score path) or $b5e8 (the boot
briefing path in $b510), snapshots, then byte-compares heights and the three cell maps with
popgen.build_world for the world's LEVEL seed (terrain.md 3).
usage: python startgame.py <in_tag> <out_tag>"""
import sys
sys.setrecursionlimit(100000)
from eg import *
from popdrive import click_lines
from popgen import build_world
PW = import_popworld()

def check_world(m, world):
    lv = PW.level(world)
    wd = build_world(lv['seed'], 4)
    H = [sw(m, 0x34be4 + 2 * i) for i in range(65 * 65)]
    res = dict(heights=wd.h == H, alt=wd.alt == list(m[0x33be4:0x33be4 + 4096]),
               shape=wd.shape == list(m[0x36e78:0x36e78 + 4096]), feat=wd.feat == list(m[0x3c522:0x3c522 + 4096]),
               seed=(wd.seed + 1) & 0x7fff == w(m, 0x3d52e), landscape=w(m, 0x3b246) == int(lv['raw'][10:12], 16))
    return lv, res

if __name__ == '__main__':
    tin, tout = sys.argv[1], sys.argv[2]
    src = OUT + '/%s.snap' % tin
    m = ram(src)
    L = click_lines(sw(m, 0x24748), sw(m, 0x2474a), 88, 176)[:-1]       # START GAME (32..144, 168..184)
    L += ['bp 1d0c0 80000000', 'snap %s/%s.snap' % (OUT, tout)]
    out = repl(src, L)
    print('\n'.join(x for x in out.splitlines() if 'breakpoint' in x or x.startswith('PC')))
    m = ram(OUT + '/%s.snap' % tout)
    world = w(m, WORLD)
    lv, res = check_world(m, world)
    print('world', world, '$21d5e', w(m, 0x21d5e), 'rec', lv['rec'], 'seed %#x' % lv['seed'], res)
    print('mana you/him', l(m, SIDE + 12), l(m, SIDE + 16 + 12), 'score', l(m, SCORE), 'opts', hex(w(m, GOD + 14)), hex(w(m, GOD + 0x2e + 14)), '$219b2', hex(w(m, 0x219b2)))
