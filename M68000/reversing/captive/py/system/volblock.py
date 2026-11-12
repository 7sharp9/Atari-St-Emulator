"""Decode the volume block (unit 1) and test the reading of its table from the OS code:
buffer word 12.. = 6 per-file-type words (the OS's $978 indexes 12(buf,type*2)), buffer 24..187 = one byte per unit
holding the 1-based directory index of the file that owns it (the OS's delete at $32a clears the bytes equal to the
file's index). Buffer offsets are the OS's, which are fedfs's data offsets (the header long, the length, is not in
the buffer: the OS compares the buffer's first long with the volume-name hash, $920).
usage: volblock.py <disk.st>"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from util import root
sys.path.insert(0, os.path.join(root(), 'reversing', 'captive', 'py'))
import fedfs
img = open(sys.argv[1], 'rb').read()
hdr, data, ok = fedfs.decode_unit(img, 1, 1)
_, data, ok = fedfs.decode_unit(img, 1, hdr)
buf = data
print('header', hex(hdr), 'checksum ok', ok, 'hash', buf[0:4].hex(), 'name', buf[4:8], 'bytes 8..11', buf[8:12].hex())
print('words at 12..23:', [hex(x) for x in struct.unpack('>6H', buf[12:24])])
umap = buf[24:188]
print('map bytes 24..187 (unit u at 24+u):')
for i in range(0, 164, 32): print(f'  u{i:3d}: ' + ' '.join(f'{b:02x}' for b in umap[i:i + 32]))
ents = fedfs.read_dir(img)
match = bad = 0
for idx, (name, u, count, length) in enumerate(ents, 1):
    owned = sorted(i for i, b in enumerate(umap) if b == idx)
    exp = [u + 2 * k for k in range(count)]
    good = owned == exp
    match += good; bad += not good
    if not good or idx <= 3: print(f'  {idx:2d} {name:12s} start {u:3d} count {count:2d} map {owned[:6]}{"..." if len(owned) > 6 else ""} {"OK" if good else "MISMATCH"}')
print(f'{match} of {len(ents)} files: map bytes == their unit span; free (0) units: {umap.count(0)}; other values: '
      f'{sorted(set(umap) - set(range(len(ents) + 1)))}')
