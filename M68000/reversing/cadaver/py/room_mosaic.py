"""room_mosaic.py - render a room's real screen-placed terrain mosaic from a live, mid-draw snapshot.

Proven mechanism (graphics.md 5th section, 5h/5i): at room entry, `$00e7b0` builds a per-cell
screen-offset table at (A5)+2634 (5h's formula: offset(row,col) = base_offset + row*0x4f8 +
col*0x508). `$00cab6` then walks the room's decoded tile-id grid (A5)+2914 and, for each visible
cell, calls `$00d1f8`, which looks up that cell's screen offset in the (A5)+2634 table and appends a
16-byte draw descriptor - {y0,y1,w,h,x0,x1,screen_offset,source_ptr,shift} - to a list. **(A5)+72
holds a POINTER to that list's base, not the list itself** (`movea.l 72(A5),A3` dereferences it) -
this is the bug that cost this pass its first few live-read attempts, see graphics.md 5i.

The list is a scratch buffer, rebuilt fresh each room entry and not preserved afterward, so it can
only be read from a snapshot taken *during* the room-entry draw, not from ordinary steady-state
gameplay snapshots (confirmed empirically: 8 different steady-state/mid-crossing snapshots all show
stale, non-tile data there). Capture one with the REPL, e.g. for the TUNNEL->CAVERN crossing from
`room2_tunnel_entry.snap` (the recipe `mechanics.md` already proved gets a real crossing):

    kbd ff 02
    bpc cab6 1 3000000
    s 5000
    snap scratchpad/cadaver/mid_cab6_cavern.snap
    q

(piped on stdin to `ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume
room2_tunnel_entry.snap repl`). The `s 5000` after the `cab6` hit lets `$00d1f8` finish building the
list before the snapshot is taken; the exact count isn't critical, cab6's whole per-room walk is a
few hundred instructions.

    python reversing/cadaver/py/room_mosaic.py scratchpad/cadaver/mid_cab6_cavern.snap \
        --out reversing/cadaver/tiles/cavern_mosaic.png

This is a rough placement (screen_offset decoded as row=offset//160, byte_col=offset%160,
pixel_x=byte_col*2, ignoring `$00d1f8`'s own sub-pixel shift-table adjustment, graphics.md 5i), good
enough to prove the mechanism visually - not yet a byte-exact pixel-diff against gameplay.png.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
from gfxview import load_ram, snapshot_regs  # noqa: E402
import sprite_array_export as sae  # noqa: E402

TILE_STRIDE = 0x200
LIST_ENTRY_STRIDE = 16
SCREEN_ROW_BYTES = 160  # 320px * 4bpp / 8


def read_u32(ram, base, a):
    return int.from_bytes(ram[a - base:a - base + 4], "big")


def read_s32(ram, base, a):
    v = read_u32(ram, base, a)
    return v - 0x100000000 if v >= 0x80000000 else v


def read_s16(ram, base, a):
    v = int.from_bytes(ram[a - base:a - base + 2], "big")
    return v - 0x10000 if v >= 0x8000 else v


def read_descriptor_list(ram, base, a5):
    """(A5)+72 is a POINTER to the list, not the list's own base - dereference it."""
    listbase = read_u32(ram, base, a5 + 72)
    entries = []
    for i in range(400):
        addr = listbase + i * LIST_ENTRY_STRIDE
        f10 = read_s32(ram, base, addr + 10)
        if f10 == -1:
            break
        f8 = read_s16(ram, base, addr + 8)
        entries.append((f8, f10 & 0xffffffff))
    return entries


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("snap", help="a mid-draw snapshot, see the recipe in this file's docstring")
    ap.add_argument("--palette", default="0x5a9c")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    ram, base = load_ram(args.snap)
    regs, ok = snapshot_regs(args.snap)
    if not ok:
        raise SystemExit("snapshot has no saved registers")
    a5 = regs["a5"]

    tile_base = read_u32(ram, base, a5 + 16)
    tile_size = read_u32(ram, base, a5 + 24)
    palette = sae.read_palette(ram, int(args.palette, 16))

    entries = read_descriptor_list(ram, base, a5)
    tiles = [(off, (ptr - tile_base) // TILE_STRIDE) for off, ptr in entries
             if tile_base <= ptr < tile_base + tile_size]
    print(f"A5={a5:#x}  list entries={len(entries)}  tile entries={len(tiles)} "
          f"(non-tile entries are this room's object/sprite descriptors, not rendered here)")
    if not tiles:
        raise SystemExit("no tile-catalog entries found - is this really a mid-cab6 snapshot? "
                          "(see the capture recipe in this file's docstring)")

    rows = [off // SCREEN_ROW_BYTES for off, _ in tiles]
    row_shift = -min(rows)
    from PIL import Image
    canvas = Image.new("RGB", (320, max(rows) + row_shift + 32), (0, 0, 0))
    for off, tid in tiles:
        row = off // SCREEN_ROW_BYTES + row_shift
        col_byte = off % SCREEN_ROW_BYTES
        px = col_byte * 2
        addr = tile_base + tid * TILE_STRIDE
        img = sae.decode_st_interleaved(ram, addr, 32, 32, 4, palette).convert("RGB")
        # Each 32x32 tile is a cube shape on a black (palette index 0) background, not a
        # full square of art - pasting opaquely lets every tile's black corners stomp over
        # the previous tile in the ~50% column/row overlap this placement relies on,
        # producing a comb of gaps instead of a continuous wall. Palette index 0 is the
        # real transparent background here (graphics.md 5i); mask it out.
        idx_img = sae.decode_st_interleaved(ram, addr, 32, 32, 4, None)  # "L" mode, idx*17
        mask = idx_img.point(lambda v: 255 if v != 0 else 0)
        canvas.paste(img, (px, row), mask)
    canvas.save(args.out)
    print("wrote", args.out, canvas.size)


if __name__ == "__main__":
    main()
