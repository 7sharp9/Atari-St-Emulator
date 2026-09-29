"""Contact strip of bank-2 (32x24) sprite frames from a snapshot (hop4: the mole and its bubble frames).

    uv run python shop_frames.py <snap> <out.png> [first last] [--scale N]
"""
import os, sys
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))
sys.path.insert(0, os.path.join(ROOT, 'reversing/impossamole/py'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import sprites
from PIL import Image, ImageDraw
from pm_export import ram_from_snap
from pathlib import Path

snap, out = sys.argv[1], sys.argv[2]
lo, hi = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (56, 100)
sc = 3
ram = ram_from_snap(Path(snap))
pal = sprites.palette(snap, ram) if 'palette' in dir(sprites) else None
cols = 10
n = hi - lo + 1
cw, ch = 32 * sc + 4, 24 * sc + 16
im = Image.new('RGB', (cols * cw, ((n + cols - 1) // cols) * ch), (40, 40, 40))
d = ImageDraw.Draw(im)
for k, i in enumerate(range(lo, hi + 1)):
    f = sprites.frame_image(ram, 2, i, pal).resize((32 * sc, 24 * sc), Image.NEAREST)
    x, y = (k % cols) * cw + 2, (k // cols) * ch + 14
    im.paste(f, (x, y))
    d.text((x, y - 12), f'{i} ${i:x}', fill=(220, 220, 220))
im.save(out)
