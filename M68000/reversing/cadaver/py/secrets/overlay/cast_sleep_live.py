"""cast_sleep_live.py: a real cast of SLEEP (spell `$17`) in level 1 room 1, to prove the room's event-24 block (gate `$17`: three verb-66 queue records
#666-#668, verb 17 sets object 659's state bit (`$734cc`, record byte 0 of the instance) 0, XP += 26) runs.

Start: scratchpad/cadaver/level1_loaded.snap (level 1, room 0).  Injected (labelled): the entry into room 1, a scratch `37 01 4 7 0` written over an
unrelated object's event-5 block and run through the consumer (`verbs2/h.py real()`, as `action/regalia_walk.py` does); the scroll, the way
`cast_live.py` does it: an object instance of the room is turned into a SLEEP scroll (byte 0 = spell, +1 = power, +7 = 1), `1262(A5)` = its id, `2463(A5)` = 1
(spell-cast mode), `2306(A5)` = 0, joystick fire held.  Everything after is the game's own path ($006faa -> $00f02e -> $00f0a0 -> consumer).

    python reversing/cadaver/py/secrets/overlay/cast_sleep_live.py [control]

`control` casts nothing (fire is not held) over the same step count: the same counters read 0.  Prints hits on the cast path, XP, object 659's state bit (`$734cc`, record byte 0 of the instance)
and the creature records queued at `1266(A5)`."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'verbs2'))
import h as H_
from ov import *
control = len(sys.argv) > 1 and sys.argv[1] == 'control'
h = H_.H(H_.SNAP1)
r = h.r
# an owner whose first block is an event-5 block of at least 10 bytes (so the scratch teleport fits)
for oid in range(1000):
    a = h.obj(oid)
    if a is None: continue
    b = r.mem(a + 0x10, 2)
    if b[1] & 0x7f == 5 and b[0] >= 12 and oid not in (0, 2): h.owner = oid; break
print('owner', h.owner, 'room before', r.w(A5 + 1166), 'xp', r.l(A5 + 1192))
H_.real(h, [0x25, 0x01, 4, 7, 0, 0x17], steps=400000)
print('room', r.w(A5 + 1166), 'xp', r.l(A5 + 1192), 'objs', r.w(A5 + 1152))
tbl = r.l(A5 + 56); n = r.w(A5 + 1152)
last = None
for i in range(1, n):
    e = r.mem(tbl + 0x46 * i, 0x46); p10 = int.from_bytes(e[10:14], 'big')
    if p10: print('  entry', i, 'id', r.w(p10 + 4), 'inst', hex(p10)); last = (r.w(p10 + 4), p10)
# the item's record: `$00f02e` takes A3 = record (resolved from 1262), A2 = A3 + byte 12 (the body); (A2) = spell id, +1 power, +4 target id, +7 flag
oid, inst = last          # the last object of the room: neither a creature (666-668) nor object 659, whose state bit is the result
a3 = h.obj(oid); assert a3 == inst, (hex(a3), hex(inst))
a2 = a3 + r.b(a3 + 12)
print('item', oid, 'A3', hex(a3), 'A2', hex(a2), 'body before', r.mem(a2, 12).hex())
wb(r, a2, 0x17); wb(r, a2 + 1, 10); ww(r, a2 + 4, oid); wb(r, a2 + 7, 1)
ww(r, a5(1262), oid); wb(r, a5(2463), 1); wb(r, a5(2306), 0)
inst = a2
xp0 = r.l(A5 + 1192)
rec659 = h.obj(659); b659 = r.mem(rec659, 0x30); q0 = r.mem(A5 + 1266, 16)
print('scroll body', r.mem(inst, 12).hex(), 'xp0', xp0)
r.snap(H_.TMP + '/sleep_before.snap')
if not control: r.cmd('kbd ff', 's 300', 'kbd 80')
h_ = r.hits(400000, 0x6faa, 0xf02e, 0xf0a0, 0xf0e4, 0x10e0e, 0xfe24)
print('hits', {hex(k): v for k, v in h_.items() if v})
r.cmd('kbd 00')
r.cmd('s 300000')
print('xp', xp0, '->', r.l(A5 + 1192), 'room', r.w(A5 + 1166))
a659 = r.mem(rec659, 0x30)
print('object 659 record bytes changed:', [(i, hex(b659[i]), hex(a659[i])) for i in range(0x30) if b659[i] != a659[i]])
print('1266(A5) before', q0.hex(' '), 'after', r.mem(A5 + 1266, 16).hex(' '))
h.close()
