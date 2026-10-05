"""sheet.py out.png cols scale img1 img2 ... : contact sheet with the file stem as label."""
import sys, os
from PIL import Image, ImageDraw
out, cols, scale = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); fs = sys.argv[4:]
ims = [Image.open(f).convert("RGB") for f in fs]
w, h = ims[0].size; w *= scale; h *= scale
rows = (len(ims) + cols - 1) // cols
S = Image.new("RGB", (cols * w, rows * (h + 12)), (30, 30, 30))
d = ImageDraw.Draw(S)
for i, (f, im) in enumerate(zip(fs, ims)):
    x, y = (i % cols) * w, (i // cols) * (h + 12)
    S.paste(im.resize((w, h), Image.NEAREST), (x, y + 12)); d.text((x + 2, y), os.path.splitext(os.path.basename(f))[0], fill=(255, 255, 0))
S.save(out)
