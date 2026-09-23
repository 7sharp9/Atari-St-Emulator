"""panelmap.py - draw the $c3e2 click regions over a game frame.

  python panelmap.py <snap> <out.png>

Each command icon's diamond hit region (from popdrive.classify) is outlined and numbered on the
frame rendered from the snapshot (tools/snap_render.py); the legend is printed."""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw
from popcfg import R
from popdrive import classify, ICONS, PANEL, RIGHT

snap, out = sys.argv[1], sys.argv[2]
tmp = out + '.base.png'
subprocess.run([sys.executable, os.path.join(R, 'tools', 'snap_render.py'), snap, tmp], check=True, capture_output=True)
im = Image.open(tmp).convert('RGB'); os.remove(tmp)
S = 3
im = im.resize((320 * S, 200 * S), Image.NEAREST)
d = ImageDraw.Draw(im)
names = {('panel', cr): n for cr, (n, _) in PANEL.items()}
names.update({('right', cr): n for cr, (n, _) in RIGHT.items()})
order = list(names.values())
reg = {}
for y in range(200):
    for x in range(320):
        k = classify(x, y)
        if k[0] == 'minimap':
            k = ('minimap', None)
        reg[x, y] = k if (k in names or k[0] == 'minimap') else None
for y in range(200):
    for x in range(320):
        k = reg[x, y]
        if k is None:
            continue
        col = (255, 255, 0) if k[0] == 'minimap' else (255, 0, 255)
        for nx, ny in ((x + 1, y), (x, y + 1)):
            if nx < 320 and ny < 200 and reg[nx, ny] != k:
                d.rectangle([nx * S, ny * S, nx * S + S - 1, ny * S + S - 1], fill=col)
for k, n in names.items():
    pts = [p for p, v in reg.items() if v == k]
    if not pts:
        continue
    cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
    i = order.index(n)
    d.text((cx * S - 5, cy * S - 6), str(i), fill=(255, 255, 255))
im.save(out)
for i, n in enumerate(order):
    print(i, n)
