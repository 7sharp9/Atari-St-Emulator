"""Piano-roll PNG of a model run (PSG tone frequency vs time, colour = channel, brightness = volume). usage: roll.py Q|J|M"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rcommon import *
from tune import *
from PIL import Image, ImageDraw
import math
ENT = {'Q': ('Q_906_59s_tune', [(0, 906)]), 'J': ('J_chord_194_208_222', [(0, 194), (1, 208), (2, 222)]), 'M': ('M_ch1_322', [(1, 322)])}
key = sys.argv[1] if len(sys.argv) > 1 else 'Q'
name, ents = ENT[key]
d, log, n = run(Driver, ents)
cur = [0] * 16; li = 0
PXs = 10 if key == 'Q' else 60       # pixels per second
fmin, fmax = 40.0, 1000.0
H = 360
W_ = int(n / ISR_HZ * PXs) + 60
img = Image.new('RGB', (W_, H + 30), (12, 12, 20)); px = img.load(); dr = ImageDraw.Draw(img)
cols = [(255, 90, 90), (90, 255, 120), (110, 150, 255)]
for f in (55, 110, 220, 440, 880):
    y = H - int((math.log2(f) - math.log2(fmin)) / (math.log2(fmax) - math.log2(fmin)) * H)
    dr.line([(0, y), (W_, y)], fill=(40, 40, 60)); dr.text((2, y - 10), '%d Hz' % f, fill=(120, 120, 150))
for t in range(n):
    while li < len(log) and log[li][0] <= t:
        for r, v in log[li][1]: cur[r] = v
        li += 1
    x = int(t / ISR_HZ * PXs)
    for ch in range(3):
        per = ((cur[2 * ch + 1] & 15) << 8) | cur[2 * ch]
        vol = cur[8 + ch] & 15
        if per == 0 or vol == 0: continue
        f = 125000.0 / per
        if not (fmin <= f <= fmax): continue
        y = H - int((math.log2(f) - math.log2(fmin)) / (math.log2(fmax) - math.log2(fmin)) * H)
        c = tuple(int(v * (0.25 + 0.75 * vol / 15)) for v in cols[ch])
        px[min(x, W_ - 1), y - 2 + ch] = c
for s in range(0, int(n / ISR_HZ) + 1, 5 if key == 'Q' else 1):
    dr.text((s * PXs, H + 10), '%ds' % s, fill=(150, 150, 150))
img.save(os.path.join(OUT, 'roll_%s.png' % name))
print('wrote', os.path.join(OUT, 'roll_%s.png' % name), img.size)
