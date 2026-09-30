"""Patch a snapshot: set PC / address registers and poke RAM bytes, write a new snapshot.
usage: patch_snap.py in.snap out.snap pc=10410 a1=80000 ram:18b2e=01 ...
Snapshot layout (tools/gfxview.py snapshot_regs): 'A68S', ver byte, then 19 little-endian int32
(D0-D7, A0-A7, USP, SSP, PC), int16 CCR/SR, u32 RAM length, RAM bytes."""
import struct, sys
src, dst = sys.argv[1], sys.argv[2]
b = bytearray(open(src, 'rb').read())
assert b[:4] == b'A68S' and b[4] >= 5
names = ['d%d' % i for i in range(8)] + ['a%d' % i for i in range(8)] + ['usp', 'ssp', 'pc']
ramoff = 5 + 19 * 4 + 2 + 4
for arg in sys.argv[3:]:
    k, v = arg.split('=', 1)
    if k.startswith('ram:'):
        a = int(k[4:], 16); data = bytes.fromhex(v)
        b[ramoff + a: ramoff + a + len(data)] = data
    else:
        struct.pack_into('<i', b, 5 + 4 * names.index(k), struct.unpack('<i', struct.pack('<I', int(v, 16)))[0])
open(dst, 'wb').write(b)
print('wrote', dst)
