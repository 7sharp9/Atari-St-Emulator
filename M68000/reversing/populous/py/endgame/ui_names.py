"""ui_names.py - world names typed at the briefing (typename.py) and the worlds START GAME built
(startgame.py): name -> popworld.number, the LEVEL record loaded into $22ad8, and the built world
(heights, $33be4, $36e78, $3c522, final seed, landscape) vs popgen.build_world.
Pairs: name<N>.snap (briefing after RETURN) / play<N>.snap ($1d0c0 after $b316)."""
import sys
sys.setrecursionlimit(100000)
from eg import *
from startgame import check_world
PW = import_popworld()
good = tot = 0
for nm_tag, play_tag in (('name1235', 'play1235'), ('name1240', 'play1240'), ('name2470', 'play2470'),
                         ('w2470_brief', 'w2470_play0'), ('name_digits', 'play_digits')):
    b, p = ram(OUT + '/%s.snap' % nm_tag), ram(OUT + '/%s.snap' % play_tag)
    name = cstr(b, 0x37e86)
    n = PW.number(name)
    lv, res = check_world(p, w(p, WORLD))
    checks = [w(p, WORLD) == n, w(p, 0x21d5e) == n, b[0x22ad8:0x22ae2].hex() == PW.level(n)['raw']] + list(res.values())
    good += sum(checks); tot += len(checks)
    print('%-10s -> %4d rec %2d  %d/%d' % (name, n, lv['rec'], sum(checks), len(checks)))
print('ui_names: %d/%d checks' % (good, tot))
