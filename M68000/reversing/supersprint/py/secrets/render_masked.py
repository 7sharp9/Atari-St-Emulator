"""render_masked.py LO HI [ROWS_PER_COL=256] [WORDS_PER_ROW=4] - SUPER.DAT[LO:HI] as 16px-wide masked sprites: words per row = mask + 3 planes
(default 4 words = 8 bytes/row) on a checker background; columns of ROWS_PER_COL rows."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh import *
from PIL import Image
lo = int(sys.argv[1], 16); hi = int(sys.argv[2], 16)
rpc = int(sys.argv[3]) if len(sys.argv) > 3 else 256
wpr = int(sys.argv[4]) if len(sys.argv) > 4 else 4
d = open(os.path.join(sscfg.FILES, 'SUPER.DAT'), 'rb').read()[lo:hi]
pal = bytes.fromhex('0000 0315 0156 0466 0444 0775 0663 0563 0333 0444 0700 0771 0525 0555 0677 0777'.replace(' ', ''))
P = []
for i in range(16):
    w = int.from_bytes(pal[2*i:2*i+2], 'big'); P.append(tuple(((w >> s) & 7) * 255 // 7 for s in (8, 4, 0)))
rows = len(d) // (wpr * 2)
cols = (rows + rpc - 1) // rpc
img = Image.new('RGB', (cols * 20, rpc), (90, 0, 90)); px = img.load()
for y in range(rows):
    c, yy = divmod(y, rpc)
    ws = [int.from_bytes(d[y * wpr * 2 + 2*k: y * wpr * 2 + 2*k + 2], 'big') for k in range(wpr)]
    mask = ws[0]; planes = ws[1:]
    for b in range(16):
        if not (mask >> (15 - b)) & 1:      # mask bit clear = opaque? try both: here set = transparent
            v = 0
            for p in range(len(planes)): v |= ((planes[p] >> (15 - b)) & 1) << p
            px[c * 20 + b, yy] = P[v]
out = os.path.join(AGENT, 'masked_%x_%x.png' % (lo, hi))
img.resize((img.width * 2, img.height * 2), Image.NEAREST).save(out); print(out, img.size)
