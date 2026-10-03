"""recdump.py: hex-dump type-6 record(s) and their type-2 template.  usage: recdump.py SNAP ID [ID...]"""
import sys
from st import St
s = St(sys.argv[1])
for i in sys.argv[2:]:
    i = int(i); a = s.obj(i); n = s.size(6, i)
    print('obj %d rec $%06x size %d: %s' % (i, a, n, s.mem(a, n).hex(' ')))
    t = s.w(a + 6); ta = s.tmpl(t)
    print('   template %d $%06x size %d: %s' % (t, ta, s.size(2, t), s.mem(ta, s.size(2, t)).hex(' ')))
