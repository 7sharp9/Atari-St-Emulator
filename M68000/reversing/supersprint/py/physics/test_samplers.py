"""Differential tests of the samplers / helpers against callcap, each on >= 200 distinct states:
   bda4 obstacle_test, b798 surface_sample, 14a4a car_window, b3fc crash_start, e5d6 car_reset, e8e6 carcar, e84c depth_sort
  natural: stop at every entry of the routine in natural play (distinct = distinct input tuples)
  fuzz:    randomise the inputs at one stop and callcap over and over
usage: test_samplers.py natural <nframes> <seed> | fuzz <nstates> <seed>"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from difflib_ss import *
import numpy as np

mode = sys.argv[1] if len(sys.argv) > 1 else 'natural'
N = int(sys.argv[2]) if len(sys.argv) > 2 else 100
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
rng = random.Random(seed)
h = Harness(sscfg.SNAP_RACE)
drv = Driver(h, seed)

ROUT = {
    'bda4': (0xbda4, True), 'b798': (0xb798, True), '14a4a': (0x14a4a, True), 'b3fc': (0xb3fc, True),
    'e5d6': (0xe5d6, True), 'e8e6': (0xe8e6, False), 'e84c': (0xe84c, False),
}
res = {k: [0, 0] for k in ROUT}
distinct = {k: set() for k in ROUT}
bad_all = []
cover = {}


def stack_car(regs):
    out, _ = h.cmd('m %x 2' % (regs['A7'] + 4))
    hb = [int(x, 16) for l in out if HEXLINE.match(l.strip()) for x in l.split()]
    return (hb[0] << 8) | hb[1]


def run_port(key, m, car):
    if key == 'bda4':
        return P.obstacle_test(m, car)
    if key == 'b798':
        P.surface_sample(m, car)
    elif key == '14a4a':
        P.car_window(m, car)
    elif key == 'b3fc':
        P.crash_start(m, car)
    elif key == 'e5d6':
        P.car_reset(m, car)
    elif key == 'e8e6':
        P.carcar(m)
    elif key == 'e84c':
        P.depth_sort(m)
    return None


def check(key, car):
    addr, has_arg = ROUT[key]
    ram = h.snap_ram()
    mapbase = ram.gl(-1910)
    mem, d, outc = h.callcap(addr, arg=car if has_arg else None)
    if d is None:
        print('callcap failed', key, outc)
        return
    m = P.Mem(ram.b)
    m0 = P.Mem(ram.b)
    c = car if car is not None else 0
    ret = run_port(key, m, c)
    bad = compare(ram.b, m, d, mapbase)
    if key == 'bda4':
        emu_ret = d['regN'][0] & 0xffffffff
        if emu_ret != ret:
            bad.append((0, ret, emu_ret))
        distinct[key].add((m0.a(P.X, c) & 15, m0.a(P.HEAD, c), bytes(ram.bytes(A4 + P.WIN, 48))))
    elif key == 'b798':
        distinct[key].add((m0.a(P.X, c), m0.a(P.Y, c), m0.a(P.HEAD, c), m0.au(P.F1, c), m0.au(P.F2, c)))
    elif key == '14a4a':
        distinct[key].add((m0.a(P.X, c) & 15, m0.a(P.Y, c), m0.a(P.HEAD, c), m0.au(P.F1, c) & 0x401, m0.au(P.ISDRONE, c) != 0))
    else:
        distinct[key].add(bytes(ram.bytes(A4 - 4050, 300)))
    res[key][1] += 1
    if not bad:
        res[key][0] += 1
    else:
        bad_all.append((key, c, [(field_name(a) if a > 100 else 'D0', pv, ev) for a, pv, ev in bad[:8]],
                        dict(x=m0.a(P.X, c), y=m0.a(P.Y, c), h=m0.a(P.HEAD, c), f1=hex(m0.au(P.F1, c)), f2=hex(m0.au(P.F2, c)), spd=m0.a(P.SPD, c))))


def events(key, dd):
    if not dd:
        return
    ed = {ad: nw for ad, old, nw in dd['mem']}


if mode == 'natural':
    for i in range(N):
        drv.poke_input()
        for key in ('e8e6', 'e84c'):
            pass
        for key in ('bda4', 'b798'):
            for _ in range(4):
                r = h.run_to(ROUT[key][0], 1, 600000)
                if r:
                    check(key, stack_car(r))
        for key in ('14a4a',):
            r = h.run_to(0x14a4a, 1, 600000)
            if r:
                check(key, stack_car(r))
        r = h.run_to(0xe8e6, 1, 600000)
        if r:
            check('e8e6', None)
        r = h.run_to(0xe84c, 1, 600000)
        if r:
            check('e84c', None)
else:
    for _ in range(25):
        drv.poke_input()
        h.run_to(0xdf18, 1)
    base = h.snap_ram()
    raw = np.frombuffer(base.bytes(base.gl(-94) + 8000, 8000), dtype=np.uint8).reshape(200, 40)
    road = np.unpackbits(raw, axis=1) == 0
    mapbase = base.gl(-1910)

    def pos():
        while True:
            x, y = rng.randint(0, 319), rng.randint(0, 199)
            if rng.random() < 0.7 and not road[y, x]:
                continue
            return x, y

    cells = [0x00, 0x80, 0x04, 0x08, 0x10, 0x20, 0x24, 0x18, 0x0c, 0x14, 0x1c, 0x01, 0x05, 0x09, 0x0d, 0x11, 0x15, 0x19, 0x1d, 0x21,
             0x02, 0x06, 0x0a, 0x0e, 0x12, 0x03, 0x07, 0x0b, 0x0f, 0x13, 0x17, 0x1f, 0x8a, 0x81, 0x85, 0x86]
    for it in range(N):
        xs, ys = zip(*(pos() for _ in range(4)))
        car = rng.randrange(4)
        hd = [rng.randrange(16) for _ in range(4)]
        poke_arr(h, P.X, xs); poke_arr(h, P.Y, ys); poke_arr(h, P.HEAD, hd)
        poke_arr(h, P.SPD, [rng.choice([0, 5, 15, 60, 110, rng.randint(0, 120)]) for _ in range(4)])
        poke_arr(h, P.QX, [8 * v for v in xs]); poke_arr(h, P.QY, [8 * v for v in ys])
        poke_arr(h, P.SAFEX, [rng.randint(0, 2500) for _ in range(4)]); poke_arr(h, P.SAFEY, [rng.randint(0, 1590) for _ in range(4)])
        poke_arr(h, P.SAFEH, [rng.randrange(16) for _ in range(4)])
        poke_arr(h, P.F1, [rng.choice([0, 0, 0, 0x400, 0x1, 0x41, 0x2000, 0x100, 0x8001, 0x10, 0x20]) for _ in range(4)])
        poke_arr(h, P.F2, [rng.choice([0, 0, 0x80, 0x8000, 0x100, 0x1000, 0x2, 0x4c0, 0x40, 0x200, 0x400, 0x800, 0x10, 0x20, 0x08]) for _ in range(4)])
        poke_arr(h, P.SECTOR, [rng.choice([0, 1, 2, 3]) for _ in range(4)])
        poke_arr(h, P.LAPS, [rng.choice([0, 1, 2, 3, 4, 7]) for _ in range(4)])
        poke_arr(h, P.ISDRONE, [rng.choice([0, 1, 1]) for _ in range(4)])
        poke_arr(h, P.FLAG, [rng.choice([0, 0, 1, 2]) for _ in range(4)])
        poke_arr(h, P.STUN, [rng.choice([0, 1, 7]) for _ in range(4)])
        for k in range(4):
            poke_arr(h, -1774 + 8 * 0, [0, 0, 0, 0]) if k == 0 else None
        h.cmd('w %x %08x' % (A4 - 1856, rng.choice([0, 0, 0x00020000])))   # pickup latch
        h.cmd('w %x %08x' % (A4 - 1846, rng.choice([0, 0, 0x00030000])))
        h.cmd('w %x %08x' % (A4 - 1896, rng.choice([0, 0, 0xffff0000])))   # pickup-vehicle animation state (b3fc)
        # surface map: sprinkle random cell values around the car probe points
        for _ in range(6):
            c = rng.randrange(1000)
            v = rng.choice(cells)
            h.cmd('w %x %02x%02x%02x%02x' % (mapbase + (c & ~3), v, rng.choice(cells), rng.choice(cells), v))
        # collision window: random sparse rows (for bda4), rebuilt for the car by 14a4a in the 14a4a test
        for r in range(12):
            h.cmd('w %x %08x' % (A4 - 3682 + 4 * r, rng.choice([0, 0, 0, rng.getrandbits(32), 1 << rng.randrange(32), rng.getrandbits(32) & rng.getrandbits(32)])))
        for key in ('bda4', 'b798', '14a4a', 'b3fc', 'e5d6'):
            check(key, car)
        check('e8e6', None)
        check('e84c', None)

print(mode)
print('b798 cells executed (kind, payload): count', dict(sorted(P.COV.items())))
for k in ROUT:
    print('%-6s matching %d/%d   distinct input states %d' % (k, res[k][0], res[k][1], len(distinct[k])))
for b in bad_all[:10]:
    print(b)
h.close()
