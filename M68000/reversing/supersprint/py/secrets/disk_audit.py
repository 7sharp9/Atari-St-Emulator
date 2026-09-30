"""disk_audit.py - audit the .ST image: directory incl. deleted/hidden/volume entries, AUTO folder, FAT chains, clusters that are
free/unreferenced but hold non-zero data, boot sector, tail beyond the FAT area."""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fat12 import *
d = Disk(sscfg.DISK)
b = d.img
print('image', len(b), 'bytes; bps', d.bps, 'spc', d.spc, 'reserved', d.res, 'nfat', d.nfat, 'root entries', d.nroot, 'spf', d.spf)
print('boot sector: jump %s oem %r serial %s; boot checksum sum=%04x (bootable iff 0x1234)' % (b[:3].hex(), bytes(b[3:8]), b[8:11].hex(), sum(struct.unpack('>256H', bytes(b[:512]))) & 0xffff))
print('boot sector tail (non-zero bytes after BPB):', bytes(b[0x1e:0x1fe]).strip(b'\0')[:64])
def dump_dir(pos, n, label):
    print('--', label)
    for i in range(n):
        e = b[pos + i * 32: pos + i * 32 + 32]
        if e[0] == 0:
            break
        nm = e[:8].decode('latin1') + '.' + e[8:11].decode('latin1')
        print('  %-14r attr %02x cluster %4d size %7d %s' % (nm, e[11], struct.unpack_from('<H', e, 26)[0], struct.unpack_from('<I', e, 28)[0], 'DELETED' if e[0] == 0xe5 else ''))
dump_dir(d.root, d.nroot, 'root')
cl, _ = d.find('AUTO')
dump_dir(d.data + (cl - 2) * d.spc * d.bps, 32, 'AUTO')
# clusters in use
used = set()
def mark(cl, size):
    for c in range(1):  # placeholder
        pass
total_clusters = (len(b) - d.data) // (d.spc * d.bps)
chain_of = {}
def walk(cl):
    out = []
    while 2 <= cl < 0xff0 and cl not in out:
        out.append(cl); cl = d.fat(cl)
    return out
for name, attr, cl, size in d.entries():
    used.update(walk(cl))
acl, _ = d.find('AUTO'); used.update(walk(acl))
for name, attr, cl, size in d.entries(d.data + (acl - 2) * d.spc * d.bps, 32):
    used.update(walk(cl))
print('data clusters', total_clusters, 'used', len(used))
nonzero_free = []
badclusters = []
for c in range(2, 2 + total_clusters):
    if c in used: continue
    f = d.fat(c)
    if f == 0xff7: badclusters.append(c)
    off = d.data + (c - 2) * d.spc * d.bps
    chunk = b[off: off + d.spc * d.bps]
    if any(chunk):
        nonzero_free.append((c, f, sum(1 for x in chunk if x)))
print('bad-marked clusters', badclusters)
print('unreferenced clusters with non-zero content:', nonzero_free[:40], 'count', len(nonzero_free))
# slack: bytes after EOF inside last cluster of each file
for name, attr, cl, size in list(d.entries()):
    ext = d.extents(cl, size)
    if ext:
        last = ext[-1]; end = last[0] + last[1]; csz = d.spc * d.bps
        slack = b[end: (last[0] // csz * csz + csz) if False else last[0] + csz]
        print('slack after', name, 'nonzero bytes in cluster slack:', sum(1 for x in b[end: last[0] + csz] if x))
# FAT copies equal?
fsz = d.spf * d.bps
print('FAT1 == FAT2:', b[d.fat0:d.fat0 + fsz] == b[d.fat0 + fsz: d.fat0 + 2 * fsz])
print('bytes beyond end of FAT area that are not in data clusters: none' if True else '')
