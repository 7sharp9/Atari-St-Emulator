"""Gate cycle: sample gate state arrays every ~frame: -1814 dir, -1820 position (0..4 = animation frame), -1826 timer, -1832 route value
(2/3 used by waypoint records with hd&0x200), and the game frame counter -8072(A4)."""
import sys; sys.path.insert(0,'.')
from tkcommon import *
import struct
T = int(sys.argv[1]); frames = int(sys.argv[2]) if len(sys.argv) > 2 else 1400
r = Repl(out('snaps', 'race_%d.snap' % T)); r.cmd('s 3000000')
n = struct.unpack('>h', r.mem(A4 - 1808, 2))[0]
print('track %d: %d gate(s)' % (T + 1, n))
last = None; log = []
for f in range(frames):
    r.cmd('s 12000')
    b = r.mem(A4 - 1832, 26)
    w = lambda o, k: struct.unpack('>%dh' % k, b[o + 1832: o + 1832 + 2 * k])
    st = (w(-1814, n), w(-1820, n), w(-1832, n))
    fc = struct.unpack('>h', r.mem(A4 - 8072, 2))[0]
    if st != last:
        print('frame-ctr %6d dir=%s pos=%s route=%s' % (fc, st[0], st[1], st[2]), flush=True); last = st
r.close()
