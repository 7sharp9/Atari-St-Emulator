"""rot_gate.py - prove the 2D rotation primitives ($a036/$a040/$a0fe/$a108 forward, $a09a/$a0a4 inverse, $a12c/$a16c angle-driven
via the Q14 sine table $1864) against a python model, by callcap. Q14: (x*c -/+ y*s)*4 >> 16 as 16-bit words."""
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent)); _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
import random, struct, sys
from rig import *
random.seed(5)
SIN = [struct.unpack('>h', RAM[0x1864 + 2*k: 0x1866 + 2*k])[0] for k in range(4096)]
def s16(v): v &= 0xffff; return v - 65536 if v & 0x8000 else v
def fwd(x, y, s, c): return s16(((x*c - y*s) * 4) >> 16), s16(((y*c + x*s) * 4) >> 16)
def inv(x, y, s, c): return s16(((x*c + y*s) * 4) >> 16), s16(((y*c - x*s) * 4) >> 16)
# routine -> (pair address, model)
R = {0xa036: (0xa70, fwd), 0xa040: (0xa64, fwd), 0xa0fe: (0xa78, fwd), 0xa108: (0xa6c, fwd), 0xa09a: (0xa74, inv), 0xa0a4: (0xa68, inv)}
tests = []; cmds = []
for rt, (pa, m) in R.items():
    for _ in range(60):
        ang = random.randrange(4096); s = SIN[ang]; c = SIN[(ang + 1024) % 4096]
        x = random.randint(-20000, 20000); y = random.randint(-20000, 20000)
        tests.append((rt, x, y, s, c))
        cmds += [f'w {pa:x} {s & 0xffff:04x}{c & 0xffff:04x}', f'callcap {rt:x} 5000 D0={x & 0xffff:x} D1={y & 0xffff:x}']
for rt, fn in ((0xa12c, fwd_ := None), (0xa16c, None)): pass
ang_tests = []
for rt, m in ((0xa12c, inv), (0xa16c, fwd)):
    for _ in range(60):
        a = random.randrange(65536); k = (a & 0xfff0) >> 4; s = SIN[k]; c = SIN[(k + 1024) % 4096]
        x = random.randint(-20000, 20000); y = random.randint(-20000, 20000)
        ang_tests.append((rt, a, x, y, m(x, y, s, c))); cmds.append(f'callcap {rt:x} 5000 D0={x & 0xffff:x} D1={y & 0xffff:x} D2={a:x}')
res = [r for r in parse_callcaps(repl(cmds)) if r['status'] == 'returned,' or True]
assert len(res) == len(tests) + len(ang_tests), (len(res), len(tests) + len(ang_tests))
ok = 0; bad = []
for t, r in zip(tests, res):
    rt, x, y, s, c = t; mx, my = R[rt][1](x, y, s, c)
    # callcap reports changed registers only; unchanged result registers keep their entry value
    d0 = r['regs'].get('D0', (None, None)); d1 = r['regs'].get('D1', (None, None))
    ex = s16(d0[1] if d0[1] is not None else x); ey = s16(d1[1] if d1[1] is not None else y)
    # model result is the low word of the swapped long; D0.w = result
    if (ex, ey) == (mx, my): ok += 1
    else: bad.append((t, (ex, ey), (mx, my)))
aok = 0
for t, r in zip(ang_tests, res[len(tests):]):
    rt, a, x, y, (mx, my) = t
    d0 = r['regs'].get('D0', (None, None)); d1 = r['regs'].get('D1', (None, None))
    ex = s16(d0[1] if d0[1] is not None else x); ey = s16(d1[1] if d1[1] is not None else y)
    if (ex, ey) == (mx, my): aok += 1
    else: bad.append((t, (ex, ey), (mx, my)))
print('pair-table rotations match', ok, '/', len(tests), '; angle-driven ($a12c inverse, $a16c forward) match', aok, '/', len(ang_tests))
print(bad[:4])
