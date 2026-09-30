"""Fuzz differential test of $df18: poke randomised car state at a df18 entry, compare ssport.frame against callcap.
usage: fuzz_df18.py [nstates] [seed]"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from difflib_ss import *
if os.environ.get('SS_MUTATE') == 'floor':      # negative control: floor division instead of DIVS truncation must be caught
    P.divs = lambda a, b: a // b
import numpy as np

N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
seed = int(sys.argv[2]) if len(sys.argv) > 2 else 7
rng = random.Random(seed)
h = Harness(sscfg.SNAP_RACE)
for _ in range(20):
    h.run_to(0xdf18, 1)
base = h.snap_ram()
planes = None
raw = np.frombuffer(base.bytes(base.gl(-94) + 8000, 8000), dtype=np.uint8).reshape(200, 40)
road = np.unpackbits(raw, axis=1) == 0       # plane 1 == 0 : drivable

def pos():
    for _ in range(50):
        x, y = rng.randint(2, 300), rng.randint(2, 184)
        if rng.random() < 0.75 and not road[min(y, 199), min(x, 319)]:
            continue
        return x, y
    return x, y

ok = 0
bad_states = []
cover = {}
NAMES = {P.FLAG: 'FLAG', P.STUN: 'STUN', P.BUMP: 'BUMP', P.F1: 'F1', P.F2: 'F2', P.GATE: 'GATE', P.SECTOR: 'SECTOR', P.LAPS: 'LAPS',
         P.SAFEX: 'SAFE', P.SPD: 'SPD', P.TGT: 'TGT', P.TURN: 'TURN', P.VX: 'VX', P.WRENCH: 'WRENCH', P.HEAD: 'HEAD'}
for i in range(N):
    xs, ys = zip(*(pos() for _ in range(4)))
    if rng.random() < 0.3:      # force a pair close together
        xs = list(xs); ys = list(ys)
        xs[1] = xs[0] + rng.randint(-8, 8); ys[1] = ys[0] + rng.randint(-8, 8)
    if rng.random() < 0.1:      # boundary
        xs = list(xs); ys = list(ys)
        c = rng.randrange(4)
        xs[c], ys[c] = rng.choice([(1, 60), (0, 70), (301, 50), (305, 60), (100, 1), (120, 0), (100, 186), (150, 190)])
    hd = [rng.randrange(16) for _ in range(4)]
    cap = base.arr(P.CAP)
    spd = [rng.choice([0, 5, 15, 60, cap[c], cap[c], cap[c] + 3, rng.randint(0, 120)]) for c in range(4)]
    poke_arr(h, P.X, xs); poke_arr(h, P.Y, ys); poke_arr(h, P.HEAD, hd); poke_arr(h, P.TGT, hd)
    poke_arr(h, P.SPD, spd)
    poke_arr(h, P.QX, [8 * v for v in xs]); poke_arr(h, P.QY, [8 * v for v in ys])
    poke_arr(h, P.PX, [8 * v + rng.randint(-3, 3) for v in xs]); poke_arr(h, P.PY, [8 * v + rng.randint(-3, 3) for v in ys])
    f1 = []
    for c in range(4):
        v = 0
        r = rng.random()
        if r < 0.15: v |= 0x400
        if rng.random() < 0.1: v |= 0x1
        if rng.random() < 0.1: v |= 0x40
        if rng.random() < 0.1: v |= 0x2000
        if rng.random() < 0.1: v |= 0x2 | (rng.randrange(4) << 2)
        f1.append(v)
    poke_arr(h, P.F1, f1)
    poke_arr(h, P.FLAG, [rng.choice([0, 0, 0, 0, 1, 2]) for _ in range(4)])
    poke_arr(h, P.STUN, [rng.choice([0, 0, 0, 1, 2, 7]) for _ in range(4)])
    poke_arr(h, P.BUMP, [rng.choice([0, 0, 0, 1, 5]) for _ in range(4)])
    poke_arr(h, P.TURN, [rng.choice([0, 0, 0, 3, 32]) for _ in range(4)])
    poke_arr(h, P.ISDRONE, [rng.choice([0, 1, 1]) for _ in range(4)])
    poke_arr(h, P.F2, [rng.choice([0, 0, 0x80, 0x8000, 0x100, 0x1000, 0x2, 0x4c0]) for _ in range(4)])
    poke_arr(h, P.SECTOR, [rng.choice([0, 1, 2, 3]) for _ in range(4)])
    h.cmd('w %x %08x' % (A4 - 8068, (rng.choice([0, 1]) << 16) | (base.gl(-8068) & 0xffff)))   # sound on/off
    # roaming hazard object ($ea56): active half the time, placed near a random car
    c0 = rng.randrange(4)
    h.cmd('w %x %04x%04x' % (A4 - 1776, rng.choice([0, 1]), 0))
    h.cmd('w %x %04x%04x' % (A4 - 1782, (ys[c0] - 12 + rng.randint(-9, 9)) & 0xffff, (xs[c0] + rng.randint(-8, 8)) & 0xffff))   # -1782 (y), -1780 (x)
    ram = h.snap_ram()
    mapbase = ram.gl(-1910)
    mem, d, outc = h.callcap(0xdf18)
    if d is None:
        print('callcap failed', outc); continue
    m = P.Mem(ram.b)
    P.frame(m)
    bad = compare(ram.b, m, d, mapbase)
    ed = emu_delta(d, mapbase)
    touched = set()
    for a in ed:
        if ed[a] != ram.b[a]:
            off = a - A4
            for b0, nm in NAMES.items():
                if b0 <= off < b0 + 8:
                    touched.add(nm)
            if mapbase <= a < mapbase + 1000: touched.add('MAPCELL')
            if off in (-4086, -4085): touched.add('-4086')
    for t in touched: cover[t] = cover.get(t, 0) + 1
    if not bad:
        ok += 1
    else:
        m0 = P.Mem(ram.b)
        bad_states.append((i, bad, dict(haz=(m0.g(-1776), m0.g(-1780), m0.g(-1782)), cars=[(m0.a(P.X, c), m0.a(P.Y, c), hex(m0.au(P.F1, c)), m0.a(P.TURN, c), m0.a(P.FLAG, c)) for c in range(4)])))
print('coverage (states in which the emulator changed the field):', dict(sorted(cover.items())))
print('fuzz df18 states matching: %d/%d' % (ok, N))
for i, bad, info in bad_states[:6]:
    print('state', i, [(field_name(a), pv, ev) for a, pv, ev in bad[:10]], info)
h.close()
