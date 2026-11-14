"""Object graphics at `$67270`, decoded from sel.snap's RAM and matched against its own screen (no emulator run).
A frame is five 1-bit planes one after another (plane-major, W/8 bytes a row, MSB leftmost): colour bits 0..3,
then the mask (1 = draw). Prints, for level 1's three objects, the opaque pixels equal to the framebuffer for
every frame; the exit's score under the other plane orders, layouts and mask polarity; and writes
  <out>/objects_set0.png   every frame of graphics set 0's 12 types, one row a type, 3x, level 1's palette
  <out>/objects_l1.png     the screen (left) and the screen with the three objects repainted from the decode
  <out>/orders.txt         the 144 alternatives on the exit frame
Run from M68000/:
  uv run python reversing/lemmings/py/objgfx.py <out dir>
"""
import itertools, os, struct, sys
sys.path.insert(0, 'tools')
from gfxview import load_ram, load_video_regs
from PIL import Image

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
SNAP = 'scratchpad/lemmings/sel.snap'
ram, _ = load_ram(SNAP)
regs = load_video_regs(SNAP)
def w(a): return struct.unpack_from('>H', ram, a)[0]
def l(a): return struct.unpack_from('>I', ram, a)[0]
PAL = [tuple(((c >> s) & 7) * 36 for s in (8, 4, 0)) for c in regs['palette_words']]
GFX, SLOTS, LIST, TYPES, SCROLL = 0x67270, 0x23044, 0xde90, 0x2752c + 112, w(0x26c06)

def screen_idx(x, y):
    if not (0 <= x < 320 and 0 <= y < 200): return None
    off = regs['base'] + y * 160 + (x // 16) * 8
    return sum(((w(off + p * 2) >> (15 - x % 16)) & 1) << p for p in range(4))

def planes(addr, W, H, layout):
    bpr, res = W // 8, []
    for p in range(5):
        pl = []
        for y in range(H):
            if layout == 'wordil':      # five words per 16 pixels
                row = [(w(addr + y * (W // 16) * 10 + xw * 10 + p * 2) >> (15 - b)) & 1
                       for xw in range(W // 16) for b in range(16)]
            else:                       # 'seq': plane-major; 'rowplane': the five planes' bytes row by row
                o = addr + (p * bpr * H + y * bpr if layout == 'seq' else y * bpr * 5 + p * bpr)
                row = [(ram[o + bx] >> (7 - b)) & 1 for bx in range(bpr) for b in range(8)]
            pl.append(row)
        res.append(pl)
    return res

def decode(addr, W, H, layout='seq', order=(0, 1, 2, 3)):
    pl = planes(addr, W, H, layout)
    return [[sum(pl[order[k]][y][x] << k for k in range(4)) for x in range(W)] for y in range(H)], pl[4]

def match(addr, W, H, ox, oy, layout='seq', order=(0, 1, 2, 3), pol=1):
    idx, mk = decode(addr, W, H, layout, order)
    cells = [(x, y) for y in range(H) for x in range(W) if mk[y][x] == pol]
    return sum(1 for x, y in cells if screen_idx(ox + x, oy + y) == idx[y][x]), len(cells)

def rec(a):
    return dict(frame=w(a + 2), n=w(a + 4), W=w(a + 6), H=w(a + 8), bpf=w(a + 10), mask=w(a + 12), code=w(a + 24),
                base=l(a + 26), cur=l(a + 30))

for name in ('objects_set0.png', 'objects_l1.png', 'orders.txt'):
    if os.path.exists(os.path.join(out, name)): os.remove(os.path.join(out, name))

print('scroll', SCROLL)
objs = []
for s in range(3):
    r = rec(SLOTS + s * 0x22)
    x, y, ty = (w(LIST + s * 8 + k) for k in (0, 2, 4))
    objs.append((r, x - SCROLL, y))
    assert r['bpf'] == r['W'] // 8 * r['H'] * 5 and r['mask'] == r['W'] // 8 * r['H'] * 4
    scores = [match(GFX + r['base'] + f * r['bpf'], r['W'], r['H'], x - SCROLL, y) for f in range(r['n'])]
    print('slot %d type %d %dx%d at screen (%d,%d), record frame %d: equal/opaque per frame %s' % (
        s, ty, r['W'], r['H'], x - SCROLL, y, r['frame'], ' '.join('%d/%d' % t for t in scores)))

r, ox, oy = objs[1]                      # the exit: where it misses, and the alternatives
addr = GFX + r['cur']
idx, mk = decode(addr, r['W'], r['H'])
bad = [(x, y) for y in range(r['H']) for x in range(r['W']) if mk[y][x] and idx[y][x] != screen_idx(ox + x, oy + y)]
print('exit misses: %d, rows %s, %d of them where the screen index has bit 3 set' % (
    len(bad), sorted({y for _, y in bad}), sum(1 for x, y in bad if screen_idx(ox + x, oy + y) & 8)))
alts = [(layout, order, pol) + match(addr, r['W'], r['H'], ox, oy, layout, order, pol)
        for layout in ('seq', 'rowplane', 'wordil') for order in itertools.permutations(range(4)) for pol in (1, 0)]
alts.sort(key=lambda t: -t[3] / t[4] if t[4] else 0)
open(os.path.join(out, 'orders.txt'), 'w').write(
    'layout order mask-polarity equal opaque\n' + ''.join('%s %s %d %d %d\n' % t for t in alts))
for layout in ('seq', 'rowplane', 'wordil'):
    for pol in (1, 0):
        best = sorted((t for t in alts if t[0] == layout and t[2] == pol), key=lambda t: -t[3])[:2]
        print('exit, layout %s mask %d: best two orders %s' % (layout, pol, ', '.join('%s %d/%d' % (t[1], t[3], t[4]) for t in best)))

both = Image.new('RGB', (640, 200))
for y in range(200):
    for x in range(320):
        both.putpixel((x, y), PAL[screen_idx(x, y)]); both.putpixel((x + 320, y), PAL[screen_idx(x, y)])
for r, ox, oy in objs:                   # painted at the frame that matched, not the record's
    f = max(range(r['n']), key=lambda f: match(GFX + r['base'] + f * r['bpf'], r['W'], r['H'], ox, oy)[0])
    idx, mk = decode(GFX + r['base'] + f * r['bpf'], r['W'], r['H'])
    for y in range(r['H']):
        for x in range(r['W']):
            if mk[y][x] and 0 <= ox + x < 320: both.putpixel((320 + ox + x, oy + y), PAL[idx[y][x]])
both.resize((1280, 400), Image.NEAREST).save(os.path.join(out, 'objects_l1.png'))

rows = []
for t in range(12):
    r = rec(TYPES + t * 34)
    assert r['bpf'] == r['W'] // 8 * r['H'] * 5
    fr = []
    for f in range(r['n']):
        idx, mk = decode(GFX + r['base'] + f * r['bpf'], r['W'], r['H'])
        im = Image.new('RGB', (r['W'], r['H']), (90, 90, 90))
        for y in range(r['H']):
            for x in range(r['W']):
                if mk[y][x]: im.putpixel((x, y), PAL[idx[y][x]])
        fr.append(im)
    rows.append(fr)
    print('type %2d: %2d frames of %dx%d, cell code %x' % (t, r['n'], r['W'], r['H'], r['code']))
sheet = Image.new('RGB', (max(sum(f.width + 2 for f in fr) for fr in rows), sum(fr[0].height + 4 for fr in rows)), (40, 40, 40))
y0 = 0
for fr in rows:
    for i, f in enumerate(fr): sheet.paste(f, (i * (f.width + 2), y0))
    y0 += fr[0].height + 4
sheet.resize((sheet.width * 3, sheet.height * 3), Image.NEAREST).save(os.path.join(out, 'objects_set0.png'))
