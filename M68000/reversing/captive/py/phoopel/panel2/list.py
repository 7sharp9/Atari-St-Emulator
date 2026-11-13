"""[reversing/captive/py/phoopel/panel2/list.py; `uv run python -I reversing/captive/py/phoopel/panel2/list.py`] lock list of base13.snap with W side, key/door kind, code and the tiles ahead of W."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
s = StServer(R); s('load', snapshot=SNAP)
tile = lambda x, y: s.read(TILES + y * 64 + x, 1)[0]
for l in lock_list(s):
    x, y = l['W']; t = tile(x, y); f = t & 3
    cells = []
    for d in range(1, 8):
        cx, cy = x - d*VEC[f][0], y - d*VEC[f][1]
        if not (0 <= cx < 64 and 0 <= cy < 32): break
        cells.append(f'{tile(cx,cy):02x}')
    print(l['i'], 'W', l['W'], f'tile {t:02x} face {f}', 'key', l['key'], 'door', l['door'], f"code {l['code']:04x}", 'ahead tiles', ' '.join(cells))
s.close()
