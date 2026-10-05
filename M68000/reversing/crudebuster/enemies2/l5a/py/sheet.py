"""Contact sheet: sheet.py <out.png> <cols> <scale> <png> ... (nearest-neighbour upscale, 256x240 frames)"""
import sys
from PIL import Image
out, cols, sc = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
ims = [Image.open(p).convert("RGB") for p in sys.argv[4:]]
w, h = ims[0].size
rows = (len(ims) + cols - 1) // cols
S = Image.new("RGB", (cols * w * sc, rows * h * sc))
for i, im in enumerate(ims):
    S.paste(im.resize((w * sc, h * sc), Image.NEAREST), ((i % cols) * w * sc, (i // cols) * h * sc))
S.save(out)
