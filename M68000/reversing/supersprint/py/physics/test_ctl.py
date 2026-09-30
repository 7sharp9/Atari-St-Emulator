"""Differential test of the two control routines: $d4fa (human/joystick car) and $eaea (drone car).
  natural: stop at every entry of the routine during natural play (driver steers with pseudo-random joystick bytes)
  fuzz:    stop once at an entry, then poke randomised state over and over (no stepping) and compare port vs callcap
usage: test_ctl.py natural <nframes> <seed>   |   test_ctl.py fuzz <nstates> <seed>"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from difflib_ss import *
if os.environ.get('SS_MUTATE') == 'floor':      # negative control: floor division instead of DIVS truncation must be caught
    P.divs = lambda a, b: a // b

mode = sys.argv[1] if len(sys.argv) > 1 else 'natural'
N = int(sys.argv[2]) if len(sys.argv) > 2 else 100
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
rng = random.Random(seed)
h = Harness(sscfg.SNAP_RACE)
drv = Driver(h, seed)
res = {'d4fa': [0, 0], 'eaea': [0, 0]}
cover = {'d4fa': {}, 'eaea': {}}
bad_all = []
NAMES = {P.SPD: 'SPD', P.TGT: 'TGT', P.TURN: 'TURN', P.HEAD: 'HEAD', P.WP: 'WP', P.STUN: 'STUN', P.TURNCNT: 'TURNCNT', P.LAPPOS: 'LAPPOS',
         P.FLAG: 'FLAG', P.F1: 'F1', P.QX: 'QX', P.VX: 'VX', P.AX: 'AX', P.WPX: 'WPX', P.RX: 'RX', P.X: 'X', P.SAFEX: 'SAFE'}


def stack_car(regs):
    out, _ = h.cmd('m %x 2' % (regs['A7'] + 4))
    hb = [int(x, 16) for l in out if HEXLINE.match(l.strip()) for x in l.split()]
    return (hb[0] << 8) | hb[1]


def check(addr, key, car):
    ram = h.snap_ram()
    mapbase = ram.gl(-1910)
    mem, d, outc = h.callcap(addr, arg=car)
    if d is None:
        print('callcap failed', outc)
        return
    m = P.Mem(ram.b)
    if key == 'd4fa':
        P.human_step(m, car, P.read_input(m, car))
    else:
        P.drone_step(m, car)
    bad = compare(ram.b, m, d, mapbase)
    ed = emu_delta(d, mapbase)
    seen = set()
    for a in ed:
        if ed[a] != ram.b[a]:
            off = a - A4
            for b0, nm in NAMES.items():
                if b0 + 2 * car <= off < b0 + 2 * car + 2:
                    seen.add(nm)
    for nm in seen:
        cover[key][nm] = cover[key].get(nm, 0) + 1
    res[key][1] += 1
    if not bad:
        res[key][0] += 1
    else:
        bad_all.append((key, car, [(field_name(a), pv, ev) for a, pv, ev in bad[:8]]))


def randomise(key, car):
    poke_arr(h, P.HEAD, [rng.randrange(16) for _ in range(4)])
    poke_arr(h, P.TGT, [rng.randrange(16) for _ in range(4)])
    poke_arr(h, P.SPD, [rng.choice([0, 3, 10, 30, 59, 60, 100, 109, 110, 120, rng.randint(-5, 130)]) for _ in range(4)])
    poke_arr(h, P.CAP, [rng.choice([60, 110, 68, 72, 40, 127]) for _ in range(4)])
    poke_arr(h, P.TURN, [rng.choice([0, 0, 0, 1, 2, 3, 32, 31, 17]) for _ in range(4)])
    poke_arr(h, P.STUN, [rng.choice([0, 0, 0, 1, 5, 9]) for _ in range(4)])
    poke_arr(h, P.TURNCNT, [rng.randint(-2, 7) for _ in range(4)])
    poke_arr(h, P.F1, [rng.choice([0, 0, 0x40, 0x2000, 0x400, 0x1, 0x800 | 0x400, 0x440, 0x1400, 0x2040]) for _ in range(4)])
    poke_arr(h, P.LAPPOS, [rng.choice([0, 0, 1, 2, 3, 8, 16, 17, 18, 19]) for _ in range(4)])
    poke_arr(h, P.AX, [rng.randint(-400, 400) for _ in range(4)])
    poke_arr(h, P.AY, [rng.randint(-400, 400) for _ in range(4)])
    poke_arr(h, P.VX, [rng.randint(-600, 600) for _ in range(4)])
    poke_arr(h, P.VY, [rng.randint(-600, 600) for _ in range(4)])
    poke_arr(h, P.RX, [rng.randint(-100, 100) for _ in range(4)])
    poke_arr(h, P.QX, [rng.randint(200, 2400) for _ in range(4)])
    poke_arr(h, P.QY, [rng.randint(100, 1500) for _ in range(4)])
    poke_arr(h, P.MINSPD, [rng.choice([0, 20, 40, 60]) for _ in range(4)])
    poke_arr(h, P.MAXSPD, [rng.choice([30, 60, 90, 127]) for _ in range(4)])
    h.cmd('w %x %04x%04x' % (A4 - 8478, rng.randrange(7), rng.randrange(7)))   # frame-mod-7 counter (+ next word)
    if key == 'eaea':
        poke_arr(h, P.WP, [rng.choice([0, 2, 4, 34, 36, 60, 62, 64, 66, 82, 10, 16, 19, 48]) for _ in range(4)])
        poke_arr(h, P.WPX, [rng.randint(100, 2300) for _ in range(4)])
        poke_arr(h, P.WPY, [rng.randint(100, 1400) for _ in range(4)])
    else:
        ch = rng.choice([0, 2, 2, 3])
        poke_arr(h, -4810, [ch] * 4)
        h.cmd('w %x %02x%02x%02x%02x' % (A4 - 4804, rng.choice([0, 0x80, 0x84, 0x88, 0x04, 0x08, 0x81, 0x82, 0x8c, 0x90, 0x48]),
                                         rng.choice([0, 0x80, 0x84, 0x88, 0x08]), 0, 0))
        for off in (28, 32, 36, 40, 44, 52, 56):
            h.cmd('w %x %08x' % (A4 - 4802 + off, rng.getrandbits(32) & 0x01010101 if rng.random() < 0.5 else 0))


if mode == 'natural':
    for i in range(N):
        drv.poke_input()
        r = h.run_to(0xd4fa, 1, 600000)
        if r:
            check(0xd4fa, 'd4fa', stack_car(r))
        for _ in range(3):
            r = h.run_to(0xeaea, 1, 600000)
            if r:
                check(0xeaea, 'eaea', stack_car(r))
else:
    for key, addr in (('d4fa', 0xd4fa), ('eaea', 0xeaea)):
        for _ in range(3):
            drv.poke_input()
            r = h.run_to(addr, 1, 600000)
        car = stack_car(r)
        for i in range(N):
            randomise(key, car)
            check(addr, key, car)
print(mode, {k: '%d/%d' % tuple(v) for k, v in res.items()})
print('emulator changed (state-count per field):', cover)
for b in bad_all[:8]:
    print(b)
h.close()
