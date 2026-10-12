#!/usr/bin/env python3
"""Python half of the synthetic quadrant-walk cross-check: pm_render_ref's
walk_q0..q3 against Fill.planQ0..3 (quad_fs.fsx). Deterministic pseudo-random corners + terrain
(no real RAM needed) so every branch (CLEAR/SET, both cmp directions, general
vs flat-top triangles) gets exercised. Dumps one line per covered pixel
"x,y,idx" sorted, for a byte-exact diff against the F# side (quad_fs.fsx).
"""
import os, sys
from pathlib import Path
_here = Path(__file__).resolve().parent
_root = next(p for p in _here.parents if (p / "tools" / "rdis.py").exists())
sys.path.insert(0, str(_root / "tools"))
OUT = Path(os.environ.get("XCHECK_OUT", "."))
import pm_render_ref as R

W, H = 9, 9  # corner grid range 0..8

def corner(r, c):
    x = 50 + ((r * 37 + c * 17) % 40)
    y = 40 + ((r * 23 + c * 31) % 30)
    return (x, y)

def typ(cx, cy):
    return 0x20 + ((cx * 7 + cy * 3) % 20)

def hgt(cx, cy):
    return 0x18 + ((cx * 5 + cy * 11) % 25)

def flg(cx, cy):
    return 0x80 if ((cx + cy) % 2 == 0) else 0x00

corners = {(r, c): corner(r, c) for r in range(W) for c in range(H)}
planes = dict(
    typ=lambda x, y: typ(x, y),
    hgt=lambda x, y: hgt(x, y),
    flg=lambda x, y: flg(x, y),
)

dith = bytes([(i * 37 + 11) & 0xFF for i in range(0x4000)])  # deterministic, non-degenerate

def run(walk_fn, name):
    idxbuf = bytearray(R.W * R.H)
    cov = bytearray(R.W * R.H)
    Rd = dict(cam=(0, 0), corners=corners, planes=planes, dith=dith, tick=1)
    walk_fn(idxbuf, cov, Rd)
    lines = []
    for y in range(R.H):
        for x in range(R.W):
            i = y * R.W + x
            if cov[i]:
                lines.append(f"{x},{y},{idxbuf[i]}")
    out = OUT / f"{name}_py.txt"
    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"{name}: {len(lines)} covered px -> {out}")

run(R.walk_q0, "q0")
run(R.walk_q1, "q1")
run(R.walk_q2, "q2")
run(R.walk_q3, "q3")
