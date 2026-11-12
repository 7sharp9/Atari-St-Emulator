"""sheet.py - decode and render every BSP model ($8e68/$9066 header) in the model pointer table $4c4ce to a contact sheet."""
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent)); _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
import sys
from model import *
from PIL import ImageFont
pal = palette(); tiles = []; info = []
for i in range(99):
    a = L(0x4c4ce + 4 * i)
    if a < 0x1000 or a > 0x80000: break
    if L(a) not in (0x8e68, 0x9066): info.append((i, hex(a), 'routine %x skipped' % L(a))); continue
    try:
        b = build(a, (0x1800, 0x0800, 0)); m = parse(a, b)
        ext = max(max(abs(x) for x in v) for v in m['vt'][:max(m['nv'], 1)]) or 1
        cz = int(ext * 3.2) + 60
        img, npoly, drawn = render(m, (0, 0, cz), pal, scale=1)
        tiles.append((i, img)); info.append((i, hex(a), 'ok', 'builder %x nv %d planes %d polys %d drawn %d ext %d' % (b['builder'], m['nv'], len(m['planes']), npoly, drawn, ext)))
    except Exception as e:
        info.append((i, hex(a), 'ERR', repr(e)[:80]))
for x in info: print(*x)
cols = 6; rows = (len(tiles) + cols - 1) // cols
sheet = Image.new('RGB', (cols * 258, rows * 130), (0, 0, 0))
from PIL import ImageDraw
for k, (i, img) in enumerate(tiles):
    sheet.paste(img, ((k % cols) * 258, (k // cols) * 130)); ImageDraw.Draw(sheet).text(((k % cols) * 258 + 3, (k // cols) * 130 + 2), str(i), fill=(255, 255, 255))
sheet.save('' + str(area_dir('render')) + '/sheet.png')
