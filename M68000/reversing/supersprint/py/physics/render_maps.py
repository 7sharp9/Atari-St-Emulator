"""render_maps.py - render the 3-plane 1bpp collision bitmap at [-94(A4)] and the 40x25 surface map at [-1910(A4)]
from a snapshot's RAM (offline, no emulator). Usage: render_maps.py [snap] [outprefix]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pl import *
import numpy as np
from PIL import Image

def planes(r, base):
    """3 planes of 8000 bytes, 40 bytes/row, MSB = leftmost pixel -> arrays [3][200][320] of 0/1"""
    out = []
    for p in range(3):
        raw = np.frombuffer(r.bytes(base + p*8000, 8000), dtype=np.uint8).reshape(200, 40)
        out.append(np.unpackbits(raw, axis=1))
    return out

def main():
    snap = sys.argv[1] if len(sys.argv) > 1 else sscfg.SNAP_RACE
    pre = sys.argv[2] if len(sys.argv) > 2 else os.path.join(OUT, 'collision')
    r = Ram(snap)
    base = r.gl(-94)
    P = planes(r, base)
    for i, p in enumerate(P):
        print('plane', i, 'set pixels', int(p.sum()), 'of', p.size)
        Image.fromarray((1 - p) * 255).convert('L').resize((640, 400), Image.NEAREST).save(pre + '_plane%d.png' % i)
    # composite: RGB = planes 0,1,2
    rgb = np.stack([P[0], P[1], P[2]], axis=-1) * 255
    Image.fromarray(rgb.astype(np.uint8)).resize((640, 400), Image.NEAREST).save(pre + '_rgb.png')
    # distinct 3-bit codes
    code = P[0] + 2*P[1] + 4*P[2]
    print('code histogram', {int(k): int(v) for k, v in zip(*np.unique(code, return_counts=True))})
    # surface map
    sm = np.frombuffer(r.bytes(r.gl(-1910), 1000), dtype=np.uint8).reshape(25, 40)
    print('surface map value histogram', {hex(int(k)): int(v) for k, v in zip(*np.unique(sm, return_counts=True))})
    np.save(pre + '_surface.npy', sm)

main()
