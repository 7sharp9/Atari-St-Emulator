"""Compare HUD bar pixel widths (screenshots) with the health word +24 of the tracked records (census file).
usage: hudbar.py <census.txt> <snapdir> <tag> <lo> <hi> [idx_player=0] [idx_enemy=14] [lag...]
Player bar: rows y=17..22, yellow (255,255,0) run starting x=24; enemy bar: rows y=33..38 same colour."""
import sys, re, os
from PIL import Image
cen, snapdir, tag, lo, hi = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
ip = int(sys.argv[6]) if len(sys.argv) > 6 else 0
ie = int(sys.argv[7]) if len(sys.argv) > 7 else 14
hp = {}
f = None
for line in open(cen):
    if line.startswith("F "): f = int(line.split()[1])
    elif line.startswith("R "):
        p = line.split(); i = int(p[1]); h = int(re.search(r"hp=([0-9a-f]+)", line).group(1), 16)
        hp[(f, i)] = h
def width(im, y):
    n = 0
    for x in range(24, 200):
        if im.getpixel((x, y))[:3] == (255, 255, 0): n += 1
        else: break
    return n
def sgn(h): return h - 0x10000 if h >= 0x8000 else h
res = {0: [0, 0], 1: [0, 0], 2: [0, 0]}
rows = []
for fr in range(lo, hi + 1):
    p = os.path.join(snapdir, "%s_%05d.png" % (tag, fr))
    if not os.path.exists(p): continue
    im = Image.open(p).convert("RGB")
    wp, we = width(im, 20), width(im, 36)
    for lag in (0, 1, 2):
        h = hp.get((fr - lag, ip))
        if h is not None:
            res[lag][0] += 1; res[lag][1] += (wp == max(0, sgn(h)))
    rows.append((fr, wp, we, hp.get((fr, ip)), hp.get((fr, ie))))
print("player bar == max(0,hp[frame-lag]):", {k: "%d/%d" % (v[1], v[0]) for k, v in res.items()})
# enemy: compare with each lag
for lag in (0, 1, 2):
    n = m = 0
    for fr, wp, we, hpp, hpe in rows:
        h = hp.get((fr - lag, ie))
        if h is not None:
            n += 1; m += (we == max(0, sgn(h)))
    print("enemy bar == max(0,hp[frame-lag]) lag %d: %d/%d" % (lag, m, n))
if os.getenv("V"): 
    for r in rows: print(r)
