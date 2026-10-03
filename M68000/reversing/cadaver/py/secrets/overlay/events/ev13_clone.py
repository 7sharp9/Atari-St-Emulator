"""a3: ev13_clone.py -- is the event-13 recipient obj 912 of the natural room-27 drive a runtime copy of object 127?  Compares the first 0x40 bytes of the live record 912 (block lists and body) with object 127's record in the same snapshot after bp at $b0f0."""
from probe import *
h = HH.H(ROOT + '/scratchpad/cadaver/s88/parent/full_A/e1/route/03_D.snap'); r = h.r
e = bp_push(h, 0xb0f0, 3000000)
a = e['ptr']; b = live_res(h, 6, 127)
print('ptr', e['ptrname'], '%06x' % a, 'object 127 live record', b and '%06x' % b)
x = r.mem(a, 0x50); y = r.mem(b, 0x50) if b else None
print('912:', x.hex(' ')); print('127:', y.hex(' ') if y else None)
print('record bytes equal except position/id/instance bytes:', [i for i in range(0x50) if y and x[i] != y[i]])
h.close()
