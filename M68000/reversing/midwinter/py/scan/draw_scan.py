"""Diagram: cells numbered in scan order for headings 0, 128 and 256, from the model. usage: draw_scan.py [out.png]
(default: reversing/midwinter/scan_order.png)"""
import sys, os, math
from common import ROOT
import scan_model as M
from PIL import Image, ImageDraw, ImageFont
C = 30; R = 8; N = 2 * R + 1
def font(sz):
    for p in ('/System/Library/Fonts/Menlo.ttc', '/System/Library/Fonts/Helvetica.ttc'):
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()
f = font(11); fb = font(15)
panels = [(0, 'heading 0 (octant 0): faces +y'), (128, 'heading 128 (octant 1): faces +x+y'), (256, 'heading 256 (octant 2): faces +x')]
W = N * C + 30; H = N * C + 70
img = Image.new('RGB', (W * len(panels), H), 'white'); d = ImageDraw.Draw(img)
for pi, (h, title) in enumerate(panels):
    L = M.scan(h); ox = pi * W + 15; oy = 40
    d.text((ox, 10), title + '  (%d cells)' % len(L), fill='black', font=fb)
    for i, (x, y) in enumerate(L):
        px = ox + (x + R) * C; py = oy + (R - y) * C
        k = max(abs(x), abs(y)); shade = int(235 - k * 14)
        col = (shade, shade + 10 if shade < 245 else 255, 255) if (x, y) != (0, 0) else (255, 200, 120)
        d.rectangle([px, py, px + C - 1, py + C - 1], fill=col, outline=(120, 120, 120))
        t = str(i); w = d.textlength(t, font=f); d.text((px + (C - w) / 2, py + C / 2 - 6), t, fill='black', font=f)
    a = h / 1024 * 2 * math.pi; cx = ox + (R + .5) * C; cy = oy + (R + .5) * C
    ex = cx + math.sin(a) * C * 3.2; ey = cy - math.cos(a) * C * 3.2
    d.line([cx, cy, ex, ey], fill=(200, 0, 0), width=3); d.ellipse([ex-4, ey-4, ex+4, ey+4], fill=(200, 0, 0))
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'reversing', 'midwinter', 'scan_order.png')
img.save(out); print('wrote', out, img.size)
