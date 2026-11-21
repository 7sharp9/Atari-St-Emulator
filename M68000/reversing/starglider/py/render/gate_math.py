"""Gate for the rotation/transform routines $ede4 (view matrix), $eca0 (object matrix + cache), $ec1e (view transform), $eb8a (model
transform) and $eeac (cached vertex transform) against rref.py.

    python3 gate_math.py [--control]      # --control: one wrong constant in the reference (a Q14 shift of 15 instead of 14 for matvec)
Method: start snapshot g_game1; every job pokes its inputs (labelled POKE below), `callcap`s the routine with A6=$5bf00 and compares the full
memory delta (every changed byte outside the stack) and the exit D1..D3 with the reference, which is handed only the snapshot RAM and the pokes.
Expected output: one line per routine `routine matched/total`, all equal."""
import os, sys, random
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import rcommon as R
import rref as F
A6 = F.A6
CONTROL = '--control' in sys.argv
if CONTROL:
    F.mulq = lambda a, b: F.s16(((F.s16(a) * F.s16(b) << 1) & 0xFFFFFFFF) >> 16)   # wrong shift
ram = R.load_ram(R.SNAP_GAME1)
random.seed(1986)
OUT = R.WORK + '/render/caps'

def delta_of(res):
    stack = (res['entrySP'] - 512, res['entrySP'] + 16)
    return {a: n for a, o, n in res['mem'] if not (stack[0] <= a < stack[1])}

def run(name, addr, mk, ref):
    jobs, pokesets, ins = [], [], []
    for i in range(int(os.environ.get('N', 40))):
        pokes, pre, info = mk(i)
        jobs.append(dict(addr=addr, presets=dict(A6=A6, **pre), pokes=pokes))
        ins.append((pokes, pre, info))
    res = R.cc_jobs(R.SNAP_GAME1, jobs, OUT, 'gm_' + name)
    ok = 0
    for r, (pokes, pre, info) in zip(res, ins):
        mem = F.Mem(ram)
        for kind, a, v in pokes:
            if kind == 'ww': mem.ww(a, v)
            elif kind == 'wb': mem.wb(a, v)
        # pokes are inputs, not outputs: re-base the model RAM on them
        base = bytearray(ram)
        for a, v in mem.w.items(): base[a] = v
        mem = F.Mem(base)
        regs = ref(mem, pre, info)
        want = mem.changes()
        got = delta_of(r)
        good = want == got
        if regs is not None:
            for k, v in regs.items():
                good &= (r['regN'][int(k[1])] & 0xFFFF) == (v & 0xFFFF)
        ok += good
        if not good and ok < 3 and False:
            print('MISS', info, sorted(want.items())[:6], sorted(got.items())[:6])
    print(f'{name:10s} {ok}/{len(ins)}')
    return ok == len(ins)

def rnd_trig():
    S = int.from_bytes(ram[A6+108:A6+112], 'big'); C = int.from_bytes(ram[A6+112:A6+116], 'big')
    def sw(a):
        v = int.from_bytes(ram[a:a+2], 'big'); return v - 65536 if v >= 32768 else v
    a = random.randrange(0, 4096)
    return sw(S + 2 * a), sw(C + 2 * a), a

def mk_ede4(i):
    pokes, info = [], []
    for o in (458, 462, 466):
        s, c, a = rnd_trig()
        pokes += [('ww', A6 + o, s), ('ww', A6 + o + 2, c)]
    return pokes, {}, i
def ref_ede4(m, pre, info):
    F.ede4(m); return None

def mk_eca0(i):
    pokes = [('ww', A6 + 378, random.randrange(0, 4096)), ('ww', A6 + 380, random.randrange(0, 4096)), ('ww', A6 + 382, random.randrange(0, 512))]
    if i % 5 == 0:   # cached: object angles equal the cache -> no work
        pokes += [('ww', A6 + 384, pokes[0][2]), ('ww', A6 + 386, pokes[1][2]), ('ww', A6 + 388, pokes[2][2])]
    return pokes, {}, i
def ref_eca0(m, pre, info):
    F.eca0(m); return None

def rand_matrix_pokes(base):
    # a real rotation (built by the reference from random angles) so the entries have realistic ranges
    mm = F.Mem(ram)
    ang = [random.randrange(0, 4096), random.randrange(0, 4096), random.randrange(0, 512)]
    S = int.from_bytes(ram[A6+108:A6+112], 'big'); C = int.from_bytes(ram[A6+112:A6+116], 'big')
    def sw(a):
        v = int.from_bytes(ram[a:a+2], 'big'); return v - 65536 if v >= 32768 else v
    s1, c1 = sw(S + 2 * ang[0]), sw(C + 2 * ang[0]); s2, c2 = sw(S + 2 * ang[1]), sw(C + 2 * ang[1])
    s3, c3 = sw(S + 16 * ang[2]), sw(C + 16 * ang[2])
    F.build_matrix(mm, base, s1, c1, s2, c2, s3, c3)
    return [('ww', A6 + base + 2 * k, mm.u16(A6 + base + 2 * k)) for k in range(9)]

def mk_ec1e(i):
    v = [random.randrange(-32768, 32768) if i % 3 == 0 else random.randrange(-3000, 3000) for _ in range(3)]
    return rand_matrix_pokes(360), dict(D1=v[0], D2=v[1], D3=v[2]), v
def ref_ec1e(m, pre, info):
    x, y, z = F.ec1e(m, *info); return dict(D1=x, D2=y, D3=z)

def mk_eb8a(i):
    v = [random.randrange(-32768, 32768) if i % 3 == 0 else random.randrange(-3000, 3000) for _ in range(3)]
    pokes = rand_matrix_pokes(342) + [('ww', A6 + 404 + 2 * k, random.randrange(-4000, 4000)) for k in range(3)]
    return pokes, dict(D1=v[0], D2=v[1], D3=v[2]), v
def ref_eb8a(m, pre, info):
    x, y, z = F.eb8a(m, *info); return dict(D1=x, D2=y, D3=z)

def mk_eeac(i):
    # vertex table at 16(A6) (model 1's verts live in RAM: use A1 = $15ada-based data), cache A0 = 760(A6), flags A2 = 1800(A6)
    nv = 22; A1 = 0x15caa + 8272
    idx = random.randrange(0, nv)
    hit = i % 4 == 0
    pokes = rand_matrix_pokes(342) + [('ww', A6 + 404 + 2 * k, random.randrange(-4000, 4000)) for k in range(3)]
    pokes += [('wb', A6 + 1800 + idx, 1 if hit else random.choice([0, 0xFF]))]
    if hit: pokes += [('ww', A6 + 760 + idx * 8 + 2 * k, random.randrange(-3000, 3000)) for k in range(3)]
    return pokes, dict(D1=idx, D4=idx * 8, D5=random.randrange(0, 65536), A0=A6 + 760, A1=A1, A2=A6 + 1800), idx
def ref_eeac(m, pre, info):
    x, y, z = F.eeac(m, pre['D1'], pre['D4'], pre['D5'], pre['A0'], pre['A1'], pre['A2']); return dict(D1=x, D2=y, D3=z)

ok = True
ok &= run('ede4', 0xede4, mk_ede4, ref_ede4)
ok &= run('eca0', 0xeca0, mk_eca0, ref_eca0)
ok &= run('ec1e', 0xec1e, mk_ec1e, ref_ec1e)
ok &= run('eb8a', 0xeb8a, mk_eb8a, ref_eb8a)
ok &= run('eeac', 0xeeac, mk_eeac, ref_eeac)
print('ALL PASS' if ok else 'FAIL')
