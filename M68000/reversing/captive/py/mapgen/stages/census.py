"""Which bytes each stage changes, summed over seeds, from dumpall.py's dumps.

    uv run python -I reversing/captive/py/mapgen/stages/census.py <d2> <lo> <hi> [--from 24f4c]

Per stage (by callee): bytes changed in G0, G1 (param / feature bytes separately), G2, and the list of other module
offsets (A6 = $20376) and federation offsets (fed A6 = $1b5ce) it changed in any seed, as ranges.
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import FED, G0, G1, G2, STAGES, load  # noqa: E402

FA6 = 0x1b5ce


def ranges(xs):
    xs = sorted(xs)
    out = []
    for x in xs:
        if out and x <= out[-1][1] + 2:
            out[-1][1] = x
        else:
            out.append([x, x])
    return ', '.join(f'{a}' if a == b else f'{a}-{b}' for a, b in out)


def main():
    d2, lo, hi = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    start = int(sys.argv[sys.argv.index('--from') + 1], 16) if '--from' in sys.argv else 0x24f4c
    first = [c for _, c in STAGES].index(start) + 1
    tot = defaultdict(lambda: defaultdict(int))
    other = defaultdict(set)
    fedo = defaultdict(set)
    for d0 in range(lo, hi):
        recs = load(d2, d0)
        for k in range(first, len(STAGES)):
            (_, m0, f0), (_, m1, f1) = recs[k - 1], recs[k]
            key = (k, STAGES[k][1])
            for i in range(len(m0)):
                if m0[i] != m1[i]:
                    if G0 <= i < G1:
                        tot[key]['g0'] += 1
                    elif G1 <= i < G2:
                        tot[key]['g1p' if (i - G1) % 2 == 0 else 'g1f'] += 1
                    elif G2 <= i < G2 + 4096:
                        tot[key]['g2'] += 1
                    else:
                        other[key].add(i)
            for i in range(len(f0)):
                if f0[i] != f1[i]:
                    fedo[key].add(FED + i - FA6)
    for k in range(first, len(STAGES)):
        key = (k, STAGES[k][1])
        print(f'{k:2d} ${key[1]:x}: {dict(tot[key])}')
        if other[key]:
            print('     module:', ranges(other[key]))
        if fedo[key]:
            print('     fed:', ranges(fedo[key]))


if __name__ == '__main__':
    main()
