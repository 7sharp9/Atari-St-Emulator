"""Populous II cell shape codes $2f and $3f against settlements, on snapshots.

Checks, per snapshot:
  1. every settled entity (type 4 in the $3ff1a array) sits on a cell coded $2f (side 1) or $3f (side 2);
  2. every $2f/$3f cell without a settlement lies within Chebyshev distance 2 of a settlement of the
     side its code names (README "Objects and entities").
  Control: settlements on the other side's code.

usage: uv run python reversing/populous2/py/owned_cells.py <snap> [<snap> ...]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from corners import ROOT  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "tools"))
from gfxview import load_ram  # noqa: E402

C = 0x3979E
CODE = {1: 0x2F, 2: 0x3F}


def main():
    for snap in sys.argv[1:]:
        r, _ = load_ram(snap)
        sett = {}
        for i in range(1, 400):
            a = 0x3FF1A + i * 0x34
            if r[a + 12] and r[a] == 4:
                sett[r[a + 6], r[a + 8]] = r[a + 12]
        on_code = sum(r[C + 4 * (y * 64 + x) + 1] == CODE.get(s) for (x, y), s in sett.items())
        swapped = sum(r[C + 4 * (y * 64 + x) + 1] == CODE.get(3 - s) for (x, y), s in sett.items())
        near = tot = 0
        for k in range(4096):
            b1 = r[C + 4 * k + 1]
            if b1 in (0x2F, 0x3F) and (k % 64, k // 64) not in sett:
                side = 1 if b1 == 0x2F else 2
                x, y = k % 64, k // 64
                tot += 1
                near += any(max(abs(x - sx), abs(y - sy)) <= 2
                            for (sx, sy), sd in sett.items() if sd == side)
        print(f"{os.path.basename(snap)}: settlements on their side's code {on_code}/{len(sett)}; "
              f"control (codes swapped) {swapped}/{len(sett)}; unoccupied $2f/$3f cells within 2 of a same-side settlement {near}/{tot}")


if __name__ == "__main__":
    main()
