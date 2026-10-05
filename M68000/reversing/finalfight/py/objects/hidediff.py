#!/usr/bin/env python3
"""hidediff.py <ref.png> <hidden.png> [out.png] : pixels that differ between a reference screenshot and the one with a record hidden (its sprite), as a bounding box, count and
optionally a crop saved to out.png. Needs numpy and Pillow (M68000/.venv/bin/python)."""
import sys
import numpy as np
from PIL import Image
a = np.array(Image.open(sys.argv[1]).convert('RGB')).astype(int); b = np.array(Image.open(sys.argv[2]).convert('RGB')).astype(int)
d = (np.abs(a - b).sum(axis=2) > 0)
n = int(d.sum())
if n == 0: print('no pixel differs'); sys.exit(0)
ys, xs = np.where(d)
print('%d pixels differ; bbox x %d..%d y %d..%d (%d x %d)' % (n, xs.min(), xs.max(), ys.min(), ys.max(), xs.max() - xs.min() + 1, ys.max() - ys.min() + 1))
if len(sys.argv) > 3:
    x0, x1, y0, y1 = max(xs.min() - 8, 0), min(xs.max() + 9, a.shape[1]), max(ys.min() - 8, 0), min(ys.max() + 9, a.shape[0])
    im = Image.fromarray(np.concatenate([a[y0:y1, x0:x1], b[y0:y1, x0:x1]], axis=1).astype('uint8')); im = im.resize((im.width * 3, im.height * 3), Image.NEAREST); im.save(sys.argv[3])
