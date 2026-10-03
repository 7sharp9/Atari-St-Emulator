"""a3: ev12_drive.py -- event 12 (mover-program opcode 4, producer $00f9a2) in level 1 with injected setup, as cast_sleep_live.py does it: (1) a scratch `37 0b 04 02 00` (TELEPORT room 11 at (4,2,0), the
coordinates of a level-1 TELEPORT verb into room 11) run through the consumer over an unrelated event-5 block puts the hero in room 11, which holds the movers 320 and 321 (both carry event-12 blocks);
(2) a scratch `11 01 40` (verb 11 GOMOVE #320: mover byte := 0, the byte the game's own verbs 11 write) starts 320's program; everything after is the game's own path.  bp at $f9a2 decodes the entry; the consumer
gate and block (object 320 gate 05: PLAY SOUND $34) are followed.  LABEL: teleport and GOMOVE are injected (synthetic)."""
from probe import *
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay/verbs2')
h = HH.H(ROOT + '/scratchpad/cadaver/level1_loaded.snap'); r = h.r
for oid in range(1000):
    a = h.obj(oid)
    if a is None: continue
    b = r.mem(a + 0x10, 2)
    if b[1] & 0x7f == 5 and b[0] >= 12 and oid not in (0, 2): h.owner = oid; break
print('owner', h.owner, 'room before', r.w(A5 + 1166))
HH.real(h, [0x25, 0x0b, 4, 2, 0, 0x17], steps=400000)
print('room', r.w(A5 + 1166), 'live objects', r.w(A5 + 1152))
tbl = r.l(A5 + 56); n = r.w(A5 + 1152); ids = []
for i in range(n):
    e = r.mem(tbl + 0x46 * i, 0x46); p10 = int.from_bytes(e[10:14], 'big')
    if p10 > 0x1000: ids.append(r.w(p10 + 4))
print('live ids', ids)
rec = h.obj(320); m = rec + r.b(rec + 13)
print('320 mover byte before', r.b(m), 'program', r.mem(m + 14, 12).hex())
if 'control' not in sys.argv: HH.real(h, [11, 0x01, 0x40, 0x17], steps=1000)
else: HH.real(h, [0x17], steps=1000)
print('320 mover byte after', 'control' if 'control' in sys.argv else 'GOMOVE', r.b(m), ' mover state byte of the live record read at rec+rec[13]=%06x' % m)
e = bp_push(h, 0xf9a2, 3000000)
if not e: print('no hit'); sys.exit(1)
print('entry op=$%04x ptr=%s word=%d  A1=%06x A3(program cursor)=%06x D0=%x' % (e['op'], e['ptrname'], e['word'], e['regs']['A1'], e['regs']['A3'], e['regs']['D0']))
for g in follow_consumer(h, e, 12, 8): print('   consumer gate:', g)
hh = r.hits(300000, 0xfe24, 0xfe36, 0xfe5a, 0xf9a2)
print('then hits match/gate/verb/f9a2:', [hh.get(a, 0) for a in (0xfe24, 0xfe36, 0xfe5a, 0xf9a2)])
h.close()
