"""hudname.py <snapdir> <tag> <lo> <hi> <step> <out.png> [x0 y0 x1 y1]: stack the HUD enemy-name crop (default x 24..100, y 23..31 of the 384x224 snapshot; the pixel position used by py/namesheet.py)
 of snapshots <tag>_<frame>.png, enlarged x4, labelled with the frame."""
import sys
from PIL import Image, ImageDraw
d, tag, lo, hi, step, out = sys.argv[1:7]
box = tuple(int(x) for x in sys.argv[7:11]) if len(sys.argv) >= 11 else (24, 20, 100, 31)
fr = list(range(int(lo), int(hi) + 1, int(step)))
S = 4
rows = []
for f in fr:
    try: im = Image.open('%s/%s_%05d.png' % (d, tag, f)).convert('RGB').crop(box)
    except Exception: continue
    rows.append((f, im.resize((im.width * S, im.height * S), Image.NEAREST)))
H = rows[0][1].height + 4
sheet = Image.new('RGB', (rows[0][1].width + 70, H * len(rows)), (30, 30, 30))
dr = ImageDraw.Draw(sheet)
for i, (f, im) in enumerate(rows):
    sheet.paste(im, (70, i * H)); dr.text((2, i * H + 10), str(f), fill=(255, 255, 255))
sheet.save(out)
print(out, sheet.size)
