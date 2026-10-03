"""x12_mover_template_bits.py: the mover pass $f71a reads the TEMPLATE flags through the copy kept in the sprite entry (+49, written at instantiation by $00ce6a): bit 0 (dynamic) must be set, bit 5 (player-style) clear.
Poke sprite+49 of the patrolling urn 198 (L0 room 53) and count position changes in 40 passes: control, bit 0 cleared, bit 5 set.   usage: x12_mover_template_bits.py"""
import sys
from lab import *
SNAP = SN('URN53', 'scratchpad/cadaver/s87/b3/work/r16/s13_b.snap')
def run(label, mod):
    r = start(SNAP); passes(r, 2)
    e = sprites(r)[198]['ent']; v = r.mem(e + 49, 1)[0]; wb(r, e + 49, mod(v))
    pos = []
    for _ in range(40):
        rec = rec_of(r, 198); pos.append(bytes(r.mem(rec, 3))); passes(r, 1)
    print('%-34s sprite+49 %02x -> %02x: position changes in 39 transitions: %d' % (label, v, mod(v), sum(1 for a, b in zip(pos, pos[1:]) if a != b)))
    r.close()
run('control', lambda v: v)
run('template bit 0 (dynamic) cleared', lambda v: v & ~1)
run('template bit 5 (player-style) set', lambda v: v | 0x20)
