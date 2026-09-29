"""Render the shop screenshots of hop4 from the driven snapshots (full frame x2 via tools/snap_render.py)."""
import os, subprocess, sys
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))
OUT = os.path.join(ROOT, 'scratchpad/impossamole/agents/hop4')
from PIL import Image
shots = {'seg6b_shop_wait': 'mole_in_shaft', 'seg7b_shop_enter': 'shop_room', 'seg8b_shop_touch': 'shop_bubble_75_worm_can',
         'seg9b_shop_toomuch': 'shop_bubble_too_much', 'shop_exit_bubble': 'shop_bubble_exit'}
for snap, name in shots.items():
    png = os.path.join(OUT, name + '.png')
    subprocess.run([sys.executable, os.path.join(ROOT, 'tools/snap_render.py'), os.path.join(OUT, snap + '.snap'), png],
                   check=True, cwd=ROOT, stdout=subprocess.DEVNULL)
    im = Image.open(png)
    im.resize((im.width * 2, im.height * 2), Image.NEAREST).save(png)
print('ok')
