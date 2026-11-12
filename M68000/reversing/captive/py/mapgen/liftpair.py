"""Gate: every lift end has a partner on the adjacent floor at exactly that floor pair's offset.

    uv run python -I reversing/captive/py/mapgen/liftpair.py <lo> <hi> [d2]

Runs gen.py's call for D0 = lo..hi-1 (D1 = 0, D2 = 1 unless given, D3 = 0) and counts lift cells: G1 feature
(low 7 bits) 4, 5, 6, $35, $36 or $37. A cell on floor k (block table, module bytes 0..15) is paired when the cell
at + offset[k] (module words 16+2(k-1) for x, 24+2(k-1) for y, as $2514c adds them) is on floor k+1 and is a lift
cell, or the cell at - offset[k-1] (as $25136 subtracts) is on floor k-1 and is a lift cell.
Prints per seed and the total `paired N/M`.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen import grids, run_cases  # noqa: E402

LIFT = (4, 5, 6, 0x35, 0x36, 0x37)


def pairs(o):
    g = grids(o)
    v = g['vars']
    t = v[:16]
    nf = int.from_bytes(v[46:48], 'big')
    off = [(int.from_bytes(v[16 + 2 * k:18 + 2 * k], 'big', signed=True),
            int.from_bytes(v[24 + 2 * k:26 + 2 * k], 'big', signed=True)) for k in range(4)]

    def floor(x, y):
        return t[(y >> 3) * 4 + (x >> 4)]

    def lift(x, y):
        return 0 <= x < 64 and 0 <= y < 32 and (g['feat'][64 * y + x] & 0x7f) in LIFT

    cells = [(x, y) for y in range(32) for x in range(64) if lift(x, y)]
    ok = 0
    for x, y in cells:
        k = floor(x, y)
        good = False
        if k < nf:
            dx, dy = off[k - 1]
            good |= lift(x + dx, y + dy) and floor(x + dx, y + dy) == k + 1
        if 1 < k <= 5:
            dx, dy = off[k - 2]
            good |= lift(x - dx, y - dy) and floor(x - dx, y - dy) == k - 1
        ok += good
    return nf, len(cells), ok


def main():
    lo, hi = int(sys.argv[1]), int(sys.argv[2])
    d2 = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    res = run_cases([[d0, 0, d2, 0] for d0 in range(lo, hi)])
    tot = tp = 0
    for o in res:
        nf, n, ok = pairs(o)
        print(f'D0 {o["args"][0]}: floors {nf}, lift cells {n}, paired {ok}')
        tot += n
        tp += ok
    print(f'paired {tp}/{tot} lift cells over D0 = {lo}..{hi - 1}, D2 = {d2}')


if __name__ == '__main__':
    main()
