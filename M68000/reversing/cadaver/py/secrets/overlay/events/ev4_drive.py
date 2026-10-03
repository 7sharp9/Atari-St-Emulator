"""a3: ev4_drive.py -- event 4, natural input from the natural chain's checkpoint 'select165' (s88 g1/D1_W1125000_0/ck_79_select165.snap: urn 165 selected, hero aimed left at (49,40,43,34) in room 39):
FIRE held (the throw of g1's `throw165`), bp at the producer push $00f328.  Prints the entry [4][thrown record][target id], the consumer gate for it (object 165's event-4 block, gate $0063 = altar 99)
and the effect (object 324 appears).  Expected: entry ptr = obj 165, word 99; gate accepted; XP +26 and 324 present afterwards."""
from probe import *
snap = absp(sys.argv[1]) if len(sys.argv) > 1 else ROOT + '/scratchpad/cadaver/s88/parent/full_A/g1/D1_W1125000_0/ck_79_select165.snap'
h = HH.H(snap); r = h.r
xp0 = r.l(A5 + 1192)
r.cmd('kbd ff 80', 's 300')
e = bp_push(h, 0xf328, 1500000)
print('entry op=$%04x ptr=%s word=%d  (target altar 99 = $63)  1166(A5)=%d  A1=%06x A2=%06x' % (e['op'], e['ptrname'], e['word'], e['room1166'], e['regs']['A1'], e['regs']['A2']))
for g in follow_consumer(h, e, 4): print('  consumer gate:', g)
r.cmd('s 100000')
r.cmd('kbd ff 00', 's 30000')
ids = [live_res(h, 6, 324) is not None]
print('XP %d -> %d; record of object 324 resolvable: %s; object 165 still resolvable: %s' % (xp0, r.l(A5 + 1192), ids[0], live_res(h, 6, 165) is not None))
h.close()
