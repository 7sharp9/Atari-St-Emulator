"""room_tile_grid.py - decode Cadaver's per-room terrain tile grid at (A5)+2914 and render it
against the shared tile catalog at (A5)+16.

Proven mechanism (graphics.md 5th section, `$00add0`-`$00ae62` decode / `$00cab6`-`$00cb28` draw):
each room's wall/floor layout is NOT stored as pixel art. A small per-room byte stream (resource
type 1, keyed by the room's own slot via the type-3/type-1 resource manager, mechanics.md section 2) is
run-length decoded into a live table at (A5)+2914: two passes, one sized by the room record's width
byte (+4), one by its height byte (+5, mechanics.md sections 4 and 5), each pass holding one ragged column per
width/height unit - a wall "height-field" stack of tile ids, not a rectangular grid. Cell values with
the top bit set are a separate, mostly-inert marker channel (graphics.md 5f), not ordinary tile ids;
this script renders them as a hatched placeholder rather than guessing a tile.

Each plain tile id indexes a flat, shared, boot-time-loaded 32x32 4bpp catalog at (A5)+16, stride
0x200 (512) bytes - not a per-room resource. (A5)+24 gives the catalog's byte size (0xa000 = 80
tiles this session; re-read live, don't hardcode across builds/sessions).

    python reversing/cadaver/py/room_tile_grid.py <snap> --room-record 0x6bf0a --w 10 --h 10 \
        --json out.json --png out.png

Room record address and w/h are read live from mechanics.md sections 2 and 4's type-3 table for a given room
slot if --room-slot is passed instead of --room-record/--w/--h; both forms re-derive (A5), the tile
catalog base/size and the palette fresh from the snapshot, per the workstream's "A5-relative fields
are build-relocatable" rule (mechanics.md, Known traps).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
from gfxview import load_ram, snapshot_regs  # noqa: E402
import sprite_array_export as sae  # noqa: E402

GRID_OFF = 2914       # (A5)+2914: decoded tile-id table, 20 rows x 8 words x 2 bytes = 320 bytes
ROWS_PER_PASS = 10     # reserved rows per pass, regardless of the room's real width/height
CELL = 32
TYPE3_INDEX, TYPE3_DATA = 0x4ac36, 0x6bf0a  # mechanics.md section 2; re-derive per build, not hardcoded


def read_u8(ram, base, a):
    return ram[a - base]


def read_u16(ram, base, a):
    return int.from_bytes(ram[a - base:a - base + 2], "big")


def read_u32(ram, base, a):
    return int.from_bytes(ram[a - base:a - base + 4], "big")


def room_record_for_slot(ram, base, slot):
    """mechanics.md section 2: type-3 index entry -> (size, offset) into the type-3 data area."""
    entry = TYPE3_INDEX + slot * 4
    offset = read_u16(ram, base, entry + 2)
    return TYPE3_DATA + offset


def decode_grid(ram, base, a5, w, h):
    """Two ragged column-stacks (width-pass, height-pass); each column is the run of nonzero
    tile-id bytes for that width/height unit, in on-disk decode order (direction not proven,
    graphics.md 5e)."""
    table = a5 + GRID_OFF
    words = [read_u16(ram, base, table + i * 2) for i in range(ROWS_PER_PASS * 2 * 8)]
    rows = [words[i * 8:(i + 1) * 8] for i in range(ROWS_PER_PASS * 2)]

    def strip(rowset, n):
        cols = []
        for r in rowset[:n]:
            vals = []
            for v in r:
                if v == 0:
                    break
                vals.append(v)
            cols.append(vals)
        return cols

    width_pass = strip(rows[0:ROWS_PER_PASS], w)
    height_pass = strip(rows[ROWS_PER_PASS:ROWS_PER_PASS * 2], h)
    return width_pass, height_pass


def render_infographic(ram, base, tile_base, tile_stride, palette, panels, out_path,
                        scale=3, pad=2, label_h=12):
    from PIL import Image, ImageDraw

    def tile_img(tid):
        special = tid >= 0x80
        if special:
            img = Image.new("RGB", (CELL, CELL), (60, 10, 10))
            d = ImageDraw.Draw(img)
            d.line([(0, 0), (CELL - 1, CELL - 1)], fill=(200, 40, 40))
            d.line([(0, CELL - 1), (CELL - 1, 0)], fill=(200, 40, 40))
        else:
            addr = tile_base + tid * tile_stride
            img = sae.decode_st_interleaved(ram, addr, CELL, CELL, 4, palette).convert("RGB")
        return img, special

    def render_strip(cols, title):
        ncols = len(cols)
        nrows = max((len(c) for c in cols), default=1) or 1
        cellw = CELL * scale + pad
        cellh = CELL * scale + pad + label_h
        W = ncols * cellw + pad
        H = nrows * cellh + pad + 20
        sheet = Image.new("RGB", (W, H), (25, 25, 25))
        d = ImageDraw.Draw(sheet)
        d.text((4, 2), title, fill=(230, 230, 230))
        for ci, col in enumerate(cols):
            for ri, tid in enumerate(col):
                img, special = tile_img(tid)
                img = img.resize((CELL * scale, CELL * scale), Image.NEAREST)
                x = pad + ci * cellw
                y = 20 + pad + ri * cellh
                sheet.paste(img, (x, y))
                d.text((x, y + CELL * scale), f"{tid:#04x}",
                       fill=(180, 220, 180) if not special else (255, 120, 120))
            d.text((pad + ci * cellw, H - 16), f"col{ci}", fill=(140, 140, 140))
        return sheet

    strips = [render_strip(cols, title) for cols, title in panels]
    totalW = max(s.width for s in strips)
    totalH = sum(s.height for s in strips) + 10 * (len(strips) - 1)
    combined = Image.new("RGB", (totalW, totalH), (15, 15, 15))
    y = 0
    for s in strips:
        combined.paste(s, (0, y))
        y += s.height + 10
    combined.save(out_path)
    return combined.size


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("snap")
    ap.add_argument("--room-slot", type=int, help="room slot index (mechanics.md section 4) - derives "
                     "the room record from the live type-3 table")
    ap.add_argument("--room-record", help="hex room-record address (alternative to --room-slot)")
    ap.add_argument("--w", type=int, help="room width in tile units (record byte +4); required "
                     "with --room-record")
    ap.add_argument("--h", type=int, help="room height in tile units (record byte +5)")
    ap.add_argument("--room-name", default="ROOM", help="label for the infographic titles")
    ap.add_argument("--tile-base", help="hex tile-catalog base; default: read live from (A5)+16")
    ap.add_argument("--tile-stride", default="0x200", help="hex bytes per tile (default 0x200)")
    ap.add_argument("--palette", default="0x5a9c", help="hex palette address")
    ap.add_argument("--json", help="write the decoded column-stacks here")
    ap.add_argument("--png", help="write the tile infographic here")
    args = ap.parse_args()

    ram, base = load_ram(args.snap)
    regs, ok = snapshot_regs(args.snap)
    if not ok:
        raise SystemExit("snapshot has no saved registers")
    a5 = regs["a5"]

    if args.room_slot is not None:
        rec = room_record_for_slot(ram, base, args.room_slot)
        w = read_u8(ram, base, rec + 4)
        h = read_u8(ram, base, rec + 5)
    elif args.room_record and args.w and args.h:
        rec = int(args.room_record, 16)
        w, h = args.w, args.h
    else:
        raise SystemExit("pass --room-slot, or --room-record --w --h")

    print(f"A5={a5:#x}  room_record={rec:#x}  w={w} h={h}")

    width_pass, height_pass = decode_grid(ram, base, a5, w, h)
    print(f"width-pass ({w} cols):", width_pass)
    print(f"height-pass ({h} cols):", height_pass)

    if args.json:
        with open(args.json, "w") as f:
            json.dump({"room_record": f"{rec:#x}", "w": w, "h": h,
                       "width_pass": width_pass, "height_pass": height_pass}, f, indent=1)
        print("wrote", args.json)

    if args.png:
        tile_base = int(args.tile_base, 16) if args.tile_base else read_u32(ram, base, a5 + 16)
        tile_stride = int(args.tile_stride, 16)
        palette = sae.read_palette(ram, int(args.palette, 16))
        size = render_infographic(
            ram, base, tile_base, tile_stride, palette,
            [(width_pass, f"{args.room_name} - width-pass wall face (w={w})"),
             (height_pass, f"{args.room_name} - height-pass wall face (h={h})")],
            args.png)
        print("wrote", args.png, size)


if __name__ == "__main__":
    main()
