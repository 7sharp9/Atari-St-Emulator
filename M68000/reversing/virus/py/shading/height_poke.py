"""Gate: the landscape tile colour has no slope term.  From one snapshot, `callcap 24098` (the grid builder and painter) is run
for a control and for three POKED height-map bytes (labelled), and the type words ($275c4.., the tile colour indices the draw
loop $243b6 passes in A0) and the drawn screen (the draw buffer at $27062, 4 planes, 320x184) are compared.
  POKE A   wb 42b61 f3   cell x=$900 z=$100 byte d3 -> f3 (+32 steps = +256 height units, SAME type band: byte & 3 equal)
  POKE B   wb 42b61 d4   byte d3 -> d4 (type band changes: the positive control, the type word and the screen colour must change)
Expected: A: type words 143/143 equal, every changed pixel (hundreds) takes a colour that is a tile colour or 0; B: 142/143 type
words, and the changed tile's colour on screen goes 9 -> 10.  The repeat control (no poke twice) must give 58880/58880 pixels.
Usage: height_poke.py [snap]   (default $W/drive/g_game2.snap; the cell is outside the launch pad, column x=$900)"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
snap = sys.argv[1] if len(sys.argv) > 1 else work('drive', 'g_game2.snap')
G = gate_dir(); CELL = 0x42a58 + 9 + 0x100   # (x>>8) + (z & $ff00) as $24754
base = load_ram(snap)
orig = base[CELL]
cc = lambda n: os.path.join(G, f'cc_{n}.json')
steps = ['callcap 24098 20000000 %s' % cc('control'),
         'wb %x %02x' % (CELL, orig + 32), 'callcap 24098 20000000 %s' % cc('plus32'),
         'wb %x %02x' % (CELL, orig + 1), 'callcap 24098 20000000 %s' % cc('plus1'),
         'wb %x %02x' % (CELL, orig), 'callcap 24098 20000000 %s' % cc('control_b')]
repl(snap, steps, os.path.join(G, 'height_poke_repl.txt'))
scr = struct.unpack('>L', base[0x27062:0x27066])[0]
def pix(r, x, y):
    o = scr + y * 160 + (x >> 4) * 8; bit = 15 - (x & 15); v = 0
    for p in range(4): v |= ((struct.unpack('>H', r[o + 2 * p:o + 2 * p + 2])[0] >> bit) & 1) << p
    return v
W2 = lambda r, a: struct.unpack('>H', r[a:a + 2])[0]
types = lambda r: [W2(r, 0x275c4 + 2 * i) for i in range(11 * 13)]
A = apply_delta(base, cc('control'))
ta = types(A); tset = {t for i, t in enumerate(ta) if i % 13 < 12} | {0}
for name, label in (('control_b', 'control: poke restored, no change'), ('plus32', 'POKE A (+32 steps, same type band)'),
                    ('plus1', 'POKE B (+1 step, type band changes; positive control)')):
    B = apply_delta(base, cc(name)); tb = types(B)
    teq = sum(x == y for x, y in zip(ta, tb))
    chg = [(x, y, pix(A, x, y), pix(B, x, y)) for y in range(184) for x in range(320) if pix(A, x, y) != pix(B, x, y)]
    inset = sum(t[3] in tset for t in chg)
    pairs = {}
    for t in chg: pairs[(t[2], t[3])] = pairs.get((t[2], t[3]), 0) + 1
    print('%s: type words equal %d/%d; screen pixels equal %d/58880; changed pixels with a tile colour or 0: %d/%d' %
          (label, teq, len(ta), 58880 - len(chg), inset, len(chg)))
    if name == 'plus1': print('  POKE B changed-pixel colour pairs (old,new): %s' % sorted(pairs.items(), key=lambda kv: -kv[1])[:3])
