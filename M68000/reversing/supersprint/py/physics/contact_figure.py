"""contact_figure.py - figure: the collision window while the human car touches the left wall (live), with the $bda4 probe regions and result.
Runs the car west at fire (as wall_hit_trace), stops at $bda4 for car 1 when x <= 18, snapshots and draws, for the 32x12 window at the car:
  dark = wall plane bit (plane 1), grey = opaque sprite pixels, red = window bits (sprite AND wall) -> collision; outlines = bda4 probes."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pl import *
import ssport as P
from PIL import Image, ImageDraw

h = Harness(sscfg.SNAP_RACE)
h.cmd('kbd fe 80')
h.cmd('s 300')
found = False
for frame in range(200):
    if h.run_to(0xdf18, 1) is None:
        break
    for _ in range(4):
        regs = h.run_to(0xbda4, 1)
        out, _ = h.cmd('m %x 2' % (regs['A7'] + 4))
        car = int(''.join(l.split()[0] + l.split()[1] for l in out if HEXLINE.match(l.strip())), 16)
        if car == 1:
            mm = P.Mem(h.snap_ram().b)
            if P.obstacle_test(mm, 1) != 0:
                found = True
            break
    if found:
        break
r = h.snap_ram()
h.close()
m = P.Mem(r.b)
c = 1
x, y, hd = m.a(P.X, c), m.a(P.Y, c), m.a(P.HEAD, c)
code = P.obstacle_test(m, c)
print('car', c, 'x', x, 'y', y, 'heading', hd, 'bda4 code', code, 'CODEMAP ->', m.g(P.CODEMAP + 2 * code))
bx = x & ~15
S = 14
W, H = 32, 12
wall = []
base = m.rl(A4 - 94) + 8000
for row in range(H):
    v = m.rl(base + (y + row) * 40 + bx // 8) if False else (m.rw(base + (y + row) * 40 + bx // 8) << 16) | m.rw(base + (y + row) * 40 + bx // 8 + 2)
    wall.append(v)
win = [m.rl(A4 + P.WIN + 4 * i) for i in range(12)]
sp = m.rl(A4 - 3602) + (((c * 16 + hd) + (0x40 if m.au(P.ISDRONE, c) else 0)) << 8)
ops = []
for row in range(12):
    pl = [m.rl(sp + 16 * row + 4 * k) for k in range(4)]
    pl = [P.ror32(v, x & 15) for v in pl]
    ops.append(((~pl[3]) | pl[0] | pl[1] | pl[2]) & 0xffffffff)
ent = A4 + P.MASKS + (hd << 4)
off1, off2, m1, m2 = (m.rl(ent + 4 * k) for k in range(4))
m1s, m2s = m1 >> (x & 15), m2 >> (x & 15)
im = Image.new("RGB", (W * S + 20 + 260, H * S + 60), (25, 25, 25))
d = ImageDraw.Draw(im)
for row in range(H):
    for col in range(W):
        bit = lambda v: (v >> (31 - col)) & 1
        px, py = 10 + col * S, 30 + row * S
        colr = (40, 40, 48)
        if bit(wall[row]):
            colr = (95, 95, 120)
        if bit(ops[row]):
            colr = (170, 170, 170) if not bit(wall[row]) else (150, 120, 120)
        if bit(win[row]):
            colr = (230, 40, 40)
        d.rectangle([px, py, px + S - 2, py + S - 2], fill=colr)
r1, r2 = off1 // 4, off2 // 4
for col in range(32):
    for row in range(r1, r2):
        if (m1s >> (31 - col)) & 1:
            d.rectangle([10 + col * S, 30 + row * S, 10 + col * S + S - 2, 30 + row * S + S - 2], outline=(255, 160, 0), width=2)
        if (m2s >> (31 - col)) & 1:
            d.rectangle([10 + col * S, 30 + row * S, 10 + col * S + S - 2, 30 + row * S + S - 2], outline=(80, 200, 255), width=2)
d.rectangle([10, 30 + r1 * S, 10 + W * S - 2, 30 + r1 * S + S - 2], outline=(255, 60, 60), width=2)
d.rectangle([10, 30 + r2 * S, 10 + W * S - 2, 30 + r2 * S + S - 2], outline=(60, 255, 60), width=2)
d.text((10, 6), 'car %d at (%d,%d) heading %d: window (red) = sprite AND wall plane; bda4 code=%d -> push heading %d' % (c, x, y, hd, code, m.g(P.CODEMAP + 2 * code)), fill=(255, 255, 255))
d.text((10, H * S + 38), 'dark blue = wall plane bit, grey = opaque sprite, red = overlap; red/green rows = N/S edge tests, orange/blue columns = W/E edge tests (x&15=%d)' % (x & 15), fill=(255, 255, 255))
im.save(os.path.join(OUT, 'contact_window.png'))
