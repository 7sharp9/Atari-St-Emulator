"""proj_gate.py - prove the projection $53f4 against a python model with callcap.
sx = ((X<<s)/Z') + cx, sy = ((Y<<s)/Z') + cy;  X = x + $a7c, Y = -y - $a80, Z = z + $a84 (view-axis coords);
Z < $a88 (near plane) -> y := $80000000. Before the divide X,Y,Z are halved until (2*Z)>>16 == 0."""
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent)); _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
import random, struct, sys
from rig import *
random.seed(11)
def s32(v): return v - (1 << 32) if v & 0x80000000 else v
def s16(v): return v - (1 << 16) if v & 0x8000 else v
def tdiv(a, b):
    q = abs(a) // abs(b); return q if (a < 0) == (b < 0) else -q
SX, SY, CX, CY = 8, 8, 160, 70            # $6fc descriptor words +8,+10,+12,+14 in the snapshot
def model(verts, c, near):
    out = []
    for (x, y, z) in verts:
        X = x + c[0]; Y = -y - c[1]; Z = z + c[2]
        if Z < near: out.append((None, 0x80000000)); continue
        while ((2 * Z) >> 16) != 0: X >>= 1; Y >>= 1; Z >>= 1
        out.append((tdiv(X << SX, Z) + CX, tdiv(Y << SY, Z) + CY))
    return out
N = 12
tests = []
for t in range(40):
    near = random.choice([0x40, 0x100, 0x200])
    c = (random.randint(-60000, 60000), random.randint(-60000, 60000), random.choice([random.randint(0, 3000), random.randint(300, 70000)]))
    vs = [(random.randint(-3000, 3000), random.randint(-3000, 3000), random.randint(-3000, 3000)) for _ in range(N)]
    tests.append((near, c, vs))
cmds = []; A1 = 0x60000; A2 = 0x61000
for near, c, vs in tests:
    cmds += [f'w a7c {c[0] & 0xffffffff:08x}', f'w a80 {c[1] & 0xffffffff:08x}', f'w a84 {c[2] & 0xffffffff:08x}', f'w a88 {near:08x}', f'w 89c {N:04x}0000']
    for i, (x, y, z) in enumerate(vs):
        cmds += [f'w {A1+6*i:x} {x & 0xffff:04x}{y & 0xffff:04x}', f'w {A1+6*i+4:x} {z & 0xffff:04x}0000']
    cmds.append(f'callcap 53f4 200000 A1={A1:x} A2={A2:x}')
res = [r for r in parse_callcaps(repl(cmds)) if r['addr'] == 0x53f4]
assert len(res) == len(tests), len(res)
ok = tot = 0; bad = []
for (near, c, vs), r in zip(tests, res):
    buf = apply(RAM, r['mem'])
    mod = model(vs, c, near)
    for i, (mx, my) in enumerate(mod):
        ex = s32(struct.unpack_from('>I', buf, A2 + 8 * i)[0]); ey = struct.unpack_from('>I', buf, A2 + 8 * i + 4)[0]
        tot += 1
        if my == 0x80000000: good = (ey == 0x80000000)
        else: good = (ex == mx and s32(ey) == my)
        ok += good
        if not good: bad.append((c, near, vs[i], (ex, s32(ey)), (mx, my)))
print('projection match', ok, '/', tot); print(bad[:5])
print('behind near plane (y=$80000000):', sum(1 for _, _, vs in [] ) )
print('vertices clipped by near rule in test:', sum(1 for (near, c, vs) in tests for (x,y,z) in vs if z + c[2] < near))
