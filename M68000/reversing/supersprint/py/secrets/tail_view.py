"""tail_view.py - quick-look renders of SUPER1.DAT 0x2f00..0x4280 (never consumed at boot): 1bpp at several row widths."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh import sscfg, AGENT
from PIL import Image
d = open(os.path.join(sscfg.FILES, 'SUPER1.DAT'), 'rb').read()
for start, end, name in ((0x2f00, 0x3a80, 'a'), (0x3c8c, 0x4280, 'b')):
    seg = d[start:end]
    rows = []
    for w in (2, 4, 6, 8):
        n = len(seg) // w
        img = Image.new('L', (w * 8, n))
        px = img.load()
        for y in range(n):
            for x in range(w * 8):
                px[x, y] = 255 if seg[y * w + x // 8] >> (7 - x % 8) & 1 else 0
        rows.append(img)
    sheet = Image.new('L', (sum(i.width for i in rows) + 8 * len(rows), max(i.height for i in rows)), 128)
    x = 0
    for i in rows:
        sheet.paste(i, (x, 0)); x += i.width + 8
    sheet.save(os.path.join(AGENT, 'super1_tail_%s.png' % name))
    print(name, sheet.size)
