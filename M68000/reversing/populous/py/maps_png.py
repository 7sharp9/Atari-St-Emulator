"""maps_png.py - render the terrain maps of a snapshot (or a callcap result) as PNG heatmaps.
Proves the layouts: $34be4 65x65 words (corner heights), $33be4/$36e78/$3c522/$37fd4/$38fd8 64x64 bytes."""
import sys; sys.setrecursionlimit(100000)
from PIL import Image, ImageDraw
from popmem import *
SC = 6
def heat(vals, n, vmax, path, pal=None):
    im = Image.new('RGB', (n*SC, n*SC)); d = ImageDraw.Draw(im)
    for i, v in enumerate(vals):
        x, y = i % n, i // n
        if pal: c = pal(v)
        else:
            t = min(v, vmax)/vmax if vmax else 0
            c = (0, 40, 140) if v == 0 else (int(60+195*t), int(140+100*t), int(40+60*t))
        d.rectangle([x*SC, y*SC, x*SC+SC-1, y*SC+SC-1], fill=c)
    im.save(path)
def shape_pal(v):
    if v == 0: return (0, 40, 140)             # sea
    if 1 <= v <= 14: return (90, 160, 60)      # slope above sea level
    if v == 0xf: return (60, 200, 60)          # flat land
    if 0x11 <= v <= 0x1e: return (200, 190, 120)   # shore slope (base altitude 0)
    if v in (0x1f, 0x20): return (230, 230, 90)    # built-up flat (house/town field, $10366)
    if 0x2f <= v <= 0x31: return (130, 130, 130)   # rock
    if v == 0x35: return (120, 60, 140)        # swamp
    if v == 0x42: return (255, 120, 0)         # ruin/burnt field ($108b8)
    return (255, 0, 255)
def feat_pal(v):
    if v == 0: return (0, 0, 0)
    if 0x32 <= v <= 0x34: return (0, 150, 0)   # trees
    if v == 0x2a: return (255, 255, 255)
    return (255, 200, 0)                        # buildings / other (people agent)
def dump(m, tag):
    H = [sw(m, 0x34be4+2*i) for i in range(65*65)]
    heat(H, 65, 8, 'h_%s.png' % tag)
    heat(list(m[0x33be4:0x33be4+4096]), 64, 7, 'alt_%s.png' % tag)
    heat(list(m[0x36e78:0x36e78+4096]), 64, 0, 'shape_%s.png' % tag, shape_pal)
    heat(list(m[0x3c522:0x3c522+4096]), 64, 0, 'feat_%s.png' % tag, feat_pal)
    heat([1 if v else 0 for v in m[0x37fd4:0x37fd4+4096]], 64, 0, 'occ_%s.png' % tag,
         lambda v: (255, 255, 255) if v else (0, 0, 0))
if __name__ == '__main__':
    base = ram('../../game_start.snap')
    dump(base, 'game_start'); dump(ram('../../g90.snap'), 'g90')
    for js, tag in (('cc_b316_w0.json', 'gen_w0'), ('cc_b316_w1235.json', 'gen_w1235'), ('cc_b316_c1234.json', 'gen_c1234')):
        dump(apply_callcap(base, js)[0], tag)
    # raise/lower before-after difference image (cmd_raise.snap = raise at (11,16))
    a = [sw(base, 0x34be4+2*i) for i in range(65*65)]
    b = [sw(ram('cmd_raise.snap'), 0x34be4+2*i) for i in range(65*65)]
    heat([y-x for x, y in zip(a, b)], 65, 0, 'raise_11_16_delta.png',
         lambda v: (0, 0, 0) if v == 0 else (255, 60*(3-min(v, 3)), 0))
