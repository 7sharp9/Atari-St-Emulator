"""where.py SNAP ID...: room (type-5 list), template, class, record header and type-specific block of each object (static)."""
import os, sys
ROOT = os.environ.get('M68000_ROOT') or os.getcwd()
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay'); sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay/graph')
sys.path.insert(0, ROOT + '/tools'); sys.path.insert(0, ROOT + '/reversing/cadaver/py')
from model import Snap
s = Snap(sys.argv[1])
loc = {}
for slot in s.rooms():
    for o in s.roomlist(slot):
        loc.setdefault(o, []).append(slot)
for a in sys.argv[2:]:
    i = int(a); o = s.obj(i)
    if o is None: print(i, 'no record'); continue
    c = s.cls(i)
    r = s.ram; ad = o['addr']
    print('obj %d rooms %s b10room %d tmpl %d class %s b23 %s b3 %02x rec %s blk %s' % (i, loc.get(i), o['room'], o['tmpl'], c and hex(c['b22']), c and c['b23'], o['b3'], r[ad:ad+16].hex(' '), r[ad + o['b12']:ad + o['b12'] + 8].hex(' ')))
# template names (type-2 template word +10 through the (A5)+168/172 name tables)
from name_strings import decode_index
import struct
t168 = struct.unpack_from('>I', s.ram, s.a5 + 168)[0]; t172 = struct.unpack_from('>I', s.ram, s.a5 + 172)[0]
for a in sys.argv[2:]:
    c = s.cls(int(a))
    if c: print('obj %s name %r' % (a, decode_index(s.ram, s.base, t168, t172, c['name']).split(b'\0')[0].decode('latin1')))
