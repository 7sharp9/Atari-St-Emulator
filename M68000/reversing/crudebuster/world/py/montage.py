"""Montage PNGs (2x scale) with labels. usage: montage.py out.png cols f1 f2 ..."""
import sys
from PIL import Image, ImageDraw
out, cols, files = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
ims = [Image.open(f).convert("RGB") for f in files]
w, h = ims[0].size
rows = (len(ims) + cols - 1) // cols
import os
S = int(os.environ.get('S','2'))
sheet = Image.new("RGB", (cols * w * S, rows * (h * S + 14)), (30, 30, 30))
d = ImageDraw.Draw(sheet)
for i, im in enumerate(ims):
    x, y = (i % cols) * w * S, (i // cols) * (h * S + 14)
    sheet.paste(im.resize((w * S, h * S), Image.NEAREST), (x, y + 14))
    d.text((x + 2, y + 1), files[i].split("/")[-1][:60], fill=(255, 255, 0))
sheet.save(out)
