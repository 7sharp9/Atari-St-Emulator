#!/usr/bin/env python3
"""render_pictures.py: the 20 picture islands (special table $16a58, islands 5, 10, ..., 100) as the game builds
them, from island_model.py's picture path and the disk image alone (the table is read from isl/ent1.snap).
Sea 4 blue, coast 5 sand, land 6/7 green; the centre 150 x 150 cells of each 256 x 256 map.

usage: uv run python reversing/archipelagos/py/render_pictures.py [out.png]   (default: ../picture_islands.png)
"""
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import island_model as im
from gfxview import load_ram
from PIL import Image, ImageDraw

out_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, '..', 'picture_islands.png')
ram, _ = load_ram(os.path.join(im.d, 'scratchpad', 'archipelagos', 'isl', 'ent1.snap'))
disk = open(im.DISK, 'rb').read()
pal = {4: (28, 60, 120), 5: (214, 196, 140), 6: (70, 130, 60), 7: (60, 115, 52)}
C, pad, cols = 150, 6, 5
sheet = Image.new('RGB', (cols * (C + pad) + pad, 4 * (C + pad + 14) + pad), (250, 250, 248))
dr = ImageDraw.Draw(sheet)
for k, N in enumerate(range(5, 101, 5)):
    r = bytearray(ram); r[0x1d566:0x1d568] = N.to_bytes(2, 'big')
    cells = im.Model(r).run(disk)
    img = Image.new('RGB', (256, 256)); img.putdata([pal[v] for v in cells])
    o = (256 - C) // 2
    x = pad + (k % cols) * (C + pad); y = pad + (k // cols) * (C + pad + 14)
    sheet.paste(img.crop((o, o, o + C, o + C)), (x, y + 14))
    dr.text((x, y + 1), f'island {N}', fill=(30, 30, 30))
sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(out_path)
print(out_path)
