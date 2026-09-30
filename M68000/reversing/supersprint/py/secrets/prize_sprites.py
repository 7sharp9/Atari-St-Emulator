"""prize_sprites.py - render the 16 winner's-circle prize-animation sprites (48x32, 4 bitplanes, 768 bytes each, table base
[-118(A4)]) from snap/pre_winner.snap with the palette in force at the winner's circle; sheet -> prize_sprites.png."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh import *
from PIL import Image
r = R(os.path.join(AGENT, 'snap', 'pre_winner.snap'))
r.cmd('u 1ae68 3000000')   # palette fade-in of the winner's circle has run by here
r.cmd('s 400000')
base = r.g32(-118)
print('sprite table base', hex(base))
pal = r.mem(0xffff8240, 32)
print('palette', pal.hex(' '))
data = r.mem(base, 16 * 768)
r.close()
def rgb(i):
    w = int.from_bytes(pal[2*i:2*i+2], 'big')
    return tuple(((w >> s) & 7) * 255 // 7 for s in (8, 4, 0))
PAL = [rgb(i) for i in range(16)]
def decode(buf, w16, h, planes=4):
    img = Image.new('RGB', (w16 * 16, h))
    px = img.load()
    off = 0
    for y in range(h):
        for wd in range(w16):
            ws = [int.from_bytes(buf[off + 2*p: off + 2*p + 2], 'big') for p in range(planes)]
            off += 2 * planes
            for b in range(16):
                v = 0
                for p in range(planes):
                    v |= ((ws[p] >> (15 - b)) & 1) << p
                px[wd * 16 + b, y] = PAL[v]
    return img
sheet = Image.new('RGB', (4 * 52, 4 * 36), (40, 40, 40))
for i in range(16):
    im = decode(data[i * 768:(i + 1) * 768], 3, 32)
    sheet.paste(im, ((i % 4) * 52 + 2, (i // 4) * 36 + 2))
out = os.path.join(AGENT, 'prize_sprites.png')
sheet = sheet.resize((sheet.width * 3, sheet.height * 3), Image.NEAREST)
sheet.save(out)
print('wrote', out)
