"""mk_shop.py - snapshot inside the item-choice (shop) loop.  The shop ($199de via $19984) is offered only to a playing human (-3914(A4)[p]==0) with
more than 3 wrenches (-3954(A4)[p]); the parked test human is eliminated after the race, so: ss_race0 + joystick-0 fires until $19984 is entered,
then poke flag[1]=0 and wrenches[1]=5 and run to the channel read $19db8 of the shop loop."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
r = R(sscfg.SNAP_RESULTS)
r.cmd('s 1000000')
r.cmd('kbd fe 80'); r.cmd('s 60000'); r.cmd('kbd fe 00')
out, g = r.cmd('u 19984 20000000'); print('entered', hex(g['PC']))
print('flags', [r.g16(-3914 + 2*i) for i in range(4)], 'wrench', [r.g16(-3954 + 2*i) for i in range(3)])
f0 = r.g16(-3914); r.cmd('w %x %04x0000' % (sscfg.A4 - 3914, f0))            # player0 flag keep, player1 flag = 0
p2 = r.g16(-3950); r.cmd('w %x 0005%04x' % (sscfg.A4 - 3954 + 2, p2))
print('after poke flags', [r.g16(-3914 + 2*i) for i in range(4)], 'wrench', [r.g16(-3954 + 2*i) for i in range(3)])
out, g = r.cmd('u 19db8 20000000'); print('shop loop', hex(g['PC']))
r.cmd('snap %s' % os.path.join(AGENT, 'snap', 'shop.snap')); r.close()
