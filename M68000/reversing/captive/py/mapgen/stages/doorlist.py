"""Check the coded-door list (federation 2330(A6) = $1bee8, pointer 13708(A6)) against the grid in every dump.

    uv run python -I reversing/captive/py/mapgen/stages/doorlist.py <lo> <hi> [d2 ...]

After the last stage, every used entry (cell word x.y, state word) must name a cell whose G1 feature is $15 (door)
with parameter low bits 2 (the coded kind; slot 0 at D2 = 1 comes from $2676c instead), state low nibble 0 and
code (state >> 4) < 24; and every door cell of kind 2 must be in the list. Prints counts and a histogram of codes.
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import FED, G1, load  # noqa: E402

LIST = 0x1b5ce + 2330 - FED


def main():
    lo, hi = int(sys.argv[1]), int(sys.argv[2])
    d2s = [int(a) for a in sys.argv[3:]] or [1, 0]
    n = good = kind2 = listed2 = 0
    codes = Counter()
    kinds = Counter()
    for d2 in d2s:
        for d0 in range(lo, hi):
            _, m, f = load(d2, d0)[-1]
            ent = set()
            for i in range(8):
                o = LIST + 4 * i
                x, y, st = f[o], f[o + 1], (f[o + 2] << 8) | f[o + 3]
                if x == 0 and y == 0 and st == 0:
                    continue
                n += 1
                c = 2 * (64 * y + x)
                feat, par = m[G1 + c + 1], m[G1 + c]
                kinds[(feat, par & 7)] += 1
                ok = feat == 0x15 and st & 0xf == 0 and (st >> 4) < 24
                good += ok
                codes[st >> 4] += 1
                ent.add(c)
            for c in range(0, 4096, 2):
                if m[G1 + c + 1] == 0x15 and m[G1 + c] & 7 == 2:
                    kind2 += 1
                    listed2 += c in ent
    print(f'entries {n}: door cell with state nibble 0 and code < 24: {good}/{n}')
    print(f'(feature, param & 7) of listed cells: {dict(kinds)}')
    print(f'kind-2 door cells in the grid listed: {listed2}/{kind2}')
    print('codes', sorted(codes.items()))


if __name__ == '__main__':
    main()
