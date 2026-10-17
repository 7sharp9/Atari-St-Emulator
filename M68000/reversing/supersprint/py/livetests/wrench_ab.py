"""wrench_ab.py - the wrench counter -3954(A4)[car] increments by exactly 1 per pickup; same-snapshot A/B.

Base data/lead_base.snap (Track 1 race live, human slot 1), run to the first frame where the wrench state machine ($ae0e) has placed a wrench
(-1850(A4) == 4; its cell col/row at -1852/-1854; the surface map [-1910(A4)] holds 0x0d there).  Snapshot (data/wr_base.snap), then each arm
teleports a car (labelled pokes of Q -3738/-3746 and the previous position -3786/-3794, per wrench_probe.py) and runs 8 frames:
  ctl     no teleport (human parked at the start line)
  off     human teleported 3 cells right of the wrench (same teleport code path, different cell)
  human   human (slot 1) teleported onto the wrench
  drone   drone slot 3 teleported onto the wrench
Reports for each: counts -3954[0..3], pickup flag -1856, wrench state -1850, the two map cells, plus the next-wrench respawn timer -1848."""
from lt import *
base = os.path.join(DATA, 'wr_base.snap')
LB = os.path.join(DATA, 'lead_base.snap')
if not os.path.exists(base):
    r = Repl2(LB)
    for _ in range(1500):
        r.cmd('s 12000')
        if r.a4w(-1850, 1)[0] == 4: break
    assert r.a4w(-1850, 1)[0] == 4
    r.cmd('snap %s' % base); r.close()
def cell(r, col, row):
    mp = struct.unpack('>I', r.mem(A4 - 1910, 4))[0]
    return r.mem(mp + col + row * 40, 2).hex()
res = {}
for arm in ('ctl', 'off', 'human', 'drone'):
    r = Repl2(base)
    col, row = r.a4w(-1852, 1)[0], r.a4w(-1854, 1)[0]
    before = (r.a4w(-3954, 4), cell(r, col, row), r.a4w(-1856, 1)[0], r.a4w(-1850, 1)[0])
    if arm != 'ctl':
        car = 3 if arm == 'drone' else 1
        c2 = col + 3 if arm == 'off' else col
        X, Y = c2 * 64 + 16, row * 64 - 48          # heading-12 sampler offsets, per tracks/wrench_probe.py
        setwords(r, {A4 + o + 2 * car: v for o, v in ((-3786, X), (-3738, X), (-3794, Y), (-3746, Y))})
    for _ in range(8): r.cmd('s 12000')
    after = (r.a4w(-3954, 4), cell(r, col, row), r.a4w(-1856, 1)[0], r.a4w(-1850, 1)[0])
    res[arm] = (before, after)
    print('%-5s wrench cell (%d,%d) counts %s -> %s ; map cell %s -> %s ; pickup flag -1856 %d -> %d ; state -1850 %d -> %d' % (
        arm, col, row, before[0], after[0], before[1], after[1], before[2], after[2], before[3], after[3]), flush=True)
    r.close()
