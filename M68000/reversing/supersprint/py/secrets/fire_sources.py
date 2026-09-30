"""fire_sources.py - who can start a session from attract ($1399e -> $13a5e(player)): fire on channel of player i = -4810(A4)+2i.
A/B from the attract snapshot: keyboard LShift (player 0), joystick0 'fe 80' (player 1), joystick1 'ff 80' (player 2); which player index does
$13a5e receive (first stack word) and which human flag ends up 0 ($19164 sets -3914(A4)[player]=0)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
for tag, pkt, rel in (('LShift (2a)', ['2a'], ['aa']), ('joystick 0 fire (fe 80)', ['fe', '80'], ['fe', '00']), ('joystick 1 fire (ff 80)', ['ff', '80'], ['ff', '00']),
                      ('joystick 0 UP only (fe 01)', ['fe', '01'], ['fe', '00']), ('joystick 1 down+left (ff 06)', ['ff', '06'], ['ff', '00'])):
    r = R(sscfg.SNAP_ATTRACT); r.cmd('s 500000')
    r.cmd('kbd ' + ' '.join(pkt))
    out, g = r.cmd('u 13a5e 3000000')
    r.cmd('kbd ' + ' '.join(rel))
    if g['PC'] == 0x13a5e:
        player = r.w16(g['A7'] + 4)
        r.cmd('s 60000')
        out, g = r.cmd('u 193c4 3000000')
        print('%-30s -> $13a5e(player=%d); human flags (0=human) %s' % (tag, player, [r.g16(-3914 + 2*i) for i in range(4)]))
    else:
        print('%-30s -> session NOT started' % tag)
    r.close()
