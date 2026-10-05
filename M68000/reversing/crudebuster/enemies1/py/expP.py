"""Portraits: every pool A type/variant spawned alone on the level-0 street (or at its boss scroll position), P1 pinned out of the way, snapshots at frames 30, 75 and 140.
Output out/expP/<t>_<v>/ (run dir snapshots in run/expP/<t>_<v>/snap/lab*.png) and out/enemies_sheet.png (cropped, labelled).  usage: expP.py"""
import sys, os, glob
sys.path.insert(0, os.path.dirname(__file__))
from labrun import run_plans, HERE
from PIL import Image, ImageDraw
TV = [(0,0),(1,1),(2,2),(3,0),(4,0),(4,1),(5,0),(5,1),(6,0),(6,1),(7,0),(8,0),(20,0),(20,1),(21,1)]
BOSS = [(9,0,0x620,0x1c0,0x500),(10,0,0x620,0x1c0,0x500),(11,0,0x620,0x1c0,0x500),(32,0,0x620,0x1c0,0x500),(14,0,0x8dc,0x140,0x7d7),(15,0,0x920,0x1c0,0x7e0),(28,0,0x700,0x80,0x700),(54,0,0x620,0x1c0,0x500),(55,0,0x620,0x1c0,0x500),(23,2,0xb40,0x160,0xa00)]
plans = []
for t, v in TV: plans.append(("%d_%d" % (t, v), dict(stop=145, pin=(0x110, 0x1c0), shots=[30, 75, 140], events=[(3, "spawn", t, v, 0x1c0, 0x1c0)])))
for t, v, x, y, sx in BOSS: plans.append(("%d_%d" % (t, v), dict(stop=145, pin=(sx + 0x20, 0x1c0), scroll=(sx, 0x100), shots=[30, 75, 140], events=[(3, "spawn", t, v, x, y)])))
if "--sheet-only" not in sys.argv: run_plans("expP", plans, parallel=6)
tiles = []
cfg = [(t, v, 0x1c0, 0x1c0, 0x100) for t, v in TV] + BOSS
for t, v, x, y, sx in cfg:
    for fno in (30, 75, 140):
        fn = os.path.join(HERE, "run", "expP", "%d_%d" % (t, v), "snap", "lab%05d.png" % fno)
        if not os.path.exists(fn): continue
        im = Image.open(fn).convert("RGB")
        cx, cy = x - sx, y - 0x100
        if cy < 110: cy = 110
        # enemies move; crop around the nominal position, wide enough
        box = (max(cx - 64, 0), max(cy - 110, 0), min(cx + 64, 256), min(cy + 24, 240))
        c = Image.new("RGB", (128, 134), (30, 30, 30)); c.paste(im.crop(box), (box[0] - (cx - 64), box[1] - (cy - 110)))
        c = c.resize((256, 268), Image.NEAREST)
        ImageDraw.Draw(c).text((3, 3), "type %d var %d  f%d" % (t, v, fno), fill=(255, 255, 0))
        tiles.append(c)
cols = 6; rows = (len(tiles) + cols - 1) // cols
W = Image.new("RGB", (256 * cols, 268 * rows))
for i, c in enumerate(tiles): W.paste(c, ((i % cols) * 256, (i // cols) * 268))
W.save(os.path.join(HERE, "out", "enemies_sheet.png")); print(len(tiles), "tiles")
