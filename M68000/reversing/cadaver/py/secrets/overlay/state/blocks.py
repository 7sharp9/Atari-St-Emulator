"""blocks.py: split each type-6 record into header / scripts / instance(rec[12]) / mover(rec[13]) / anim(rec[14]) spans and print the mover and anim bytes.  usage: blocks.py SNAP [ids...]"""
import sys
from st import St
s = St(sys.argv[1]); ids = [int(x) for x in sys.argv[2:]] or range(s.count(6))
for i in ids:
    a = s.obj(i)
    if a is None: continue
    n = s.size(6, i); r = s.mem(a, n)
    t = (r[6] << 8) | r[7]; tm = s.mem(s.tmpl(t), 32)
    if r[13] == r[14] == r[12] and n - r[14] < 10: continue
    print('obj %3d t%-3d tmpl+12=%02x +22=%02x rec+3=%02x +15=%02x  inst@%02x[%d] mov@%02x[%d] anim@%02x[%d]' % (i, t, tm[12], tm[22], r[3], r[15], r[12], r[13]-r[12], r[13], r[14]-r[13], r[14], n-r[14]))
    print('     inst', r[r[12]:r[13]].hex(' '), '| mov', r[r[13]:r[14]].hex(' '), '| anim', r[r[14]:].hex(' '))
