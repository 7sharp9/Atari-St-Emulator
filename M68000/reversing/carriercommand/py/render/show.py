import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent)); _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
import sys
from model import *
addr = int(sys.argv[1], 16); out = sys.argv[2]; ang = tuple(int(x, 0) for x in sys.argv[3:6]); cz = int(sys.argv[6]); cy = int(sys.argv[7]) if len(sys.argv) > 7 else 0
b = build(addr, ang); m = parse(addr, b)
img, npoly, drawn = render(m, (0, cy, cz), palette())
img.save(out); print(out, 'polys', npoly, 'drawn', drawn, 'planes', len(m['planes']))
