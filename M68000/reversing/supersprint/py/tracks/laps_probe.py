"""Lap/checkpoint semantics: sample -3906(A4) (lap counter), -3850(A4) (next-checkpoint counter) and -3842(A4) for every
car each ~frame from race_T.snap; print every change with the frame number, and the surface-attribute checkpoint cells."""
import sys; sys.path.insert(0,'.')
from tkcommon import *
import struct, attrmap as AM
T = int(sys.argv[1]); maxf = int(sys.argv[2]) if len(sys.argv) > 2 else 2500
m = AM.attr_map(T)
cps = {}
for i, v in enumerate(m):
    if (v & 3) == 2 and (v & 0x7f):
        cps.setdefault((v >> 2) & 7, []).append((i % 40, i // 40, '%02x' % v))
print('checkpoint cells (attr low2==2) by n=(v>>2)&7:', {k: v for k, v in sorted(cps.items())})
r = Repl(out('snaps', 'race_%d.snap' % T)); r.cmd('s 3000000')
last = None
for f in range(maxf):
    r.cmd('s 12000')
    b = r.mem(A4 - 3954, 130)
    w = lambda o, n=4: struct.unpack('>%dh' % n, b[o + 3954: o + 3954 + 2 * n])
    cur = (w(-3906), w(-3850), w(-3914))
    if last is None or cur[:2] != last[:2]:
        print('frame %4d lap(-3906)=%s cp(-3850)=%s drone(-3914)=%s' % (f, cur[0], cur[1], cur[2]), flush=True)
    last = cur
    if max(cur[0]) >= 5: break
r.close()
