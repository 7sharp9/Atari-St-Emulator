"""Live check of the chase rule `$00b932` used by type 115 bees (README "Spawn types", item c).

    ATARI_NOTRACE=1 uv run python chase_check.py [snap slot]

`$013602` (type 115 handler `$01417c`, D0 = 0) calls `$b932` (A0 = the bee, A1 = the hero, D7 = speed). Every
75(A0) = 4th call it clears 16/18(A0) and, per axis, when the distance between the hero's and the bee's box centres exceeds
D7 sets the speed to D7 and the direction bit toward the hero (20(A0): 0 left 1 right; 21(A0): 0 up 1 down). D7 = 98(A0),
or 16(A0) (2 for the bee) when 98 is 0. The script stops at `$b932` (reads its inputs from RAM), then at `$b9f8` (the
rts side: reads 16/18/20/21) and compares with the rule. No pokes except health.
"""
import os, sys, struct, re
sys.path.insert(0, os.path.dirname(__file__))
from replx import Repl
from trigger_scan import regs

snap = sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/impossamole/pass103/live_c1.snap'
S = lambda b, k: struct.unpack_from('>h', b, k)[0]


def predict(bee, hero):
    d7 = bee[98] or S(bee, 16) or S(bee, 18)
    sp = d7 & 0xff
    if bee[76] + 1 != bee[75]:                         # counter not yet at the period: nothing changes
        return None
    d0 = ((S(hero, 8) * 2 + hero[12]) - (S(bee, 8) * 2 + bee[12])) >> 1
    d0 += S(hero, 2) - S(bee, 2)
    v16, x20 = 0, bee[20]
    if d0 < 0:
        if -d0 > d7:
            v16, x20 = d7, 0
    elif d0 > d7:
        v16, x20 = d7, 1
    d1 = ((S(hero, 10) * 2 + hero[13]) - (S(bee, 10) * 2 + bee[13])) >> 1
    d1 += S(hero, 4) - S(bee, 4)
    v18, y21 = 0, bee[21]
    if d1 < 0:
        if -d1 > d7:
            v18, y21 = d7, 0
    elif d1 > d7:
        v18, y21 = d7, 1
    return v16, v18, x20, y21


with Repl(snap) as r:
    r.run('w bb74 12120300')
    ok = n = calls = rec = 0
    for _ in range(80):
        out = r.run('s 1', 'bp b932 400000')
        g = regs(out)
        if g.get('PC') != 0xb932:
            break
        a = g['A0']
        if a == 0x1a572:
            continue
        bee = r.mem(a, 108)
        hero = r.mem(0x1a572, 108)
        calls += 1
        want = predict(bee, hero)
        out = r.run('s 1', 'bp b9f8 400000')
        after = r.mem(a, 108)
        if want is None:
            n += 1
            ok += (S(after, 16), S(after, 18), after[20], after[21]) == (S(bee, 16), S(bee, 18), bee[20], bee[21])
            continue
        n += 1
        rec += 1
        got = (S(after, 16), S(after, 18), after[20], after[21])
        ok += got == want
        if got != want:
            print('MISMATCH', hex(a), 'want', want, 'got', got)
    print(f'{snap}: {ok}/{n} `$b932` calls (all objects that call it) match the rule ({calls} calls seen, {rec} of them recomputed the velocities)')
