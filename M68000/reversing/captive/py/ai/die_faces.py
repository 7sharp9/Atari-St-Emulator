"""Render the DIE's faces: federation's own $12168 (char -> pip layout from the table at $121f8) is called for each char
under stserver, and the 16x16 cell it draws in the Amiga-planar panel sheet at 15782(A6) (4 planes of 8000 bytes, 40-byte
rows; destination offset 3826) is decoded with the snapshot's palette.
Usage: die_faces.py <snap> <out.png>   (chars $20..$2b are the random faces, $30..$33 the coded-door hints)"""
import os, sys, pathlib
here = pathlib.Path(__file__).resolve()
R = str(next(p for p in here.parents if (p / 'tools' / 'rdis.py').exists()))
sys.path.insert(0, os.path.join(R, 'tools'))
from stclient import StServer
from gfxview import load_video_regs
from PIL import Image, ImageDraw
CH = list(range(0x20, 0x2c)) + list(range(0x30, 0x34))
snap, out = sys.argv[1], sys.argv[2]
vr = load_video_regs(snap)
pal = vr['palette_words']
col = lambda w: (((w >> 8) & 7) * 36, ((w >> 4) & 7) * 36, (w & 7) * 36)  # as tools/snap_render.py
s = StServer(R); s('load', snapshot=snap)
sheet = int.from_bytes(s.read(0x1b5ce + 15782, 4), 'big')
base = s('fork')['id']
X0, Y0, W, H = 3826 % 40 - 2, 3826 // 40 - 1, 6, 18   # bytes, rows around the drawn cell
img = Image.new('RGB', (len(CH) * (W * 8 + 4), H + 12), (40, 40, 40))
d = ImageDraw.Draw(img)
for i, ch in enumerate(CH):
    s('restore', id=base); s.sp = None
    s.call(0x12168, d0=ch)
    planes = [s.read(sheet + p * 8000 + Y0 * 40, H * 40) for p in range(4)]
    for y in range(H):
        for xb in range(W):
            for bit in range(8):
                v = sum(((planes[p][y * 40 + X0 + xb] >> (7 - bit)) & 1) << p for p in range(4))
                img.putpixel((i * (W * 8 + 4) + xb * 8 + bit, y), col(pal[v]))
    d.text((i * (W * 8 + 4) + 4, H), f'{ch:02x}', fill=(255, 255, 0))
s.close()
img.resize((img.width * 4, img.height * 4), Image.NEAREST).save(out)
print(out, 'sheet', hex(sheet))
