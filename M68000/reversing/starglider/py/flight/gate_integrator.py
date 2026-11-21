"""Gate: the flight integrator $12340 against models.flight_step on N randomised states (callcap-style: `call` of the
routine from the g_game1 snapshot through stserver, after poking random values into the fields it reads).

    cd M68000 && ATARI_NOTRACE=1 python3 reversing/starglider/py/flight/gate_integrator.py [N] [--broken]

Prints `integrator: MATCH k/N` (k trials whose whole globals block, the stick words and the button bytes equal the
model's prediction; a mismatch lists the first differing address). `--broken` changes one constant in the model (the
altitude ceiling $f8f8 -> $f8f0): the gate must then fail."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flightlib import *
import models
from models import Mem, G

N = int([a for a in sys.argv[1:] if a.isdigit()][0]) if any(a.isdigit() for a in sys.argv[1:]) else 400
BROKEN = '--broken' in sys.argv
if BROKEN:
    import re, inspect
    src = inspect.getsource(models.flight_step).replace('0xf8f8', '0xf8f0')
    ns = dict(vars(models)); exec(src, ns); models.flight_step = ns['flight_step']

s = StServer(ROOT)
s('load', snapshot=sg.SNAP_GAME1, disk=sg.DISK)
TAB = (0x1e000, 0x4000)
tab = s.read(*TAB)
f0 = s('fork')['id']
rnd = random.Random(1986)
GLEN = 0x1d00

def pw(a, v): s('poke', addr=a, width=2, value=v & 0xffff)
def pb(a, v): s('poke', addr=a, width=1, value=v & 0xff)

ok = 0; first_bad = None; branches = {}
for t in range(N):
    s('restore', id=f0)
    m712 = rnd.random() < 0.3; m714 = rnd.random() < 0.3
    vals = {
        302: rnd.getrandbits(16), 306: rnd.getrandbits(16), 316: rnd.getrandbits(16),
        304: rnd.choice([rnd.randint(-1800, -20), rnd.randint(-2200, 200), rnd.randint(-40, 0), rnd.randint(-1810, -1790)]),
        542: rnd.choice([rnd.randint(0, 479), rnd.randint(-300, 900)]),
        640: rnd.randint(-40, 40) if rnd.random() < .6 else 0,
        658: rnd.choice([0, 0x1e, 5]), 630: rnd.randint(2, 300), 628: rnd.getrandbits(16), 634: rnd.getrandbits(16),
        626: rnd.getrandbits(16), 618: rnd.getrandbits(16), 620: rnd.getrandbits(16), 622: rnd.getrandbits(16),
        516: rnd.getrandbits(16), 518: rnd.getrandbits(16), 570: rnd.getrandbits(16), 318: rnd.getrandbits(16)}
    for o, v in vals.items():
        pw(G + o, v)
    pb(G + 712, m712); pb(G + 714, m714); pb(G + 705, rnd.random() < .2); pb(G + 700, rnd.random() < .5)
    pw(models.SX, rnd.choice([rnd.randint(-800, 800), rnd.randint(-496, 496)]))
    pw(models.SY, rnd.choice([rnd.randint(-600, 600), rnd.randint(-48, 48)]))
    pw(models.SD, rnd.choice([rnd.randint(-700, 150), rnd.randint(-479, 0)]))
    pre = {G: s.read(G, GLEN), 0xc34e: s.read(0xc34e, 0x92), TAB[0]: tab}
    m = Mem(pre)
    calls = models.flight_step(m)
    s.call(0x12340, a6=G)
    post = {G: s.read(G, GLEN), 0xc34e: s.read(0xc34e, 0x92)}
    exp = m.blob()
    bad = None
    for base in post:
        if exp[base] != post[base]:
            i = next(i for i in range(len(post[base])) if exp[base][i] != post[base][i])
            bad = (base + i, exp[base][i], post[base][i])
            break
    key = ('712' if m712 else '') + ('714' if m714 else '')
    branches[key or 'flying'] = branches.get(key or 'flying', 0) + 1
    if bad is None:
        ok += 1
    elif first_bad is None:
        first_bad = (t, bad, vals, m712, m714)
print(f'integrator: MATCH {ok}/{N}  (branches {branches})')
if first_bad:
    t, (a, e, g), vals, m712, m714 = first_bad
    print(f'first mismatch trial {t}: ${a:x} (A6{a-G:+d}) model {e:#04x} emulator {g:#04x}; 712={m712} 714={m714}')
s.close()
