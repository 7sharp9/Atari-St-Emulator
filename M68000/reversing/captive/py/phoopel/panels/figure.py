"""figure.py: panels_kinds.png (one row per key kind 0-3: cover, opened, code set; locks 9, 17, 0, 4) and
doors_kinds.png (door kinds 0, 1, 2 seen from the cell beside D, shut and open; locks 9, 7, 1), cropped to the
view window and scaled 3x, from panels.py's renders under scratchpad/captive/phoopel/panels/lock<N>/."""
import os
from PIL import Image
R = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(R, 'tools', 'rdis.py')):
    R = os.path.dirname(R)
D = os.path.join(R, 'scratchpad', 'captive', 'phoopel', 'panels')
crop = lambda p: Image.open(os.path.join(D, p)).convert('RGB').crop((30, 55, 180, 170)).resize((450, 345), Image.NEAREST)

def grid(rows, out):
    o = Image.new('RGB', (len(rows[0]) * 456 - 6, len(rows) * 351 - 6), (0, 0, 0))
    for r, row in enumerate(rows):
        for c, p in enumerate(row):
            o.paste(crop(p), (c * 456, r * 351))
    o.save(os.path.join(D, out))

grid([[f'lock{n}/code_before.png', f'lock{n}/code_open.png', f'lock{n}/code_after.png'] for n in (9, 17, 0, 4)],
     'panels_kinds.png')
grid([[f'lock{n}/walk_shut_view.png', f'lock{n}/walk_open_view.png'] for n in (9, 7, 1)], 'doors_kinds.png')
