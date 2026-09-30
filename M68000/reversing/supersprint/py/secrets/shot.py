"""shot.py - render the current ST low-res screen of a running Repl (video base from $ffff8201/03, palette $ffff8240) to a PIL image."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh import *
from PIL import Image

def grab(r, base=None, pal=None):
    if base is None:
        hi = r.w8(0xffff8201); mid = r.w8(0xffff8203)
        base = (hi << 16) | (mid << 8)
    if pal is None:
        pal = r.mem(0xffff8240, 32)
    scr = r.mem(base, 32000)
    P = []
    for i in range(16):
        w = int.from_bytes(pal[2*i:2*i+2], 'big')
        P.append(tuple(((w >> s) & 7) * 255 // 7 for s in (8, 4, 0)))
    img = Image.new('RGB', (320, 200)); px = img.load()
    for y in range(200):
        for xb in range(20):
            o = y * 160 + xb * 8
            ws = [int.from_bytes(scr[o + 2*p:o + 2*p + 2], 'big') for p in range(4)]
            for b in range(16):
                v = 0
                for p in range(4):
                    v |= ((ws[p] >> (15 - b)) & 1) << p
                px[xb * 16 + b, y] = P[v]
    return img, base

if __name__ == '__main__':
    snap, out = sys.argv[1], sys.argv[2]
    r = R(snap)
    if len(sys.argv) > 3: r.cmd('s %s' % sys.argv[3])
    img, base = grab(r)
    img.save(out); print('saved', out, 'base %x' % base)
    r.close()
