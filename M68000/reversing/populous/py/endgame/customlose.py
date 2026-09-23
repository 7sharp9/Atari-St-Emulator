"""customlose.py - lose a custom game (mode 1 boot) and click NEW GAME: $1c858 skips $1d0e6
($21d5e == -1) and $b316(0,-1) builds a custom world from the current seed $3d52e. Checks the
rebuilt world against build_world(seed at $b316 entry, 5 pre-rolls when seed != 0)."""
import sys
sys.setrecursionlimit(100000)
from eg import *
from popdrive import move_lines
from popgen import build_world
src = OUT + '/boot_custom_run.snap'
m = ram(src)
P = Poker(m)
for i, e, d in entities(m):
    if d['side'] == 0 and d['str'] > 0:
        P.w(e + 4, 0)
L = P.flush() + ['bp 1c858 3000000', 'r', 'snap %s/clost_entry.snap' % OUT, 'bp 1cfe2 30000000', 'snap %s/clost_score.snap' % OUT]
out = repl(src, L)
m1 = ram(OUT + '/clost_score.snap')
L = move_lines(sw(m1, 0x24748), sw(m1, 0x2474a), 160, 184) + ['s 240000', 'mouse down l', 'bp b316 3000000', 'mouse up l',
     'm 3d52e 2', 'm 3b246 2', 'bp 1d0c0 80000000', 'snap %s/clost_built.snap' % OUT]
out = repl(OUT + '/clost_score.snap', L)
hx = [x for x in out.splitlines() if re.fullmatch(r'[0-9a-f]{2} [0-9a-f]{2}', x.strip())]
seed = int(hx[0].replace(' ', ''), 16); land0 = int(hx[1].replace(' ', ''), 16)
m2 = ram(OUT + '/clost_built.snap')
wd = build_world(seed, 5 if seed else 4)
H = [sw(m2, 0x34be4 + 2 * i) for i in range(65 * 65)]
print('button', rowtext(m1, 0), 'seed at $b316 %#x' % seed, 'landscape', land0, '->', w(m2, 0x3b246),
      dict(h=wd.h == H, shape=wd.shape == list(m2[0x36e78:0x36e78 + 4096]), feat=wd.feat == list(m2[0x3c522:0x3c522 + 4096]),
           seed=(wd.seed + 1) & 0x7fff == w(m2, 0x3d52e)))
