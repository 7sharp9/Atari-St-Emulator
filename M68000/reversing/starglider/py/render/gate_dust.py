"""Gate for the ground-dust field $f336 (with its colour setup, the view transform $ec1e, the divide, the window test, the plot $142f4 and the
respawn through the generator $f23e) and the generators $f21e / $f23e, against rref on natural entries (g_game2, every 10th hit).
    python3 gate_dust.py [n]      --control: respawn offset 0x1000 changed to 0x1001
Expected: `dust $f336 n/n`, `rng $f21e n/n`, `rng $f23e n/n`."""
import os, sys, json
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import rcommon as R
import rref as F
if '--control' in sys.argv:
    src = open(os.path.join(here, 'rref.py')).read().replace("- 0x1000)", "- 0x1001)")
    import types; F2 = types.ModuleType('rref_bad'); exec(compile(src, 'rref_bad', 'exec'), F2.__dict__); F = F2
n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 12
OUT = R.WORK + '/render/caps/dust'
def gate(name, addr, hits, call):
    R.cap_calls(R.SNAP_GAME2, addr, hits, OUT, name, callcap_steps=300000)
    ok = 0; respawn = 0
    for h in hits:
        j = json.load(open(f'{OUT}/{name}_{h}.json')); ram = R.load_ram(f'{OUT}/{name}_{h}.snap')
        m = F.Mem(ram); regs = call(m, j['reg0'])
        stack = (j['entrySP'] - 512, j['entrySP'] + 16)
        got = {a: nw for a, o, nw in j['mem'] if not (stack[0] <= a < stack[1])}
        good = got == m.changes() and (regs is None or (j['regN'][0] & 0xFFFFFFFF) == regs)
        ok += good
        if not good and ok < 2: print('MISS', h, sorted(got.items())[:5], sorted(m.changes().items())[:5], regs, j['regN'][0])
    print(f'{name} {addr:#x} {ok}/{len(hits)}')
    os.system(f'rm -f {OUT}/{name}_*.snap')
gate('dust', 0xf336, [1 + 2 * i for i in range(n)], lambda m, r: F.dust(m, r[0]))
gate('rng1', 0xf21e, [1 + 30 * i for i in range(n)], lambda m, r: F.rng1(m))
gate('rng2', 0xf23e, [1 + 30 * i for i in range(n)], lambda m, r: (lambda d: (r[0] & 0xFFFF0000) | d)(F.rng2(m, r[0])))

# poked variant: camera moved/turned so that most of the 40 points leave the frustum and respawn (labelled POKES: 302/306 camera x/z, 314/316/318 angles,
# 360..376 view matrix rebuilt by the reference from the angle words as $ede4 does, 712 second-view flag, 626/618/622 second-view angle/position)
import random
random.seed(11)
ram = R.load_ram(R.SNAP_GAME2); A6 = F.A6
S = int.from_bytes(ram[A6+108:A6+112], 'big'); C = int.from_bytes(ram[A6+112:A6+116], 'big')
def sw(a):
    v = int.from_bytes(ram[a:a+2], 'big'); return v - 65536 if v >= 32768 else v
cases = []
for i in range(int(os.environ.get('NP', 16))):
    a1, a2, a3 = random.randrange(4096), random.randrange(4096), random.randrange(512)
    m = F.Mem(ram)
    for o, ia in ((458, 2 * a1), (462, 2 * a2), (466, 16 * a3)):
        m.sg(o, sw(S + ia)); m.sg(o + 2, sw(C + ia))
    F.ede4(m)
    pk = [('ww', A6 + o, m.u16(A6 + o)) for o in list(range(458, 470, 2)) + list(range(360, 378, 2))]
    pk += [('ww', A6 + 316, a2), ('ww', A6 + 302, random.randrange(-30000, 30000)), ('ww', A6 + 306, random.randrange(-30000, 30000)),
           ('ww', A6 + 626, random.randrange(4096)), ('ww', A6 + 618, random.randrange(-30000, 30000)), ('ww', A6 + 622, random.randrange(-30000, 30000))]
    if i % 3 == 0: pk.append(('wb', A6 + 712, 1))
    cases.append((dict(A6=A6, D0=random.randrange(1 << 32)), pk))
res = R.cc_jobs(R.SNAP_GAME2, [dict(addr=0xf336, presets=p, pokes=pk) for p, pk in cases], OUT, 'dustp', steps=600000)
ok = 0
for (p, pk), j in zip(cases, res):
    base = bytearray(ram)
    for k, a, v in pk:
        if k == 'ww': base[a] = v >> 8 & 255; base[a + 1] = v & 255
        else: base[a] = v
    m = F.Mem(base); F.dust(m, p['D0'])
    stack = (j['entrySP'] - 512, j['entrySP'] + 16)
    got = {a: nw for a, o, nw in j['mem'] if not (stack[0] <= a < stack[1])}
    ok += got == m.changes()
print(f'dust $f336 poked-camera (respawn path, both views) {ok}/{len(cases)}')
