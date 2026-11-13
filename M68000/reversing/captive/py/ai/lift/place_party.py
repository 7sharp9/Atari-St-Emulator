"""LABELLED POKE: move the party to another cell: place_party.py <snap> <out.snap> <x> <y> <facing>
Runs to $88b4, the return from $88b8 inside the per-frame $88ac (which has just cleared the old cell's occupancy bit
and latched its plane-2 pointer in 1766(A6)), pokes 26(A6) = x, 28(A6) = y, 30(A6) = facing, and lets $88d6 set
the occupancy bit and seen marks on the new cell. Then runs 120,000 steps (two frames) so the next $88b8 re-latches
the new cell, and saves. Prints the poked words and the old/new cells' tile bytes."""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe_input import srv, w16, A6  # noqa
s = srv(sys.argv[1]); x, y, f = map(int, sys.argv[3:6])
ox, oy = w16(s, 26), w16(s, 28)
r = s('run', max_steps=200000, until_pc=[0x88b4])
assert s.reg('pc') == 0x88b4, r
for off, v in ((26, x), (28, y), (30, f)):
    s('poke', addr=A6 + off, width=2, value=v)
s('step', n=120000)
t = lambda cx, cy: s.read(A6 + 9242 + 64 * cy + cx, 1)[0]
print(f'POKE 26/28/30(A6) = {x},{y},{f} at $88b4 (was {ox},{oy}); tile old {t(ox, oy):02x} new {t(x, y):02x};',
      'pos', w16(s, 26), w16(s, 28), 'face', w16(s, 30), 'latch 1766', hex(struct.unpack('>I', s.read(A6 + 1766, 4))[0]))
s('save', path=os.path.abspath(sys.argv[2])); s.close()
