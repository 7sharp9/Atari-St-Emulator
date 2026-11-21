"""Gate for the point plot $142f4 (-> $142fa): natural entries (the dust field $f336, the death-spark loop) plus random (x, y, z) jobs, against
rref.plot_dot.  Compared: the whole memory delta outside the stack.   python3 gate_dot.py [n]    --control: size threshold $800 instead of $700.
Expected: `dot $142f4 natural n/n` and `random m/m`."""
import os, sys, json, random
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import rcommon as R
import rref as F
if '--control' in sys.argv:
    src = open(os.path.join(here, 'rref.py')).read().replace("if D3 < 0x700:", "if D3 < 0x800:")
    import types; F2 = types.ModuleType('rref_bad'); exec(compile(src, 'rref_bad', 'exec'), F2.__dict__); F = F2
n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 30
OUT = R.WORK + '/render/caps/dot'
hits = [1 + 40 * i for i in range(n)]
R.cap_calls(R.SNAP_GAME2, 0x142f4, hits, OUT, 'd', callcap_steps=50000)
ok = 0; sizes = {}
for h in hits:
    j = json.load(open(f'{OUT}/d_{h}.json')); ram = R.load_ram(f'{OUT}/d_{h}.snap')
    m = F.Mem(ram); r = j['reg0']
    F.plot_dot(m, r[1], r[2], r[3])
    stack = (j['entrySP'] - 512, j['entrySP'] + 16)
    got = {a: nw for a, o, nw in j['mem'] if not (stack[0] <= a < stack[1])}
    ok += got == m.changes()
    k = (r[3] & 0xFFFF) < 0x700, (r[3] & 0xFFFF) < 0x1000
    sizes[k] = sizes.get(k, 0) + 1
print(f'dot $142f4 natural {ok}/{len(hits)}  (size classes (2-wide, 2-tall) -> count: {sizes})')
os.system(f'rm -f {OUT}/d_*.snap')
random.seed(5)
snap = R.SNAP_GAME2; ram = R.load_ram(snap)
cases = [dict(D1=random.randrange(16, 304), D2=random.randrange(10, 129), D3=random.choice([100, 0x6ff, 0x700, 0x800, 0xfff, 0x1000, 3000]),
              A6=F.A6) for _ in range(60)]
cases += [dict(D1=x, D2=60, D3=d, A6=F.A6) for x in (15, 16, 31, 32, 303) for d in (100, 0x900)]
for c in cases[:0]: pass
res = R.cc_jobs(snap, [dict(addr=0x142f4, presets=c) for c in cases], OUT, 'dr', steps=50000)
ok2 = 0
for c, j in zip(cases, res):
    m = F.Mem(ram); F.plot_dot(m, c['D1'], c['D2'], c['D3'])
    stack = (j['entrySP'] - 512, j['entrySP'] + 16)
    got = {a: nw for a, o, nw in j['mem'] if not (stack[0] <= a < stack[1])}
    ok2 += got == m.changes()
print(f'dot $142f4 random {ok2}/{len(cases)}')
