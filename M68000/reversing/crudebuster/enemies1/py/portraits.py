"""Contact sheet of enemy portraits: reads the S lines of enemylog.txt (lua/enemylog.lua CB_PORTRAIT) and crops each snapshot around the record.
usage: portraits.py <rundir with snap/> <enemylog.txt> <out.png> [cols]   (crop 96x112 px around the screen position x-sx, y-sy, 2x)"""
import sys, os, re, glob
from PIL import Image, ImageDraw
run, log, out = sys.argv[1:4]; cols = int(sys.argv[4]) if len(sys.argv) > 4 else 6
tiles = []
for l in open(log):
    if not l.startswith("S "): continue
    t = l.split(); f = int(t[1]); ty, var, st, sx, sy, x, y = int(t[3]), int(t[5]), int(t[7]), int(t[9]), int(t[11]), int(t[13]), int(t[15])
    fn = glob.glob(os.path.join(run, "snap", "p%05d_t%d_v%d_s%d.png" % (f, ty, var, st)))
    if not fn: continue
    im = Image.open(fn[0]).convert("RGB")
    cx, cy = x - sx, y - sy
    box = (cx - 48, cy - 100, cx + 48, cy + 20)
    c = Image.new("RGB", (96, 120), (40, 40, 40)); c.paste(im.crop(box), (0, 0)) if box[0] >= 0 and box[2] <= 256 and box[1] >= 0 else c.paste(im.crop((max(box[0],0), max(box[1],0), min(box[2],256), min(box[3],240))), (max(0,-box[0]), max(0,-box[1])))
    c = c.resize((192, 240), Image.NEAREST)
    d = ImageDraw.Draw(c); d.text((2, 2), "t%d v%d s%d f%d" % (ty, var, st, f), fill=(255, 255, 0))
    tiles.append(c)
rows = (len(tiles) + cols - 1) // cols
W = Image.new("RGB", (192 * cols, 240 * rows))
for i, c in enumerate(tiles): W.paste(c, ((i % cols) * 192, (i // cols) * 240))
W.save(out); print(len(tiles), "tiles")
