"""Pairwise byte comparison of the output regions between consecutive cases of a gen.py json (all pairs with --all).

    uv run python -I reversing/captive/py/mapgen/gen.py seeds.json 1,0,1,0 1,0,1,0 1,0x1234,1,7 1,0,0,0 2,0,1,0 \
        1,164,14,1 1,165,14,1 1,164,14,2
    uv run python -I reversing/captive/py/mapgen/cmpcases.py seeds.json

Determinism: the two 1,0,1,0 runs differ in 0 bytes. Base seeding: 1,0x1234,1,7 equals 1,0,1,0 (D1, D3 unused).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen import outpath  # noqa: E402

KEYS = ('outa', 'outb', 'g0', 'g1', 'g2', 'fedtab')


def main():
    d = json.load(open(outpath(sys.argv[1])))
    every = '--all' in sys.argv
    for i in range(len(d)):
        for j in range(i + 1, len(d)):
            if not every and j != i + 1:
                continue
            diffs = {k: sum(a != b for a, b in zip(bytes.fromhex(d[i][k]), bytes.fromhex(d[j][k]))) for k in KEYS}
            print(d[i]['args'], d[j]['args'], diffs)


if __name__ == '__main__':
    main()
