import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
E = {0x19984:'shop', 0x18024:'prepare', 0x172f0:'hiscore', 0xbe40:'race', 0x1a4ca:'winner', 0x19164:'select', 0x13a5e:'session', 0x1399e:'wait', 0x186ce:'join-check', 0x18626:'prep-esc-poll', 0x1b458:'t534', 0x1a4ca:'winner'}
r = R(sscfg.SNAP_RESULTS)
a = Acc(r, list(E))
def rep(tag):
    print(tag, {E[k]: v for k, v in a.tot.items() if v}, hex(a.regs['PC']))
    for k in a.tot: a.tot[k] = 0
a.run(1000000); rep('start (winner circle, no input) 1M')
for i in range(8):
    a.kbd('fe', '80'); a.run(60000); a.kbd('fe', '00'); a.run(2500000); rep('after joystick0 fire #%d' % (i + 1))
r.close()
