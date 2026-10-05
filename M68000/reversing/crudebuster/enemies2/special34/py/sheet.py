"""Contact sheet of snapshot PNGs: sheet.py <out.png> <cols> <png>...   (each tile 256 wide scaled x1; labels with file stem)"""
import sys
from PIL import Image, ImageDraw
out, cols, files = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
ims = [Image.open(f).convert("RGB") for f in files]
w, h = ims[0].size
rows = (len(ims) + cols - 1) // cols
sh = Image.new("RGB", (w * cols, h * rows))
for i, (im, f) in enumerate(zip(ims, files)):
    sh.paste(im, ((i % cols) * w, (i // cols) * h))
    ImageDraw.Draw(sh).text(((i % cols) * w + 3, (i // cols) * h + 3), f.split("/")[-1][:-4], fill=(255, 255, 0))
sh.save(out)
print(out, sh.size)
