"""Control for gen.py's shortcut entry: compare case 0 of a gen.py json (run with the landing arguments
1,0xffff,14,0 and MAPGEN_POISON=1) with the natural call's result in scratchpad/captive/mg_ret.snap, region by region.

    MAPGEN_POISON=1 uv run python -I reversing/captive/py/mapgen/gen.py land.json 1,0xffff,14,0
    uv run python -I reversing/captive/py/mapgen/cmp_ret.py land.json

Expected: every region `equal`.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen import REGIONS, SNAP, outpath  # noqa: E402
from gfxview import load_ram  # noqa: E402  (tools/, on the path through gen)


def main():
    ram, base = load_ram(SNAP)
    o = json.load(open(outpath(sys.argv[1])))[0]
    for k, (a, n) in REGIONS.items():
        got = bytes.fromhex(o[k])
        ref = ram[a - base:a - base + n]
        diff = [i for i in range(n) if got[i] != ref[i]]
        print(k, f'${a:x}', n, 'equal' if not diff else f'{len(diff)} differ, first at +{diff[0]:#x}')


if __name__ == '__main__':
    main()
