"""Enemy HUD bar width vs the health word of the enemy last damaged (writers 0079fe/007a04-family/00db68 on i>0 in ft file).
usage: hudenemy.py <census> <htap file> <snapdir> <tag> <lo> <hi>"""
import sys, re, os
from PIL import Image
cen, ft, snapdir, tag, lo, hi = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]), int(sys.argv[6])
hp = {}; f = None
for line in open(cen):
    if line.startswith("F "): f = int(line.split()[1])
    elif line.startswith("R "):
        p = line.split(); hp[(f, int(p[1]))] = int(re.search(r"hp=([0-9a-f]+)", line).group(1), 16)
# events from an htap file: a +60 write (hit by pointer) on i>0 names the victim enemy; on i=0 (Cody) its data is the attacker
DMG = {"0079fe", "007a12", "007a02", "007a32", "007bd6", "007bec", "00db68", "003fa2", "003fae", "003fb4", "006630", "006640", "00762 2"}
last = []  # (frame, idx) of damaging writes to enemies
for l in open(ft):
    m = re.match(r"W f=(\d+) pc=(\w+) i=(\d+) o=60 d=(\w+)", l)
    if not m or m.group(4) == "0000": continue
    i = int(m.group(3))
    if i == 0: i = (0xff0000 + int(m.group(4), 16) - 0xff8568) // 0xc0
    last.append((int(m.group(1)), i))
def sgn(h): return h - 0x10000 if h >= 0x8000 else h
def width(im, y):
    n = 0
    for x in range(24, 200):
        if im.getpixel((x, y))[:3] == (255, 255, 0): n += 1
        else: break
    return n
res = [0, 0]; rows = []
for fr in range(lo, hi + 1):
    p = os.path.join(snapdir, "%s_%05d.png" % (tag, fr))
    if not os.path.exists(p): continue
    cand = [i for (ff, i) in last if ff <= fr - 1]
    if not cand: continue
    i = cand[-1]
    h = hp.get((fr, i))
    if h is None: continue
    we = width(Image.open(p).convert("RGB"), 36)
    res[0] += 1; ok = (we == max(0, sgn(h))); res[1] += ok
    if not ok: rows.append((fr, i, we, h))
print("enemy bar == hp of last damaged enemy: %d/%d" % (res[1], res[0])); print(rows[:10])
