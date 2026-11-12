"""Dump the generator's grids after every stage of its main routine $23bb0.

    uv run python -I reversing/captive/py/mapgen/stagedump.py <out.json> d0,d1,d2,d3


Same entry and labelled pokes as gen.py; the run stops at the return address of each `bsr` in $23bb0's base path
($23c86..$23d4a) and after the export $23936 ($200f2), reading G0/G1/G2 there. Output: list of
{after: <callee hex>, step, g0, g1, g2}.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen import R, REGIONS, RET, outpath, start  # noqa: E402
from stclient import StServer  # noqa: E402

# (return address, callee) for each bsr of $23bb0's base path, read from the listing
STAGES = [(0x23c86, 0x2624a), (0x23c8a, 0x2011e), (0x23c8e, 0x201de), (0x23c92, 0x202a2), (0x23ca8, 0x245e2),
          (0x23cb0, 0x263c2), (0x23cb4, 0x244b6), (0x23cb8, 0x24d78), (0x23cbc, 0x24f4c), (0x23cc0, 0x25198),
          (0x23cc4, 0x2533a), (0x23cc8, 0x25198), (0x23ccc, 0x25162), (0x23cd0, 0x263fa), (0x23cd4, 0x25240),
          (0x23cea, 0x2676c), (0x23cee, 0x25c1e), (0x23cf2, 0x256f0), (0x23cf6, 0x25722), (0x23cfa, 0x25414),
          (0x23cfe, 0x2543a), (0x23d02, 0x2419a), (0x23d0a, 0x24d64), (0x23d0e, 0x24128), (0x23d12, 0x240c2),
          (0x23d16, 0x25d88), (0x23d1a, 0x26438), (0x23d1e, 0x26478), (0x23d22, 0x264ac), (0x23d26, 0x264c8),
          (0x23d2a, 0x265cc), (0x23d2e, 0x26606), (0x23d36, 0x24d64), (0x23d3a, 0x2630c), (0x23d3e, 0x26854),
          (0x23d42, 0x26532), (0x23d46, 0x26570), (0x23d4a, 0x268f8), (0x200f2, 0x23936)]


def main():
    d0, d1, d2, d3 = [int(x, 0) for x in sys.argv[2].split(',')]
    s = StServer(R)
    out = []
    try:
        stops = [a for a, _ in STAGES]
        start(s, d0, d1, d2, d3, stops=stops)
        callee = dict(STAGES)
        while True:
            pc = s.reg('pc')
            if pc == RET:
                break
            rec = {'after': f'{callee[pc]:x}', 'step': s.reg('step')}
            for k in ('g0', 'g1', 'g2', 'mvars', 'vars'):
                a, n = REGIONS[k]
                rec[k] = s.read(a, n).hex()
            out.append(rec)
            r = s('run', max_steps=60_000_000, until_pc=[RET] + stops)
            if r['reason'] != 'until':
                sys.exit(f'stopped: {r}')
    finally:
        s.close()
    json.dump(out, open(outpath(sys.argv[1]), 'w'))
    print(len(out), 'stages')
    prev = None
    for rec in out:  # bytes each stage changed in G0/G1/G2
        cur = {k: bytes.fromhex(rec[k]) for k in ('g0', 'g1', 'g2')}
        if prev:
            print(rec['after'], {k: sum(a != b for a, b in zip(cur[k], prev[k])) for k in cur})
        prev = cur


if __name__ == '__main__':
    main()
