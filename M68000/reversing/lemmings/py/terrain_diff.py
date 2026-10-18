"""Summarise skilldrive.py's frames.txt: per frame the lemming, and the pixels cleared/set against the first frame.
  python3 reversing/lemmings/py/terrain_diff.py <frames.txt> [--show N]   (N: print frame N as ASCII)"""
import sys, re
fr = []; cur = None
for l in open(sys.argv[1]):
    if l.startswith('=='):
        cur = [l.strip(), []]; fr.append(cur)
    elif cur is not None and l.strip():
        cur[1].append(l.rstrip('\n')[4:]); cur.append(int(l[:3])) if len(cur) == 2 else None
base = fr[0][1]
for i, (h, rows, *_) in enumerate(fr):
    clr = sum(1 for r in range(len(rows)) for c in range(len(rows[r])) if base[r][c] == '#' and rows[r][c] == '.')
    st = sum(1 for r in range(len(rows)) for c in range(len(rows[r])) if base[r][c] == '.' and rows[r][c] == '#')
    print('%2d %-60s cleared %4d set %3d' % (i, h[3:63], clr, st))
if '--show' in sys.argv:
    n = int(sys.argv[sys.argv.index('--show') + 1]); y0 = fr[n][2]
    for r, row in enumerate(fr[n][1]): print('%3d %s' % (y0 + r, row))
