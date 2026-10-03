"""a3: ev25_live.py -- event 25 (and 24) live: scroll 87 (FREEZE, body byte 7 = 1, byte 3 bit 7 clear) selected by poke (1262(A5) := 87, 2463(A5) := 1, 2306(A5) := 0, as cast_sleep_live.py) in CAVERN (gameplay_empire.snap),
FIRE held with nothing in front; bp at the event-24 push $00f0a0 and the event-25 push $00f0c8, entries decoded.  No object block in either level answers 25, so nothing matches in the consumer (hits fe24 printed)."""
from probe import *
h = HH.H(ROOT + '/scratchpad/cadaver/gameplay_empire.snap'); r = h.r
ww(r, A5 + 1262, 87); wb(r, A5 + 2463, 1); wb(r, A5 + 2306, 0)
r.cmd('kbd ff', 's 300', 'kbd 80')
for site, name in ((0xf0a0, 'event 24'), (0xf0c8, 'event 25')):
    e = bp_push(h, site, 3000000)
    if not e: print(name, 'no hit'); continue
    print('%s: entry op=$%04x ptr=%s word=$%04x  (spell id of 87 = body byte 0 = 2)  A2(body of item)=%06x  A3(item record)=%06x' % (name, e['op'], e['ptrname'], e['word'], e['regs']['A2'], e['regs']['A3']))
hh = r.hits(300000, 0xf0a0, 0xf0c8, 0xfe24)
print('further hits f0a0 f0c8 fe24:', [hh.get(a, 0) for a in (0xf0a0, 0xf0c8, 0xfe24)])
h.close()
