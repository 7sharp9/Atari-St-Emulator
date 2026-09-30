"""Make disk variants under data/: DISK.ID deleted (dir entry marked $e5) and DISK.ID content changed."""
import struct, sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
d = bytearray(open(DISK, 'rb').read())
bps, spc, res, nfat, nroot, tot, media, spf = struct.unpack('<HBHBHHBH', d[11:11+2+1+2+1+2+2+1+2])
print('bps', bps, 'spc', spc, 'res', res, 'nfat(BPB)', nfat, 'nroot', nroot, 'spf', spf)
nfat = 2                       # the BPB byte undercounts (README): the real layout has two FATs
root = (res + nfat * spf) * bps
data0 = root + nroot * 32
for i in range(nroot):
    e = d[root + 32*i: root + 32*i + 32]
    if e[:11] == b'DISK    ID ':
        cl = struct.unpack('<H', e[26:28])[0]; size = struct.unpack('<I', e[28:32])[0]
        off = data0 + (cl - 2) * spc * bps
        print('DISK.ID entry', i, 'cluster', cl, 'size', size, 'offset', off, 'data', d[off:off+4].hex())
        a = bytearray(d); a[root + 32*i] = 0xe5
        open(WORK + '/data/disk_no_diskid.st', 'wb').write(a)
        b = bytearray(d); b[off:off+4] = bytes.fromhex('11223344')
        open(WORK + '/data/disk_bad_diskid.st', 'wb').write(b)
        break
else:
    print('not found')
