# t_live0.py SNAP: list the live sprite-array objects (id, record, +3, room, offsets, +15, template flags/class); the quick look used to pick experiment targets
import sys
from live import *
r = start(sys.argv[1])
for o in objs(r):
    h = o['hdr']; t = o['tm']
    print('slot %2d id %3d rec %06x x,y,z=%02x,%02x,%02x +3=%02x room=%02x nblk=%02x off=%02x/%02x/%02x +15=%02x | tmpl+12=%02x cls=%02x | draw42=%02x' % (o['slot'], o['id'], o['rec'], h[0], h[1], h[2], h[3], h[10], h[11], h[12], h[13], h[14], h[15], t[12], t[22], o['e'][42]))
print('PC', hex(r.pc()))
r.close()
