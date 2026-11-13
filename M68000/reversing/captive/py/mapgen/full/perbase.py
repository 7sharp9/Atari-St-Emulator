"""Per base: groups, members, free bytes left in the group list, and the groups added by $25d88 and $2543a.

    uv run python -I reversing/captive/py/mapgen/full/perbase.py <d2> <d0> [<d0> ...]
"""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import groups as G  # noqa: E402
import common  # noqa: E402

d2 = int(sys.argv[1])
for d0 in [int(a) for a in sys.argv[2:]]:
    common.DUMPS = G.MINE if os.path.exists(os.path.join(G.MINE, f'd{d2}_{d0}.bin')) else G.SHARED
    recs = common.load(d2, d0)
    f = recs[-1][2]
    gs = G.groups(f)
    free = (f[0x1c77e - common.FED + 2] << 8) | f[0x1c77e - common.FED + 3]
    st = G.per_stage(recs)
    m = recs[-1][1]
    print(f'd2={d2} d0={d0:3d} groups {len(gs):3d} members {sum((len(g) - 8) // 8 for g in gs):4d} free {free:4d} '
          f'$25d88 {st[0x25d88]:3d} $25722 {st[0x25722]:3d} $2543a {st[0x2543a]:3d} floors(13274 at start) {recs[8][1][13275]} sheetmask {m[13749]:#x}')
