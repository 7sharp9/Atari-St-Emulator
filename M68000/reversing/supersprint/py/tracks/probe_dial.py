import sys; sys.path.insert(0,'.')
from tkcommon import *
r = Repl2(out('snaps','w0.snap'))
o,reg = r.cmd2('bpc 19646 1 400000')
print('\n'.join(o[-14:]))
a6 = reg['A6']; print(hex(a6))
print(r.mem(a6-14,16).hex(' '))
r.close()
