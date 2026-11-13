"""Populous II landscape: the corner heights implied by the 64x64 cell records at $3979e.

There is no corner-height grid in RAM (a whole-RAM search for a 65x65 byte or word grid that
derives the cells finds none). Each cell record is 4 bytes; byte 0 & 7 is the cell altitude and
byte 1 the shape code, and the corner-height reader $1f176(D0=x, D1=y) -> D2 returns

    h(x, y) = (cell(x, y).b0 & 7) + bit k of $36b7a[cell(x, y).b1]

with k = 0 for the cell's own top corner; on the x = 64 or y = 64 edge it reads the neighbour
cell's bit 1, 3 or 2 instead ($1f1cc..$1f1e4).

Checks, on one snapshot:
  shared   every one of the 65x65 corners reads the same height from each cell that touches it
  derive   Populous 1's cell derivation ($c0ee, reversing/populous/terrain.md section 1) applied
           to that corner grid gives back b0 & 7 and b1 for every cell not coded $2f/$3f
           (land held by a settlement), without Populous 1's shore rule (+$10 on a slope at sea level); the
           variant with the shore rule is printed as the control
  callcap  (with --callcap) $1f176 under callcap at every non-zero corner, 100 sea corners and
           three edge corners, against the grid; an altitude-only model is the control

usage: uv run python reversing/populous2/py/corners.py <snap> [--callcap]
"""
import os
import random
import re
import subprocess
import sys


def m68000_root():
    d = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(d, "tools", "rdis.py")):
        nd = os.path.dirname(d)
        if nd == d:
            sys.exit("cannot find M68000/ (tools/rdis.py) above " + __file__)
        d = nd
    return os.environ.get("M68000_ROOT", d)


ROOT = m68000_root()
sys.path.insert(0, os.path.join(ROOT, "tools"))
from gfxview import load_ram  # noqa: E402

CELLS = 0x3979E
CORNER_MASK = 0x36B7A


def corner_grid(ram):
    T = ram[CORNER_MASK:CORNER_MASK + 256]

    def cell(x, y):
        o = CELLS + (y * 64 + x) * 4
        return ram[o:o + 4]

    def corner_of(x, y, k):
        c = cell(x, y)
        return (c[0] & 7) + ((T[c[1]] >> k) & 1)

    H, disagree = {}, 0
    for y in range(65):
        for x in range(65):
            vals = [corner_of(cx, cy, k)
                    for (cx, cy, k) in ((x, y, 0), (x - 1, y, 1), (x - 1, y - 1, 2), (x, y - 1, 3))
                    if 0 <= cx < 64 and 0 <= cy < 64]
            disagree += len(set(vals)) > 1
            H[x, y] = vals[0]
    return H, disagree, cell


def derive_check(H, cell, shore):
    ok = n = 0
    for y in range(64):
        for x in range(64):
            c = cell(x, y)
            if c[1] in (0x2F, 0x3F):
                continue
            a, b, cc, d = H[x, y], H[x + 1, y], H[x + 1, y + 1], H[x, y + 1]
            s = (a + b + cc + d) >> 2
            bits = (a > s) | (b > s) << 1 | (cc > s) << 2 | (d > s) << 3
            if s and not bits:
                s -= 1
                bits = 15
            if shore and s == 0 and bits not in (0, 15):
                bits += 16
            n += 1
            ok += bits == c[1] and s == (c[0] & 7)
    return ok, n


def callcap_check(snap, H, cell):
    random.seed(2)
    nz = [k for k, v in H.items() if v]
    z = random.sample([k for k, v in H.items() if not v], 100)
    pts = nz + z + [(64, 64), (64, 0), (0, 64)]
    script = "".join(f"callcap 1f176 20000 D0={x:x} D1={y:x}\n" for x, y in pts)
    dll = os.path.join(ROOT, "bin", "Debug", "net8.0", "M68000.dll")
    out = subprocess.run(["dotnet", "exec", dll, "resume", snap, "repl"], input=script,
                         capture_output=True, text=True, cwd=ROOT).stdout
    blocks = out.split("--- callcap")[1:]
    if len(blocks) != len(pts):
        sys.exit(f"expected {len(pts)} callcaps, got {len(blocks)}:\n{out[-2000:]}")
    d2_entry = None
    good = ctl = 0
    for (x, y), blk in zip(pts, blocks):
        if "returned" not in blk.splitlines()[0]:
            sys.exit("callcap did not return: " + blk.splitlines()[0])
        m = re.search(r"D2 \$([0-9a-f]+)->\$([0-9a-f]+)", blk)
        if m:
            d2_entry = int(m.group(1), 16)
            d2 = int(m.group(2), 16)
        else:
            if d2_entry is None:
                sys.exit("D2 unchanged before any change seen; cannot recover it")
            d2 = d2_entry
        good += (d2 & 0xFFFF) == H[x, y]
        ctl += (d2 & 0xFFFF) == (cell(min(x, 63), min(y, 63))[0] & 7)
    print(f"callcap $1f176 vs corner grid {good}/{len(pts)}; altitude-only control {ctl}/{len(pts)}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        sys.exit(__doc__)
    snap = os.path.abspath(args[0])
    ram, _ = load_ram(snap)
    H, disagree, cell = corner_grid(ram)
    print(f"shared corners consistent {65 * 65 - disagree}/{65 * 65}")
    ok, n = derive_check(H, cell, shore=False)
    cok, _ = derive_check(H, cell, shore=True)
    print(f"cells re-derived {ok}/{n}; control with Populous 1's shore rule {cok}/{n}")
    hist = {}
    for v in H.values():
        hist[v] = hist.get(v, 0) + 1
    print("corner height histogram", sorted(hist.items()))
    if "--callcap" in sys.argv:
        callcap_check(snap, H, cell)


if __name__ == "__main__":
    main()
