"""Probe: the model viewer's key handler $e944 (called from the viewer loop $dd7a at $ddfc). Each leg restores the
same gallery state, taps one key, runs the same budget, and reads the fields $e944 writes. Leg 'none' is the control.

    cd M68000 && python3 reversing/starglider/py/curios/gallery_keys.py
"""
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, '..', 'flight'))
from flightlib import *
OUTDIR = sg.work('curios'); os.makedirs(OUTDIR, exist_ok=True)

FIELDS = dict(model=(504, 2), spinx=(486, 2), spiny=(488, 2), spinz=(490, 2), camx=(404, 2), camy=(406, 2),
              dist=(408, 2), step=(716, 1), stereo=(718, 1), allfaces=(701, 1), eye=(648, 2))
def snap(dr):
    return {k: (dr.s16(G + o) if n == 2 else dr.u8(G + o)) for k, (o, n) in FIELDS.items()}

def tap(dr, sc, hold=150000, gap=150000):
    if sc is None: dr.step(hold + gap); return
    dr.hold(sd.Key(sc), steps=hold); dr.step(gap)

dr = sd.Drive(ROOT, journal=os.path.join(OUTDIR, 'j.jsonl'), period=POLL)
dr.load(sg.SNAP_TITLE, sg.DISK)
dr.poke(G + 717, 1, 0xff)                       # practice flag (the JS ARG toggle, gate_cheat.py)
tap(dr, 0x22, hold=200000, gap=1500000)         # G -> gallery
r = dr.rpc('regs'); r = r[0] if isinstance(r, list) else r
print('in gallery, PC', r['pc'], snap(dr))
base = dr.fork()
dr.rpc('render', path=os.path.join(OUTDIR, 'base.png'))

LEGS = [('none', None), ('.', 0x34), (',', 0x33), ('X', 0x2d), ('S', 0x1f), ('Y', 0x15), ('T', 0x14), ('Z', 0x2c),
        ('A', 0x1e), ('L', 0x26), ('K', 0x25), ('6', 0x07), ('4', 0x05), ('2', 0x03), ('8', 0x09), ('R', 0x13),
        ('E', 0x12), ('3', 0x04), ('H', 0x23), ('P', 0x19)]
b0 = snap(dr)
for name, sc in LEGS:
    dr.restore(base)
    tap(dr, sc)
    s = snap(dr)
    d = {k: f'{b0[k]}->{v}' for k, v in s.items() if v != b0[k]}
    print(f'{name:5s}', d if d else 'no change')
    if name in ('H', '3', 'none'):
        dr.step(4 * POLL)
        dr.rpc('render', path=os.path.join(OUTDIR, f'key_{ {"H":"H","3":"3","none":"none"}[name]}.png'))

# walk every model with '.' from model 0 and render each
dr.restore(base)
dr.poke(G + 486, 2, 0); dr.poke(G + 488, 2, 0); dr.poke(G + 490, 2, 0)
dr.poke(G + 504, 2, 1)                          # start the walk at model 1 ('.' then steps it)
for i in range(0, 30):
    m = dr.s16(G + 504)
    dr.step(3 * POLL)
    dr.rpc('render', path=os.path.join(OUTDIR, f'model_{m:02d}.png'))
    tap(dr, 0x34)
    if dr.s16(G + 504) == m:
        print('model stops at', m); break
dr.close()
