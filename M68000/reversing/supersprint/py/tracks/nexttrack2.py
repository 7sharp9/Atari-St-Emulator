import sys; sys.path.insert(0,'.')
from tkcommon import *
r = Repl2(out('snaps', 'race_0.snap'))
o, reg = r.cmd2('bpc 13b00 1 26000000')
for k in range(40):
    if reg['PC'] == 0x13b00: break
    r.cmd('kbd fe 80'); r.cmd('s 100000'); r.cmd('kbd fe 00')
    o, reg = r.cmd2('bpc 13b00 1 3000000')
print('hit $13b00 (addq #1,-1748(A4)): PC=%x race counter before = %d' % (reg['PC'], int.from_bytes(r.mem(A4-1748,2),'big')))
r.cmd('s 20'); print('after: race counter =', int.from_bytes(r.mem(A4-1748,2),'big'))
o, reg = r.cmd2('bpc be40 1 4000000')
print('next be40 entry PC=%x track arg %d race counter %d' % (reg['PC'], int.from_bytes(r.mem(reg['A7']+4,2),'big'), int.from_bytes(r.mem(A4-1748,2),'big')))
r.close()
