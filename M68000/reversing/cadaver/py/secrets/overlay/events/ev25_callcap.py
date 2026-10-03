"""a3: ev25_callcap.py -- the cast routine $00f034 (D1 = item id, normally 1262(A5)): callcap on a scroll id and read the ring entries it queues: expect [$4018][room record 164(A5)][word = body byte 0 = spell id] (event 24, site $f0a0)
then [$0019][item record][stale word] (event 25, site $f0c8).  Scrolls tried: 27 (MAGIC MISSILE), 87 (FREEZE), 161 (MIND BLAST) of level 0 (body byte 7 not 0 and not 2); 371 (READ MAGIC, byte 7 = 2) and 132 (READ LANGUAGE) as contrasts."""
from probe import *
from lib2 import afterl, afterw, afterb
h = HH.H(ROOT + '/scratchpad/cadaver/gameplay_empire.snap'); r = h.r
for oid in (27, 87, 161, 371, 132, 324):
    a = h.obj(oid); body = a + h.ram[a + 12]
    wq = r.l(A5 + 304); c0 = r.w(A5 + 1154)
    d = h.call(0xf034, [], cap=300000, regs='D1=%x' % oid)
    n = afterw(h, d, A5 + 1154) - c0
    ents = []
    for k in range(n):
        p = wq + 8 * k
        ents.append((afterw(h, d, p), afterl(h, d, p + 2), afterw(h, d, p + 6)))
    print('item %3d body[0..7]=%s locked(byte3 bit7)=%d byte7=%d returned=%s steps=%d: %d pushes %s' % (oid, h.ram[body:body + 8].hex(), h.ram[body + 3] >> 7, h.ram[body + 7], d['ret'], d['steps'], n,
          [('op $%04x' % op, ptr_name_live(h, ptr) if False else ('room rec' if ptr == r.l(A5 + 164) else 'item rec %d' % (h.r.w(ptr + 4)) if 0x1000 < ptr < 0x7ffff else hex(ptr)), 'word $%04x' % w) for op, ptr, w in ents]))
h.close()
