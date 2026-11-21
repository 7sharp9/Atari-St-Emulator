"""Gate: the IKBD/ACIA interrupt handler $b7be (vector $118, re-pointed after every byte) against models.isr, on random
byte streams fed through the ACIA with the main loop replaced by `bra *` at $900 (so only the interrupt handlers run).

    cd M68000 && ATARI_NOTRACE=1 python3 reversing/starglider/py/flight/gate_isr.py [TRIALS] [--broken]

Per trial: 24 random IKBD bytes (key make/break codes and $f8-$ff packet headers with their two data bytes), one `kbd`
call per byte and 3,000 steps after each; then the key-flag array, the stick words, the button bytes, $c3de and the
vector are compared with the model's. Prints `isr: MATCH k/TRIALS (b bytes)`. `--broken` makes the model send the right
button's vertical motion to the wrong accumulator: must fail."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flightlib import *
import models
from models import Mem

N = int([a for a in sys.argv[1:] if a.isdigit()][0]) if any(a.isdigit() for a in sys.argv[1:]) else 30
if '--broken' in sys.argv:
    import inspect
    src = inspect.getsource(models.isr).replace('m.setw(SD, m.w(SD) + s8(b))', 'm.setw(SY, m.w(SY) + s8(b))')
    ns = dict(vars(models)); exec(src, ns); models.isr = ns['isr']

s = StServer(ROOT)
s('load', snapshot=sg.SNAP_GAME1, disk=sg.DISK)
s('poke', addr=0x900, width=2, value=0x60fe)
s('set_reg', name='pc', value=0x900); s('set_reg', name='sr', value=0x2000)
s.step = None
s('step', n=20000)
f0 = s('fork')['id']
rnd = random.Random(118)
REG = (0xc34e, 0x92)
ok = 0; nbytes = 0; first_bad = None
for t in range(N):
    s('restore', id=f0)
    s('poke', addr=0x118, width=4, value=0xb7be)
    s('poke', addr=0xc3de, width=1, value=0)
    m = Mem({REG[0]: s.read(*REG)})
    vec = 0xb7be
    stream = []
    while len(stream) < 24:
        r = rnd.random()
        if r < .35:   stream += [rnd.randrange(1, 0x72) | rnd.choice([0, 0x80])]
        elif r < .45: stream += [rnd.choice([0x74, 0xf4, 0x75, 0xf5, 0x39, 0xb9])]
        else:         stream += [rnd.randrange(0xf8, 0x100), rnd.randrange(256), rnd.randrange(256)]
    for b in stream:
        s('kbd', bytes=[f'{b:02x}'])
        s('step', n=3000)
        vec = models.isr(m, vec, b)
        nbytes += 1
    post = s.read(*REG); exp = m.blob()[REG[0]]
    live_vec = int.from_bytes(s.read(0x118, 4), 'big')
    bad = next(((REG[0] + i, exp[i], post[i]) for i in range(len(post)) if exp[i] != post[i]), None)
    if bad is None and live_vec != vec:
        bad = (0x118, vec, live_vec)
    if bad is None: ok += 1
    elif first_bad is None: first_bad = (t, bad)
print(f'isr: MATCH {ok}/{N}  ({nbytes} bytes)')
if first_bad:
    print(f'first mismatch trial {first_bad[0]}: ${first_bad[1][0]:x} model {first_bad[1][1]:#x} emulator {first_bad[1][2]:#x}')
s.close()
