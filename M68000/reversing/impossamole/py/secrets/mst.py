"""MST.IMG = GEMDOS PRG stub (text 0x1e4 bytes: banner, trainer prompt, 'AUTOMATION PACKER V2.2f' decruncher) + an LSD! payload; depack it and compare with the resident image."""
import sys, struct
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
from lsd import depack
d = rd('MST.IMG')
i = d.find(b'LSD!')
print('LSD! tag at file offset', hex(i), 'U,P =', struct.unpack('>II', d[i+4:i+12]), 'file len', len(d), 'payload bytes after tag', len(d) - i - 4)
o, a1, nl, nm = depack(d[i:])
print('unpacked', len(o), 'final a1', a1, 'literals', nl, 'matches', nm)
open(WORK + '/data/mst_unpacked.bin', 'wb').write(o)
r = ram()
# find the load address: search a distinctive chunk
for off in (0x100, 0x1000, 0x3000, 0x8000):
    ch = o[off:off + 64]
    k = r.find(ch)
    print(f'chunk of unpacked+{off:#x} found in RAM at', hex(k) if k >= 0 else None, ' => load base', hex(k - off) if k >= 0 else None)
base = 0xa8a8
n = len(o)
m = sum(1 for k in range(n) if o[k] == r[base + k])
print(f'image at ${base:x}..${base+n:x}: {m}/{n} bytes equal to the live RAM of the Amazon snapshot ({100*m/n:.2f}%)')
# where do they differ? runs
diff = [k for k in range(n) if o[k] != r[base + k]]
runs = []
for k in diff:
    if runs and k == runs[-1][1] + 1: runs[-1][1] = k
    else: runs.append([k, k])
print('differing runs:', len(runs))
for a, b in runs[:40]: print(f'   ${base+a:05x}..${base+b:05x} ({b-a+1} bytes)')
