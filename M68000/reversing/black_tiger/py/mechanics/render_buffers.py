"""Render both screen buffers ($f0000, $f8000) of a snapshot with the live palette (the shop scene is drawn off-screen first).
Usage: render_buffers.py snap out_prefix"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import btlib as b
sys.path.insert(0, os.path.join(b.ROOT, "tools"))
import gfxview
from PIL import Image
snap, pref = sys.argv[1], sys.argv[2]
ram = b.ram_from_snap(snap)
v = gfxview.load_video_regs(snap)
pal = [gfxview.ste_colour(w) for w in v['palette_words']]
for base in (0xf0000, 0xf8000):
    im = Image.new("RGB", (320, 200))
    px = im.load()
    for y in range(200):
        for xw in range(20):
            a = base + y * 160 + xw * 8
            w = [(ram[a + 2 * p] << 8) | ram[a + 2 * p + 1] for p in range(4)]
            for bit in range(16):
                c = sum(((w[p] >> (15 - bit)) & 1) << p for p in range(4))
                px[xw * 16 + bit, y] = pal[c]
    im.save("%s_%x.png" % (pref, base))
print("live base %x" % v["base"])
