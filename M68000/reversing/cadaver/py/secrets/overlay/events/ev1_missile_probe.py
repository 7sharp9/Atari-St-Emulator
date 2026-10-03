"""a3: ev1_missile_probe.py -- the 'down' run of ev1_missile.py stopped at the first event-1 push ($00fa62): decoded entry ([1][struck object][word]), the mover (A1) and what the consumer does with it.
Expected: ptr = a CAVERN object id, word = 15 (MAGIC MISSILE spell id = body byte 0 of scroll 27 = ammunition 476 body byte 0 & $7f)."""
from probe import *
h = HH.H(ROOT + '/scratchpad/cadaver/gameplay_empire.snap'); r = h.r
r.cmd('kbd ff 02', 's 300', 's 60000', 'kbd ff 00', 's 30000')
ww(r, A5 + 1262, 27); wb(r, A5 + 2463, 1); wb(r, A5 + 2306, 0)
r.cmd('kbd ff', 's 300', 'kbd 80')
print('scroll 27 body byte 0 =', h.ram[h.obj(27) + h.ram[h.obj(27) + 12]])
for k in range(3):
    e = bp_push(h, 0xfa62, 3000000)
    if not e: print('no hit'); break
    a1 = e['regs']['A1']; body = a1 + r.b(a1 + 12)
    print('entry op=$%04x ptr=%s word=%d  A1(mover)=%06x id %d class(22 of class tmpl)=? body0..2=%s  A4=%06x' % (e['op'], e['ptrname'], e['word'], a1, r.w(a1 + 4), r.mem(body, 3).hex(), e['regs']['A4']))
    for g in follow_consumer(h, e, 1, 8): print('   consumer gate:', g)
h.close()
