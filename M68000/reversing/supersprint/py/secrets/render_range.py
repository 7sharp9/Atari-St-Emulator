"""render_range.py LO HI [BYTES_PER_ROW=160] [OUT] - render SUPER.DAT[LO:HI] as 4-plane interleaved words (16px groups), using the
winner's-circle palette of pre_winner.snap, for a quick look at unused ranges."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh import *
from PIL import Image
lo = int(sys.argv[1], 16); hi = int(sys.argv[2], 16); bpr = int(sys.argv[3]) if len(sys.argv) > 3 else 160
out = sys.argv[4] if len(sys.argv) > 4 else os.path.join(AGENT, 'range_%x_%x.png' % (lo, hi))
d = open(os.path.join(sscfg.FILES, 'SUPER.DAT'), 'rb').read()[lo:hi]
pal = bytes.fromhex('0000 0315 0156 0466 0444 0775 0663 0563 0333 0444 0700 0771 0525 0555 0677 0777'.replace(' ', ''))
P = []
for i in range(16):
    w = int.from_bytes(pal[2*i:2*i+2], 'big'); P.append(tuple(((w >> s) & 7) * 255 // 7 for s in (8, 4, 0)))
W = bpr // 8 * 16; H = len(d) // bpr
img = Image.new('RGB', (W, H)); px = img.load()
for y in range(H):
    for xb in range(bpr // 8):
        o = y * bpr + xb * 8
        ws = [int.from_bytes(d[o + 2*p:o + 2*p + 2], 'big') for p in range(4)]
        for b in range(16):
            v = 0
            for p in range(4): v |= ((ws[p] >> (15 - b)) & 1) << p
            px[xb * 16 + b, y] = P[v]
img.save(out); print(out, img.size)
