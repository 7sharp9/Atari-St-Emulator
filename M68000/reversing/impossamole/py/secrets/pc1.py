"""E_MOTION.PC1 and PRES_ST.PC1: LSD!-packed Degas PC1 (0x8000 = compressed low res, 16 palette words, PackBits per scanline plane).  Renders PNGs."""
import sys, struct
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
from lsd import depack
from PIL import Image
def unpackbits(src, pos, n):
    out = bytearray()
    while len(out) < n:
        c = src[pos]; pos += 1
        if c < 128:
            k = c + 1; out += src[pos:pos + k]; pos += k
        elif c > 128:
            k = 257 - c; out += bytes([src[pos]]) * k; pos += 1
        # 128 = nop
    return bytes(out[:n]), pos
def decode(o):
    rez = struct.unpack('>H', o[:2])[0]
    pal = struct.unpack('>16H', o[2:34])
    pos = 34
    img = Image.new('RGB', (320, 200))
    px = img.load()
    for y in range(200):
        planes = []
        for p in range(4):
            row, pos = unpackbits(o, pos, 40)
            planes.append(row)
        for x in range(320):
            w = x // 16; b = 15 - (x % 16)
            v = 0
            for p in range(4):
                word = (planes[p][2*w] << 8) | planes[p][2*w+1]
                v |= ((word >> b) & 1) << p
            c = pal[v]
            px[x, y] = (((c >> 8) & 7) * 36, ((c >> 4) & 7) * 36, (c & 7) * 36)
    return rez, pos, img
for n in ('E_MOTION.PC1', 'PRES_ST.PC1'):
    o, *_ = depack(rd(n))
    rez, pos, img = decode(o)
    print(n, 'rez word', hex(rez), 'consumed', pos, 'of', len(o))
    img.save(WORK + '/data/' + n.replace('.PC1', '') + '.png')
