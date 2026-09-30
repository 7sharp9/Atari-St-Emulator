"""scan_overlays.py <disk.st> <header_sector>: parse the '881990' level table (20-byte records from +16, five
(start_sector, nsectors) pairs each, until an all-zero record), LZHUF-depack every pair (lzhuf.py), and flag pairs whose
depacked bytes look like a level-code overlay: [u32 len][u16 $0050][u16 table offsets ascending-ish ...][u16 2].
Writes overlay_<tag>_pair<i>.bin for hits (size < 6000 and <= 6 sectors, to exclude the 7-11KB blobs with a similar header shape) (tag = third arg).  Expected: one-disk image sector 400 -> levels 0 and 1 (pair 0 each);
Disk 2 sector 7 -> see the printed table."""
import sys, struct, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lzhuf
disk, hs = sys.argv[1], int(sys.argv[2]); tag = sys.argv[3] if len(sys.argv) > 3 else 'x'
hdr = lzhuf.read_sectors(disk, hs, 1)
assert hdr[:6] == b'881990'
out = os.path.dirname(os.path.abspath(__file__))
pairs = []
o = 16
while o + 4 <= 512:
    s, n = struct.unpack_from('>HH', hdr, o)
    if s == 0 and n == 0: break
    pairs.append((s, n)); o += 4
print('pairs:', pairs)
k = 0
for i, (s, n) in enumerate(pairs):
    if n == 0: continue
    raw = lzhuf.read_sectors(disk, s, n)
    size = struct.unpack_from('>I', raw, 0)[0]
    try:
        data = lzhuf.decode(raw[4:], size) if 0 < size < 200000 else b''
    except Exception as e:
        data = b''
    ok = False
    if len(data) > 40:
        w = lambda q: struct.unpack_from('>H', data, 4 + q)[0]
        inner = struct.unpack_from('>I', data, 0)[0]
        ok = (inner == len(data) - 4 or inner == size - 4) and 0x20 <= w(0) < 0x400 and w(2) < w(4) < w(6) < w(8) < 0x1000 and w(10) < 100 and size < 6000 and n <= 6
    print('pair %2d sector %4d n=%3d size=%6d %s' % (i, s, n, size, 'OVERLAY' if ok else ''))
    if ok:
        open(os.path.join(out, 'overlay_%s_pair%d.bin' % (tag, i)), 'wb').write(data); k += 1
