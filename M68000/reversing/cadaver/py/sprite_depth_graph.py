"""sprite_depth_graph.py - check the per-entity depth rows at 68(A5) against the box relation of `$00d656`
(graphics.md 5k), and count screen-overlapping pairs whose table-index order is not a back-to-front order.

For entity A (placement table 56(A5), stride $46; bytes 0-5 = x lead, y lead, x trail, y trail, z top, z base)
row[A] (16 bytes at 68(A5)+16*index; bytes 4..15 are a 96-bit set indexed by entity index) holds every B with
    A.xlead >= B.xtrail and A.ylead >= B.ytrail and A.ztop >= B.zbase
i.e. A is not behind B on any axis, so B must be painted before A (B is "behind" A).

    python reversing/cadaver/py/sprite_depth_graph.py <snap> [<snap> ...]

Prints, per snapshot, rows matching the relation (set equality) and the index-order violation count.
Word 0 of a row is a counter that does not always equal the set's size (not explained, not used here).
"""
import os, struct, sys
ROOT = os.environ.get("M68000_ROOT", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from gfxview import load_ram, snapshot_regs  # noqa: E402


def read_entities(snap):
    regs, ok = snapshot_regs(snap)
    ram, _ = load_ram(snap)
    a5 = regs["a5"] & 0xFFFFFF
    w = lambda a: struct.unpack(">H", ram[a & 0xFFFFFF:(a & 0xFFFFFF) + 2])[0]
    l = lambda a: struct.unpack(">I", ram[a & 0xFFFFFF:(a & 0xFFFFFF) + 4])[0]
    tab, occ, n = l(a5 + 56), l(a5 + 68), w(a5 + 1152)
    ents, rows = [], []
    for i in range(n):
        e = ram[tab + 0x46 * i: tab + 0x46 * (i + 1)]
        row = ram[occ + 16 * i: occ + 16 * i + 16]
        ents.append(dict(i=i, live=not (e[0] == 0xFF and e[1] == 0xFF) and e[:4] != b"\xff\xff\xff\xfe",
                         xl=e[0], yl=e[1], xt=e[2], yt=e[3], zt=e[4], zb=e[5],
                         sx=struct.unpack(">H", e[18:20])[0], ex=struct.unpack(">H", e[46:48])[0], sy=e[20], ey=e[23]))
        rows.append({k for k in range(96) if row[4 + k // 8] >> (k % 8) & 1})
    return ents, rows


def front(a, o):
    return a["xl"] >= o["xt"] and a["yl"] >= o["yt"] and a["zt"] >= o["zb"]


def main():
    for snap in sys.argv[1:]:
        ents, rows = read_entities(snap)
        live = [e for e in ents if e["live"]]
        liveset = {e["i"] for e in live}
        ok = sum(rows[a["i"]] & liveset == {o["i"] for o in live if o["i"] != a["i"] and front(a, o)} for a in live)
        L = [e for e in live if e["sx"] < 0x8000]
        ov = lambda a, o: a["sx"] < o["ex"] and o["sx"] < a["ex"] and a["sy"] < o["ey"] and o["sy"] < a["ey"]
        wrong = good = 0
        for i, a in enumerate(L):
            for o in L[i + 1:]:
                if ov(a, o):
                    if front(a, o) and not front(o, a): wrong += 1
                    else: good += 1
        print(f"{snap}: rows matching the box relation {ok}/{len(live)}; screen-overlapping pairs with index order "
              f"correct {good}, wrong {wrong}")


main()
