"""Gate for $12f1c (bearing of an object from the camera by an arctangent table).   python3 gate_bearing.py [n]   --control: base angle $c00 -> $c01
Random (dx, dz) pairs by POKING the world x/z words of a record at $5c700 (4/8(A0)) and the camera 302/306(A6); natural callers are the enemy
routines at $12824..$12d96.  Compared: exit D1 (low word).  Inputs with dx = 0 divide by zero (vector 5, TOS's handler at $fc0724): the reference raises ZeroDivisionError and
those inputs are excluded from the count (the callers must keep dx away from 0; not checked).   Expected: `bearing $12f1c n/n`."""
import os, sys, random
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import rcommon as R
import rref as F
if '--control' in sys.argv:
    src = open(os.path.join(here, 'rref.py')).read().replace("D5 = 0xC00", "D5 = 0xC01")
    import types; F2 = types.ModuleType('rref_bad'); exec(compile(src, 'rref_bad', 'exec'), F2.__dict__); F = F2
n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 80
random.seed(12)
ram = R.load_ram(R.SNAP_GAME2); A6 = F.A6; REC = 0x5c700
cases = []
for i in range(n):
    cx, cz = random.randrange(-30000, 30000), random.randrange(-30000, 30000)
    sc = random.choice([50, 500, 5000, 20000])
    dx, dz = random.randrange(-sc, sc), random.randrange(-sc, sc)
    if i % 10 == 0: dz = 0
    if i % 13 == 0: dx = dz
    pk = [('ww', A6 + 302, cx), ('ww', A6 + 306, cz), ('ww', REC + 4, (cx + dx) & 0xFFFF), ('ww', REC + 8, (cz + dz) & 0xFFFF)]
    cases.append((dict(A0=REC, A6=A6), pk, (dx, dz)))
res = R.cc_jobs(R.SNAP_GAME2, [dict(addr=0x12f1c, presets=p, pokes=pk) for p, pk, d in cases], R.WORK + '/render/caps', 'brg', steps=50000)
ok = 0; zd = 0
for (p, pk, d), j in zip(cases, res):
    base = bytearray(ram)
    for k, a, v in pk: base[a] = v >> 8 & 255; base[a + 1] = v & 255
    m = F.Mem(base)
    try:
        want = F.bearing(m, REC)
    except ZeroDivisionError:
        zd += 1; continue
    g = j['outcome'] == 'returned' and (j['regN'][1] & 0xFFFF) == (want & 0xFFFF)
    ok += g
    if not g: print('MISS', d, j['outcome'], hex(j['regN'][1] & 0xFFFF), hex(want & 0xFFFF))
print(f'bearing $12f1c {ok}/{len(cases) - zd}   ({zd} further inputs with dx = 0 excluded: DIVS by zero enters the vector-5 handler)')
