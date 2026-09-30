"""extract_overlay.py [disk.st] [snapshot] [outdir]
Level-code overlay extraction (Cadaver, one-disk Empire crack).  Reads the header file at sector 400 (magic '881990'),
the level table (20-byte records of five (start_sector, nsectors) pairs, level record = 252(A5)+16+20*level, sector-count
pairs contiguous), takes pair 0 of level N (the overlay), LZHUF-depacks it (lzhuf.py, same algorithm as the game's $0118ec),
writes overlay_levelN.bin (the bytes the game puts at 2534(A5)) and compares with RAM at the snapshot's overlay base.
Expected for level 0 from gameplay_empire.snap: 3084 bytes, 3084/3084 bytes identical to RAM $04c65e.."""
import sys, struct, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, 'tools')
import lzhuf
from gfxview import load_ram
disk = sys.argv[1] if len(sys.argv) > 1 else '../Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st'
snap = sys.argv[2] if len(sys.argv) > 2 else 'scratchpad/cadaver/gameplay_empire.snap'
out = sys.argv[3] if len(sys.argv) > 3 else 'scratchpad/cadaver/secrets_out/overlay'
hdr = lzhuf.read_sectors(disk, 400, 1)
assert hdr[:6] == b'881990', hdr[:6]
print('header words', [hex(struct.unpack_from('>H', hdr, 6 + 2 * i)[0]) for i in range(5)])
# level records start at +16 (252(A5)+$10), 20 bytes each
recs = []
for lv in range(10):
    o = 16 + 20 * lv
    pairs = [struct.unpack_from('>HH', hdr, o + 4 * k) for k in range(5)]
    recs.append(pairs)
    print('level', lv, [(s, n) for s, n in pairs])
ram, _ = load_ram(snap)
base = struct.unpack_from('>I', ram, 0x18152 + 2534)[0]
for lv, pairs in enumerate(recs):
    s, n = pairs[0]
    if n == 0: continue
    raw = lzhuf.read_sectors(disk, s, n); size = struct.unpack('>I', raw[:4])[0]
    data = lzhuf.decode(raw[4:], size)
    open(os.path.join(out, 'overlay_level%d.bin' % lv), 'wb').write(data)
    print('level %d overlay: sectors %d..%d, raw %d bytes, depacked %d bytes' % (lv, s, s + n - 1, n * 512, size))
    if lv == 0:
        same = sum(1 for i in range(size) if ram[base + i] == data[i]) if False else sum(1 for i in range(size - 4) if ram[base + i] == data[4 + i])
        print('  vs RAM $%06x: %d/%d bytes identical' % (base, same, size - 4))
