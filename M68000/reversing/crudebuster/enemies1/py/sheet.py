"""Contact sheet of PNG snapshots: sheet.py out.png cols png... (each 256x240; cropping by --crop x0,y0,x1,y1)"""
import sys
from PIL import Image
out, cols = sys.argv[1], int(sys.argv[2]); fs = sys.argv[3:]
ims = [Image.open(f) for f in fs]
rows = (len(ims) + cols - 1) // cols
W = Image.new("RGB", (256 * cols, 240 * rows))
for i, im in enumerate(ims): W.paste(im, ((i % cols) * 256, (i // cols) * 240))
W.save(out)
