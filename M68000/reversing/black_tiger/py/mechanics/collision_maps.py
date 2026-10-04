"""Collision/marker maps of the eight levels from the level files + tileset class tables (no emulator).
class table = T file bytes $40..$43f (loaded at $25f8c, read at $25fcc by $ec7c); level -> tileset letter from $175fb ("00234567").
Writes levels_collision.png (one panel per level) under $BT_WORK/agents/mechanics/ and prints a start-position sanity check:
the 3f anchor must have a non-solid cell at the hero's head/chest and a solid/ladder cell at the feet row."""
import os, sys, struct
sys.path.insert(0, os.path.dirname(__file__))
import btlib as b, levelmap as lm
from PIL import Image, ImageDraw
TS = ["T0", "T0", "T2", "T3", "T4", "T5", "T6", "T7"]
COL = {0: (20, 20, 30), 1: (150, 150, 160), 2: (60, 190, 90), 3: (220, 50, 50)}
OTHER = (110, 90, 40)
panels = []
for n in range(8):
    w, h, words, _ = lm.load(n)
    t = open(os.path.join(b.FILES, TS[n]), "rb").read()
    cls = t[0x40:0x440]
    S = 4
    im = Image.new("RGB", (w * S, h * S))
    d = ImageDraw.Draw(im)
    anchors = {}
    for i, wd in enumerate(words):
        col, row = i % w, i // w
        c = cls[wd & 0x3ff]
        d.rectangle([col * S, row * S, col * S + S - 1, row * S + S - 1], fill=COL.get(c, OTHER))
        m = wd >> 10
        if m:
            colr = (80, 160, 255) if m < 0x28 else ((255, 160, 40) if m < 0x3d else (255, 60, 255))
            d.rectangle([col * S, row * S, col * S + S - 1, row * S + S - 1], outline=colr)
            if m >= 0x3d: anchors[m] = (col, row)
    sx, sy = anchors[0x3f]
    def cl(x, y): return cls[words[(y // 16) * w + (x // 16) % w] & 0x3ff]
    px, py = sx * 16, sy * 16 + 16
    print("level %d: tileset %s class counts %s; start (x=%d,y=%d) cells head/chest/feet classes: %d %d %d" %
          (n + 1, TS[n], {k: sum(1 for wd in words if cls[wd & 0x3ff] == k) for k in (0, 1, 2, 3)}, px, py, cl(px, py - 32), cl(px, py - 16), cl(px, py)))
    panels.append(im)
W = sum(p.width for p in panels[:4]) + 30; Hh = max(p.height for p in panels[:4]) + max(p.height for p in panels[4:]) + 10
sheet = Image.new("RGB", (W, Hh), (0, 0, 0)); x = 0
for p in panels[:4]: sheet.paste(p, (x, 0)); x += p.width + 10
x = 0; y0 = max(p.height for p in panels[:4]) + 10
for p in panels[4:]: sheet.paste(p, (x, y0)); x += p.width + 10
sheet.save(os.path.join(b.OUT, "levels_collision.png"))
print("wrote", os.path.join(b.OUT, "levels_collision.png"))
