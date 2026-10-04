"""Overlay the invisible/special map markers on the graphics agent's whole-level renders.
Colours: door-in red, door-out green, anchor B (dungeon arrival) yellow, anchor A (start) white,
checkpoint cyan, exit magenta, old men/shop man orange, traps $1d/$1e blue, chest $a brown.
usage: secrets_map.py [level 0..7 ...] -> $OUT/map_L<n>.png"""
import os, sys, struct
from btsec import *
from PIL import Image, ImageDraw
col = {0x1b: "red", 0x1c: "lime", 0x3e: "yellow", 0x3f: "white", 0x3d: "pink", 0x1f: "cyan", 0x20: "magenta",
       0x1d: "blue", 0x1e: "blue", 0x0a: "brown", 0x11: "orange", 0x12: "orange", 0x13: "orange", 0x14: "orange",
       0x15: "orange", 0x16: "orange"}
for n in [int(a) for a in sys.argv[1:]] or range(8):
    d = open(os.path.join(WORK, "files", str(n)), "rb").read()
    w, h = struct.unpack(">HH", d[:4]); words = struct.unpack(">%dH" % (w * h), d[4:4 + 2 * w * h])
    im = Image.open(os.path.join(WORK, "agents", "graphics", "png", "level_%d_map.png" % n)).convert("RGB")
    dr = ImageDraw.Draw(im)
    for i, x in enumerate(words):
        mk = x >> 10
        if mk in col:
            cx, cy = (i % w) * 16 + 8, (i // w) * 16 + 8
            dr.rectangle([cx - 7, cy - 7, cx + 7, cy + 7], outline=col[mk], width=2)
    im.save(os.path.join(OUT, "map_L%d.png" % n)); print(n, im.size)
