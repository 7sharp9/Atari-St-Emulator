"""Contact sheet of snapshots: sheet.py <out.png> <cols> <png...> (PIL from M68000/.venv)"""
import sys
from PIL import Image, ImageDraw
out, cols, fs = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
ims = [Image.open(f).convert("RGB") for f in fs]
w, h = ims[0].size
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (w * cols, h * rows))
d = ImageDraw.Draw(sheet)
for i, (f, im) in enumerate(zip(fs, ims)):
    sheet.paste(im, ((i % cols) * w, (i // cols) * h))
    d.text(((i % cols) * w + 2, (i // cols) * h + 2), f.split("/")[-1][1:-4], fill=(255, 255, 0))
sheet.save(out); print(len(ims), sheet.size)
