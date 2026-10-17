"""render_layout.py: SUPER.DAT file layout (B0..B12 + tail) with the seven round-1 'never consumed' 4 KB blocks marked by their consumer
(found by the flows in data/scan_*.json, census_*.txt)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uc import *
from PIL import Image, ImageDraw
B = [('B0', 0, 3488), ('B1', 0xda0, 9120), ('B2', 0x3140, 7190), ('B3 cars', 0x4d56, 32768), ('B4 tile pack', 0xcd56, 80000), ('B5 sprites', 0x205d6, 30000),
     ('B6', 0x27b06, 3000), ('B7', 0x286be, 3520), ('B8', 0x2947e, 2000), ('B9 prize', 0x29c4e, 12300), ('B10', 0x2cc5a, 480), ('B11', 0x2ce3a, 7100),
     ('B12', 0x2e9f6, 8000), ('tail', 0x30936, 212650 - 0x30936)]
C = {0x3000: ('SELECT TRACK / shop entry (wheel frames)', (230, 120, 40)), 0xf000: ('track 5-8 race start (tile maps)', (60, 140, 230)),
     0x1b000: ('track 5-8 race start (bank-2 tiles)', (60, 140, 230)), 0x23000: ('crash: helicopter sheets', (200, 60, 200)),
     0x24000: ('crash: helicopter sheets', (200, 60, 200)), 0x25000: ('crash: helicopter sheets', (200, 60, 200)), 0x2b000: ('winner animations 2 and 3 (prize frames 6-11)', (60, 190, 90))}
W = 1700; S = W / 212650
img = Image.new('RGB', (W, 330), (24, 24, 24)); d = ImageDraw.Draw(img)
cols = [(90, 90, 90), (120, 120, 120)]
for i, (n, o, l) in enumerate(B):
    d.rectangle([o * S, 40, (o + l) * S, 80], fill=cols[i % 2])
    d.text((o * S + 2, 84 + 12 * (i % 3)), n, fill=(220, 220, 220))
y = 130
for lo, (txt, col) in sorted(C.items()):
    ln = 0x3000 if lo == 0x23000 else 0x1000
    d.rectangle([lo * S, 40, (lo + ln) * S, 80], fill=col)
    if lo in (0x24000, 0x25000): continue
    d.text((10, y), '%06x-%06x  %s' % (lo, lo + ln, txt), fill=col); y += 14
d.text((10, 10), 'SUPER.DAT (212,650 B): the seven 4 KB blocks of round 1 and what consumes them', fill=(255, 255, 255))
img.save(os.path.join(PNG, 'super_dat_candidate_blocks_consumers.png')); print(img.size)
