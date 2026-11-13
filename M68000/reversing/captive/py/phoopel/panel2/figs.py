"""[reversing/captive/py/phoopel/panel2/figs.py] Builds fig_kind3_depths.png (lock 16) and fig_kind2_depths.png (lock 12): the panel at
depth 1, 2, 3 in front of W, cropped from the scene.py renders (run `scene.py 16 1,0 2,0 3,0` and `scene.py 12 1,0 2,0 3,0` first).
Output in scratchpad/captive/phoopel/panel2/."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT
from PIL import Image
box = (10, 28, 182, 150)
for name, lock in (('fig_kind3_depths.png', 16), ('fig_kind2_depths.png', 12)):
    ims = [Image.open(os.path.join(OUT, f'scene_L{lock}_d{d}_l0.png')).crop(box).resize((172 * 3, 122 * 3), Image.NEAREST) for d in (1, 2, 3)]
    m = Image.new('RGB', (172 * 3 * 3 + 8, 122 * 3), 'white')
    for k, i in enumerate(ims): m.paste(i, (k * (172 * 3 + 4), 0))
    m.save(os.path.join(OUT, name)); print(name)
