import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent)); _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
import sys
from model import *
from PIL import ImageDraw
pal = palette(); addr = int(sys.argv[1], 16); out = sys.argv[2]
yaws = [0, 0x2000, 0x4000, 0x6000, 0x8000, 0xa000, 0xc000, 0xe000]
tiles = []
for y in yaws:
    b = build(addr, (y, int(sys.argv[3], 0), 0)); m = parse(addr, b)
    ext = max(max(abs(x) for x in v) for v in m['vt'][:max(m['nv'], 1)]) or 1
    img, n, d = render(m, (0, 0, int(ext * 3.2) + 60), pal, scale=1); tiles.append((y, img, n, d))
sheet = Image.new('RGB', (4 * 258, 2 * 130))
for k, (y, img, n, d) in enumerate(tiles):
    sheet.paste(img, ((k % 4) * 258, (k // 4) * 130)); ImageDraw.Draw(sheet).text(((k % 4) * 258 + 3, (k // 4) * 130 + 2), 'a4=%04x items=%d' % (y, n), fill=(255, 255, 255))
sheet.save(out)
