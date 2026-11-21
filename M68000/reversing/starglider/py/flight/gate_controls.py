"""Gate: the per-frame key routine $d29a (held-key flags -> stick accumulators, with the silo launch) against
models.controls, on N random key-flag arrays, user-defined keys and accumulator values; and the RNG $f21e against
models.rng_f21e (the launch path calls it twice).

    cd M68000 && ATARI_NOTRACE=1 python3 reversing/starglider/py/flight/gate_controls.py [N] [--broken]

Prints `controls: MATCH k/N`. `--broken` swaps the accelerate step $10 -> $12 in the model: must fail."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flightlib import *
import models
from models import Mem, G

N = int([a for a in sys.argv[1:] if a.isdigit()][0]) if any(a.isdigit() for a in sys.argv[1:]) else 400
if '--broken' in sys.argv:
    import inspect
    src = inspect.getsource(models.controls).replace('add(SD, -0x10)', 'add(SD, -0x12)')
    ns = dict(vars(models)); exec(src, ns); models.controls = ns['controls']

s = StServer(ROOT)
s('load', snapshot=sg.SNAP_GAME1, disk=sg.DISK)
f0 = s('fork')['id']
rnd = random.Random(208)
GLEN = 0x1000
ok = 0; first_bad = None; modes = {}
for t in range(N):
    s('restore', id=f0)
    flags = bytearray(0x72)
    for sc in rnd.sample(range(0x72), rnd.choice([0, 1, 2, 3, 6])):
        flags[sc] = 1
    for sc in (57, 53, 75, 77, 72, 80, 45, 46, 39, 52):          # make the fixed keys common
        if rnd.random() < .15:
            flags[sc] = 1
    s('poke', addr=0, width=1, value=0) if False else None
    for i, v in enumerate(flags):
        if s.read(0xc34e + i, 1)[0] != v:
            s('poke', addr=0xc34e + i, width=1, value=v)
    for n in range(728, 734):
        s('poke', addr=G + n, width=1, value=rnd.choice([0, rnd.randrange(1, 0x72)]))
    s('poke', addr=0xc3de, width=1, value=0)
    s('poke', addr=G + 658, width=2, value=rnd.choice([0, 0x1e, 7]))
    s('poke', addr=G + 100, width=4, value=rnd.getrandbits(32))
    s('poke', addr=G + 92, width=4, value=rnd.getrandbits(32))
    for a in (models.SX, models.SY, models.SD):
        s('poke', addr=a, width=2, value=rnd.randint(-500, 500) & 0xffff)
    pre = {G: s.read(G, GLEN), 0xc34e: s.read(0xc34e, 0x92)}
    m = Mem(pre)
    mode = models.controls(m)
    s.call(0xd29a, a6=G)
    post = {G: s.read(G, GLEN), 0xc34e: s.read(0xc34e, 0x92)}
    exp = m.blob()
    bad = None
    for base in post:
        if exp[base] != post[base]:
            i = next(i for i in range(len(post[base])) if exp[base][i] != post[base][i])
            bad = (base + i, exp[base][i], post[base][i]); break
    modes[str(mode)] = modes.get(str(mode), 0) + 1
    if bad is None: ok += 1
    elif first_bad is None: first_bad = (t, bad)
print(f'controls: MATCH {ok}/{N}  (accelerate/decelerate/launch/none: {modes})')
if first_bad:
    t, (a, e, g) = first_bad
    print(f'first mismatch trial {t}: ${a:x} model {e:#04x} emulator {g:#04x}')
s.close()
