"""sheet.py out.png in1.png in2.png ... : labelled contact sheet (4 columns)."""
import sys, os
from PIL import Image, ImageDraw
files = sys.argv[2:]; ims = [Image.open(f).convert("RGB") for f in files]
w, h = ims[0].size; cols = 4; rows = (len(ims) + cols - 1) // cols
sh = Image.new("RGB", (cols * w, rows * (h + 12)), (30, 30, 30)); d = ImageDraw.Draw(sh)
for i, (f, im) in enumerate(zip(files, ims)):
    x, y = (i % cols) * w, (i // cols) * (h + 12)
    sh.paste(im, (x, y + 12)); d.text((x + 2, y), os.path.basename(f)[:-4], fill=(255, 255, 0))
sh.save(sys.argv[1])
