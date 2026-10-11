"""finale_delta.py <dir> <tag>: model check of the $1a648 finale frames. For frame k (1..7): take the page shown at the
previous snapshot (<tag>_base, then <tag>_f<k-1>), apply the k-th record list of the $3f768 table ($1a808: word offset,
word count-1, count longs; a negative offset ends the frame) and compare the 32000 bytes with the page shown at <tag>_f<k>."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve()
while not (ROOT / 'tools' / 'rdis.py').exists(): ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / 'tools'))
from pm_export import ram_from_snap
d, tag = Path(sys.argv[1]), sys.argv[2]
s16 = lambda v: v - 65536 if v & 0x8000 else v
page = lambda r: int.from_bytes(r[0x2df78:0x2df7c], 'big')
rams = [ram_from_snap(d / f'{tag}_{n}.snap') for n in ['base'] + ['f%d' % i for i in range(1, 8)]]
r0 = rams[0]; a = 0x3f768
for k in range(1, 8):
    prev, cur = rams[k - 1], rams[k]
    scr = bytearray(prev[page(prev):page(prev) + 32000])
    while True:
        o = s16(int.from_bytes(r0[a:a + 2], 'big')); a += 2
        if o < 0: break
        n = int.from_bytes(r0[a:a + 2], 'big') + 1; a += 2
        for _ in range(n):
            scr[o:o + 4] = r0[a:a + 4]; a += 4; o += 4
    got = cur[page(cur):page(cur) + 32000]
    diff = sum(1 for x, y in zip(scr, got) if x != y)
    print('frame %d: %d of 32000 bytes differ from the model' % (k, diff))
