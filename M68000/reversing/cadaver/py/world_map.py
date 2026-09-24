"""world_map.py - walk the type-3 resource-manager table (mechanics.md sec38a/38d) and decode
every populated room's world-space bounding-box rectangle, to build the full room-adjacency graph.

Resource manager (sec38a): 18-byte type record at (A5)+96, indexed by type. Type 3 is the room
table: index-table base $4ac36, data-area base $6bf0a, 100 slots. Each index-table entry is 4
bytes: [+0 size(word)][+2 offset(word)]; a zero size means the slot is unpopulated. A populated
slot's room record lives at data_area + offset, and (sec38d) bytes [+1 x0][+3 y0][+4 width]
[+5 height] (all unsigned bytes) are its world-grid rectangle [x0,y0]-[x0+width,y0+height]
(inclusive both ends, confirmed by the TUNNEL/CAVERN pair touching exactly at their shared edge).

These fields are static per snapshot (game data, not per-frame state), so any snapshot with the
resource manager initialised works; room2_tunnel_entry.snap is used by convention.

    python reversing/cadaver/py/world_map.py <snap> [--out world_map.png]

Prints every populated slot's rectangle and every pair of rectangles that touch or overlap
(the adjacency graph), and optionally renders the rectangles into a PNG map.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
from gfxview import load_ram  # noqa: E402

INDEX_TABLE = 0x4ac36
DATA_AREA = 0x6bf0a
SLOT_COUNT = 100

KNOWN_NAMES = {0: "CAVERN", 1: "TUNNEL"}


def read_u16(ram, addr, base):
    o = addr - base
    return int.from_bytes(ram[o:o + 2], "big")


def read_room(ram, base, slot):
    entry_addr = INDEX_TABLE + slot * 4
    size = read_u16(ram, entry_addr, base)
    offset = read_u16(ram, entry_addr + 2, base)
    if size == 0:
        return None
    rec = DATA_AREA + offset
    o = rec - base
    x0, y0, w, h = ram[o + 1], ram[o + 3], ram[o + 4], ram[o + 5]
    return {"slot": slot, "size": size, "offset": offset, "rec": rec,
            "x0": x0, "y0": y0, "w": w, "h": h, "x1": x0 + w, "y1": y0 + h}


def adjacency(a, b):
    """Classify how two inclusive-grid rectangles relate: overlapping (share interior cells),
    edge (share a boundary segment, e.g. TUNNEL/CAVERN's y1+1==y0 case from sec38d), corner (share
    only a single grid point), or None. Gap of exactly 1 counts as touching: sec38d's own
    TUNNEL/CAVERN pair sits with CAVERN's y0 one past TUNNEL's y1, not overlapping."""
    x_ov = min(a["x1"], b["x1"]) - max(a["x0"], b["x0"])  # >=0 real overlap, -1 adjacent, <-1 apart
    y_ov = min(a["y1"], b["y1"]) - max(a["y0"], b["y0"])
    if x_ov < -1 or y_ov < -1:
        return None
    if x_ov >= 0 and y_ov >= 0:
        return "overlap"
    if x_ov == -1 and y_ov == -1:
        return "corner"
    return "edge"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("snap")
    ap.add_argument("--out", help="write a rendered map PNG here")
    args = ap.parse_args()

    ram, base = load_ram(args.snap)

    rooms = [r for s in range(SLOT_COUNT) if (r := read_room(ram, base, s)) is not None]
    print(f"{len(rooms)}/{SLOT_COUNT} populated slots")
    for r in rooms:
        name = KNOWN_NAMES.get(r["slot"], "")
        print(f"  slot {r['slot']:3d} {name:8s} rec={r['rec']:#07x} size={r['size']:4d} "
              f"rect=[{r['x0']:3d},{r['y0']:3d}]-[{r['x1']:3d},{r['y1']:3d}] "
              f"(w={r['w']},h={r['h']})")

    print("\nadjacency (touching or overlapping rectangles):")
    edges = []
    for i, a in enumerate(rooms):
        for b in rooms[i + 1:]:
            kind = adjacency(a, b)
            if kind:
                edges.append((a["slot"], b["slot"], kind))
    for sa, sb, kind in edges:
        print(f"  slot {sa:3d} -- slot {sb:3d}  ({kind})")
    print(f"\n{len(edges)} adjacent pairs "
          f"({sum(k == 'edge' for _, _, k in edges)} edge, "
          f"{sum(k == 'overlap' for _, _, k in edges)} overlap, "
          f"{sum(k == 'corner' for _, _, k in edges)} corner)")

    if args.out:
        import numpy as np
        from PIL import Image, ImageDraw

        xs = [c for r in rooms for c in (r["x0"], r["x1"])]
        ys = [c for r in rooms for c in (r["y0"], r["y1"])]
        minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
        scale = 12
        pad = 4
        img_w = (maxx - minx + 1 + 2 * pad) * scale
        img_h = (maxy - miny + 1 + 2 * pad) * scale
        img = Image.new("RGB", (img_w, img_h), (20, 20, 24))
        d = ImageDraw.Draw(img)
        for r in rooms:
            x0 = (r["x0"] - minx + pad) * scale
            y0 = (r["y0"] - miny + pad) * scale
            x1 = (r["x1"] - minx + pad + 1) * scale
            y1 = (r["y1"] - miny + pad + 1) * scale
            d.rectangle([x0, y0, x1, y1], outline=(120, 200, 120), width=2)
            label = KNOWN_NAMES.get(r["slot"], str(r["slot"]))
            d.text((x0 + 2, y0 + 2), label, fill=(220, 220, 120))
        img.save(args.out)
        print("wrote", args.out)


if __name__ == "__main__":
    main()
