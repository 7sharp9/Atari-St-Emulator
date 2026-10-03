"""a3: ev1_missile.py [snap] -- event 1 at the hit-scan site $00fa62 with a poked selection: 1262(A5) := 27 (scroll MAGIC MISSILE, body byte 7 = 0), 2463(A5) := 1 (spell-cast mode), 2306(A5) := 0 (the way cast_sleep_live.py
does it), FIRE held after a short joystick tap in each of the four directions (the hero faces the last direction moved); the cast `$f02e` spawns the class-$82 ammunition 476 (`$f0f6`) and its flight reaches an object.
Prints hit counts per direction.  LABEL: the selection is poked (synthetic), everything after is natural."""
from probe import *
snap = absp(sys.argv[1]) if len(sys.argv) > 1 else ROOT + '/scratchpad/cadaver/gameplay_empire.snap'
for name, bits in (('up', 1), ('down', 2), ('left', 4), ('right', 8)):
    h = HH.H(snap); r = h.r
    r.cmd('kbd ff %02x' % bits, 's 300', 's 60000', 'kbd ff 00', 's 30000')
    ww(r, A5 + 1262, 27); wb(r, A5 + 2463, 1); wb(r, A5 + 2306, 0)
    r.cmd('kbd ff', 's 300', 'kbd 80')
    hh = r.hits(2500000, 0xf02e, 0xf0f6, 0xfa62, 0xfa34, 0xfe24)
    print('%-5s hits cast f02e, spawn f0f6, event-1 push fa62, hit loop fa34, match fe24:' % name, [hh.get(a, 0) for a in (0xf02e, 0xf0f6, 0xfa62, 0xfa34, 0xfe24)])
    h.close()
