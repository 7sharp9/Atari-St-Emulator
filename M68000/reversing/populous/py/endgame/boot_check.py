"""boot_check.py - the three title-menu start paths (boot_mode.py snapshots).
boot_<mode>_b510.snap = $b510 entry, boot_<mode>_built.snap = $b538 (after the first $b316(0,1)),
boot_<mode>_run.snap = 20M steps later (tutorial/custom).
Checks: mode $37ebc, the first world = build_world(seed, pre-rolls) (seed 0 for custom and conquest,
$69bc for the tutorial), mana, options, god records, pause."""
import sys
sys.setrecursionlimit(100000)
from eg import *
from popgen import build_world
from popmem import img
I = img()
good = tot = 0
def chk(name, ok):
    global good, tot
    good += bool(ok); tot += 1
    if not ok: print('  FAIL', name)
for mode, num, seed, pre in (('custom', 1, 0, 4), ('conquest', 2, 0, 4), ('tutorial', 3, 0x69bc, 5)):
    b0, b1 = ram(OUT + '/boot_%s_b510.snap' % mode), ram(OUT + '/boot_%s_built.snap' % mode)
    chk('mode', w(b0, 0x37ebc) == num)
    wd = build_world(seed, pre)
    H = [sw(b1, 0x34be4 + 2 * i) for i in range(65 * 65)]
    for k, v in dict(h=wd.h == H, alt=wd.alt == list(b1[0x33be4:0x33be4 + 4096]), shape=wd.shape == list(b1[0x36e78:0x36e78 + 4096]),
                     feat=wd.feat == list(b1[0x3c522:0x3c522 + 4096]), seed=(wd.seed + 1) & 0x7fff == w(b1, 0x3d52e)).items():
        chk(k, v)
    chk('custom path $21d5e=-1', w(b1, 0x21d5e) == 0xffff)
    tut = mode == 'tutorial'
    chk('mana', (l(b1, SIDE + 12), l(b1, SIDE + 28)) == ((10000 if tut else 399), 399))
    chk('god recs', b0[GOD:GOD + 0x5c] == (I[0x22af2:0x22af2 + 0x2e] + I[0x22b20:0x22b20 + 0x2e] if tut else I[GOD:GOD + 0x5c]))
    chk('options $219b2', w(b0, 0x219b2) == (w(I, 0x22ad6) if tut else w(I, 0x219b2)))
    chk('paused $3b274', w(b0, 0x3b274) == int(tut))
    print(mode, 'seed %#x pre %d' % (seed, pre), 'mana', l(b1, SIDE + 12), l(b1, SIDE + 28), 'walkers', [d['side'] for i, e, d in entities(b1)].count(0), [d['side'] for i, e, d in entities(b1)].count(1))
for mode in ('custom', 'tutorial'):
    r = ram(OUT + '/boot_%s_run.snap' % mode)
    chk('frame counter after 20M steps (paused -> 0)', (w(r, 0x3c4c8) == 0) == (mode == 'tutorial'))
    print(mode, 'run: frame', w(r, 0x3c4c8), 'mode now', w(r, 0x37ebc))
print('boot_check: %d/%d' % (good, tot))
