"""verify_gen.py - byte-compare popgen.build_world() against the real $b316 run under callcap.
cc_b316_w0.json    : game_start.snap as-is (conquest, world 0 GENESIS, LEVEL rec 0, seed 0x6302)
cc_b316_w1235.json : $21d5e=1235 and LEVEL.DAT record 49 poked into $22ad8 (conquest world 1235)
cc_b316_c1234.json : $21d5e=-1, seed $3d52e=0x1234 (custom game typed as a number)
The seed rule is the one in $b316 (see terrain.md)."""
import sys; sys.setrecursionlimit(100000)
import os
from popcfg import WORK
TW = os.path.join(WORK, 'agents', 'terrain')
from popmem import *; from popgen import *
L = open(os.path.join(WORK,'files','LEVEL.DAT'), 'rb').read()
def seed_for(world=None, custom=None):
    if world is not None:
        rec = L[(world//25)*10:(world//25)*10+10]
        return ((rec[8] << 8 | rec[9]) + (world & 7)) & 0xffff, 4
    # custom: one extra rand() (landscape-type coin) when the seed is non-zero
    return custom, (5 if custom else 4)
base = ram(os.path.join(WORK,'game_start.snap'))
for js, kw in (('cc_b316_w0.json', dict(world=0)), ('cc_b316_w1235.json', dict(world=1235)), ('cc_b316_c1234.json', dict(custom=0x1234))):
    m, d = apply_callcap(base, os.path.join(TW, js))
    seed, pre = seed_for(**kw)
    wd = build_world(seed, pre)
    H = [sw(m, 0x34be4+2*i) for i in range(65*65)]
    res = {'heights': wd.h == H,
           'alt $33be4': wd.alt == list(m[0x33be4:0x33be4+4096]),
           'shape $36e78': wd.shape == list(m[0x36e78:0x36e78+4096]),
           'feat $3c522': wd.feat == list(m[0x3c522:0x3c522+4096]),
           'seed(+1 at $b506)': (wd.seed+1) & 0x7fff == w(m, 0x3d52e)}
    print(js, kw, 'seed=%#06x prerolls=%d' % (seed, pre), 'type', w(m, 0x3b246), res)
