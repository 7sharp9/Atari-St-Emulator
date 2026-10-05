"""namesheet.py <htap events file> <census> <snapdir> <tag> <winfile> <out.png>: for the last frame of each shot window, crop the HUD enemy-name text
 (x 24..99, y 23..30 of the 384x224 snapshot), enlarge it and print beside it the attributes of the record the HUD tracks (the enemy of the last +60 hit event)."""
import sys, re
from PIL import Image, ImageDraw
ev_f, cen_f, snap, tag, winf, out = sys.argv[1:7]
last = []
for l in open(ev_f):
    m = re.match(r"W f=(\d+) pc=(\w+) i=(\d+) o=60 d=(\w+)", l)
    if not m or m.group(4) == '0000': continue
    i = int(m.group(3))
    if i == 0: i = (0xff0000 + int(m.group(4), 16) - 0xff8568) // 0xc0
    last.append((int(m.group(1)), i, m.group(2)))
cen = {}; f = None
for l in open(cen_f):
    if l.startswith('F '): f = int(l.split()[1])
    elif l.startswith('R '):
        d = dict(t.split('=') for t in l.split()[3:]); d['i'] = int(l.split()[1]); cen[(f, d['i'])] = d
win = [tuple(map(int, x.split('-'))) for x in open(winf).read().split(',')]
rows = []
for a, b in win:
    fr = b
    ev = [e for e in last if e[0] <= fr - 1]
    f0, i, pc = ev[-1]
    rows.append((fr, f0, i, pc, cen.get((fr, i))))
S = 4
sheet = Image.new('RGB', (76 * S + 640, len(rows) * (8 * S + 4)), (30, 30, 30))
dr = ImageDraw.Draw(sheet)
for k, (fr, f0, i, pc, r) in enumerate(rows):
    im = Image.open('%s/%s_%05d.png' % (snap, tag, fr)).convert('RGB').crop((24, 23, 100, 31)).resize((76 * S, 8 * S), Image.NEAREST)
    y = k * (8 * S + 4); sheet.paste(im, (0, y))
    txt = 'f%d ev@%d idx%d %s ' % (fr, f0, i, pc) + (' '.join('%s=%s' % (q, r[q]) for q in ('b19', 'w20', 'p92', 'b55', 'hp') if q in r) if r else 'dead')
    dr.text((76 * S + 6, y + 6), txt, fill=(255, 255, 255))
sheet.save(out); print(sheet.size)
for x in rows: print(x[0], x[2], x[3], x[4] and {q: x[4][q] for q in ('b19', 'w20', 'p92', 'p56', 'b55', 'b96', 'b98', 'hp')})
