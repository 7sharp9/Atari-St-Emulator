"""face_gate.py - prove the face visibility (back-face) test $9426 against a python model by callcap.
A0 -> 3 vertex-index bytes, A1 = vertex table (6 bytes/vertex: x,y,z words, view axes), object centre in view space at $a7c/$a80/$a84.
result D0 = dot(n, eye - v0) after both vectors are halved until they fit 16 bits; the caller skips the face if D0 < 0 (bmi)."""
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent)); _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
import random, struct, sys
from rig import *
random.seed(3)
def s32(v): v &= 0xffffffff; return v - (1 << 32) if v & 0x80000000 else v
def fits(v): return -32768 <= v <= 32767
def model(vs, idx, c):
    v0, v1, v2 = (vs[i] for i in idx)
    e1 = [(a - b) >> 1 for a, b in zip(v1, v0)]; e2 = [(a - b) >> 1 for a, b in zip(v2, v0)]
    n = (e1[1]*e2[2] - e1[2]*e2[1], e1[2]*e2[0] - e1[0]*e2[2], e1[0]*e2[1] - e1[1]*e2[0])
    d = [-(c[k] + v0[k]) for k in range(3)]
    while not all(fits(x) for x in d): d = [x >> 1 for x in d]
    n = [s32(x) for x in n]
    while not all(fits(x) for x in n): n = [x >> 1 for x in n]
    return s32(sum(a*b for a, b in zip(d, n)))
tests = []; cmds = []; A1 = 0x60000; A0 = 0x62000
for t in range(120):
    vs = [tuple(random.randint(-3000, 3000) for _ in range(3)) for _ in range(8)]
    idx = random.sample(range(8), 3); c = tuple(random.randint(-9000, 9000) for _ in range(2)) + (random.randint(500, 60000),)
    if t % 3 == 0: c = tuple(random.randint(-70000, 70000) for _ in range(3))
    tests.append((vs, idx, c))
    cmds += [f'w {a:x} {v & 0xffffffff:08x}' for a, v in ((0xa7c, c[0]), (0xa80, c[1]), (0xa84, c[2]))]
    for i, (x, y, z) in enumerate(vs): cmds += [f'w {A1+6*i:x} {x & 0xffff:04x}{y & 0xffff:04x}', f'w {A1+6*i+4:x} {z & 0xffff:04x}0000']
    cmds += [f'w {A0:x} {idx[0]:02x}{idx[1]:02x}{idx[2]:02x}00', f'callcap 9426 20000 A0={A0:x} A1={A1:x}']
res = [r for r in parse_callcaps(repl(cmds)) if r['addr'] == 0x9426]
assert len(res) == len(tests)
ok = 0; neg = 0; bad = []
for (vs, idx, c), r in zip(tests, res):
    e = s32(r['regs']['D0'][1]) if 'D0' in r['regs'] else None
    m = model(vs, idx, c)
    if e == m: ok += 1; neg += m < 0
    else: bad.append((e, m))
print('face test match', ok, '/', len(tests), '(of which negative=back-facing:', neg, ')'); print(bad[:4])
