#!/usr/bin/env python3
"""shiftdiff.py <png_ref> <png> [dymax]: for the whole frame and for horizontal bands, find the vertical shift dy (-dymax..dymax) of <png> relative to <png_ref>
that minimises the pixel difference (rows 32..223 compared; the HUD rows 0..31 are excluded). Prints per-band best dy and the residual.
Needs numpy + pillow: run with M68000/.venv/bin/python."""
import sys
import numpy as np
from PIL import Image
def load(p): return np.asarray(Image.open(p).convert('RGB')).astype(np.int16)
a, b = load(sys.argv[1]), load(sys.argv[2])
dm = int(sys.argv[3]) if len(sys.argv) > 3 else 6
H = a.shape[0]
def best(y0, y1):
    res = []
    for dy in range(-dm, dm + 1):
        ya0, ya1 = max(y0, y0 + dy), min(y1, y1 + dy)
        if ya1 - ya0 < 4: continue
        d = np.abs(a[ya0 - dy:ya1 - dy] - b[ya0:ya1]).sum() / max(1, (ya1 - ya0))
        res.append((d, dy))
    res.sort()
    return res[0], dict((dy, round(d)) for d, dy in res)
(d0, dy0), allr = best(32, H)
zero = allr.get(0)
print('whole frame: best dy=%d resid=%d (dy=0 resid=%s)' % (dy0, d0, zero))
for y0 in range(32, H, 32):
    (d, dy), _ = best(y0, min(H, y0 + 32))
    print('  rows %3d-%3d: best dy=%d resid=%d' % (y0, min(H, y0 + 32), dy, d))
