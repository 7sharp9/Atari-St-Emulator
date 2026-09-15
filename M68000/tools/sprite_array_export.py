"""sprite_array_export.py - batch-export every entry of a struct-driven sprite/object
array as individual PNGs plus a contact sheet and a manifest.

Built in the Cadaver spike (7th pass) after finding that a sprite array's real per-object
width/height/bitmap-pointer are ordinary struct fields (Cadaver: offsets +50/+51/+52 on a
70-byte-stride array), not something you have to guess a fixed grid size for. Rendering at
a guessed uniform tile size (e.g. 32x32) produces sheared, cross-contaminated garbage the
moment objects differ in size - this tool reads each entry's own dimensions instead.

Game-agnostic: works for any game whose sprite/entity table is a fixed-stride array of
fixed-format structs with a width byte, a height byte, and a 4-byte big-endian bitmap
pointer at known offsets. Point it at a `.snap`, the array base/stride/count, and those
three offsets.

    python tools/sprite_array_export.py game.snap --base 0x38338 --stride 0x46 --count 22 \
        --w-off 50 --h-off 51 --ptr-off 52 --w-unit 16 --palette 0x5a9c \
        --out-dir reversing/cadaver/sprites

Also supports a single arbitrary region (no array), for one-off checks:

    python tools/sprite_array_export.py game.snap --region 0x2ca84 32 42 --palette 0x5a9c \
        --out reversing/cadaver/player_idle.png

`--array-ptr-field <addr>` reads the array's own base from a pointer field instead of taking
`--base` literally (e.g. Cadaver's array base lives at a fixed offset from A5, so the base
itself moves across snapshots/reboots - read it fresh rather than hardcoding a stale value).
"""
import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gfxview import load_ram, ste_colour  # noqa: E402


def decode_st_interleaved(ram, off, width, height, bpp=4, palette=None):
    """One sprite/tile at `off`: standard ST-interleaved planar, `width` a multiple of 16px."""
    import numpy as np
    from PIL import Image

    row_bytes = width // 16 * 2 * bpp
    n = row_bytes * height
    buf = ram[off:off + n]
    if len(buf) < n:
        buf = buf + b"\x00" * (n - len(buf))
    a = np.frombuffer(buf, np.uint8).reshape(height, row_bytes) if n else \
        np.zeros((height, row_bytes), np.uint8)
    idx = np.zeros((height, width), np.uint8)
    for x in range(width):
        wg, bit = x // 16, 15 - (x % 16)
        val = np.zeros(height, np.uint8)
        for p in range(bpp):
            o = wg * bpp * 2 + p * 2
            word = (a[:, o].astype(np.uint16) << 8) | a[:, o + 1]
            val |= (((word >> bit) & 1) << p).astype(np.uint8)
        idx[:, x] = val
    if palette:
        colors = [ste_colour(w) for w in palette] + [(0, 0, 0)] * (16 - len(palette))
        rgb = np.zeros((height, width, 3), np.uint8)
        for i, c in enumerate(colors):
            rgb[idx == i] = c
        return Image.fromarray(rgb, "RGB")
    return Image.fromarray((idx * 17).astype(np.uint8), "L")


def read_palette(ram, addr):
    return [int.from_bytes(ram[addr + k * 2: addr + k * 2 + 2], "big") for k in range(16)]


def contact_sheet(imgs, ncols, scale, gap=2, bg=(40, 40, 40)):
    from PIL import Image

    maxw = max(i.width for i in imgs)
    maxh = max(i.height for i in imgs)
    nrows = (len(imgs) + ncols - 1) // ncols
    canvas = Image.new("RGB", (ncols * (maxw + gap), nrows * (maxh + gap)), bg)
    for i, img in enumerate(imgs):
        cx, cy = i % ncols, i // ncols
        canvas.paste(img, (cx * (maxw + gap), cy * (maxh + gap)))
    return canvas.resize((canvas.width * scale, canvas.height * scale), Image.NEAREST)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help=".snap file")
    ap.add_argument("--palette", help="hex address of a 16-word $0RGB palette table")
    ap.add_argument("--scale", type=int, default=6, help="NEAREST upscale for saved PNGs")

    ap.add_argument("--region", nargs=3, metavar=("ADDR", "W", "H"),
                     help="decode one region: hex addr, width px, height rows")
    ap.add_argument("--out", help="output PNG path for --region")

    ap.add_argument("--base", help="hex array base address (literal)")
    ap.add_argument("--array-ptr-field", help="hex address of a 4-byte pointer to the array base "
                     "(read fresh instead of trusting a hardcoded --base)")
    ap.add_argument("--stride", help="hex bytes per array entry")
    ap.add_argument("--count", type=int, help="number of array entries")
    ap.add_argument("--w-off", type=int, help="byte offset of the width field (1 byte)")
    ap.add_argument("--h-off", type=int, help="byte offset of the height field (1 byte)")
    ap.add_argument("--ptr-off", type=int, help="byte offset of the bitmap pointer (4 bytes, BE)")
    ap.add_argument("--state-off", type=int, help="optional byte offset of a state/type field, "
                     "recorded in the manifest only")
    ap.add_argument("--w-unit", type=int, default=16,
                     help="pixels per unit in the width field (Cadaver: 16)")
    ap.add_argument("--out-dir", help="output directory for --base/array mode")
    ap.add_argument("--cols", type=int, default=6, help="contact sheet columns")
    args = ap.parse_args()

    ram, base = load_ram(args.input)
    palette = read_palette(ram, int(args.palette, 16)) if args.palette else None

    if args.region:
        addr, w, h = int(args.region[0], 16), int(args.region[1]), int(args.region[2])
        img = decode_st_interleaved(ram, addr, w, h, 4, palette)
        img = img.resize((img.width * args.scale, img.height * args.scale))
        out = args.out or f"sprite_{addr:x}_{w}x{h}.png"
        img.save(out)
        print(f"wrote {out} ({w}x{h} at {addr:#x}, scale {args.scale})")
        return

    if args.base is None and args.array_ptr_field is None:
        sys.exit("pass --region ADDR W H, or --base/--array-ptr-field + --stride --count "
                 "--w-off --h-off --ptr-off")

    if args.array_ptr_field:
        pf = int(args.array_ptr_field, 16)
        arr_base = int.from_bytes(ram[pf:pf + 4], "big")
        print(f"array base read from pointer field {pf:#x}: {arr_base:#x}")
    else:
        arr_base = int(args.base, 16)

    stride = int(args.stride, 16)
    out_dir = Path(args.out_dir or "sprite_array_export_out")
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    imgs = []
    for i in range(args.count):
        entry = arr_base + i * stride
        w_units = ram[entry + args.w_off]
        h = ram[entry + args.h_off]
        ptr = int.from_bytes(ram[entry + args.ptr_off:entry + args.ptr_off + 4], "big")
        w = w_units * args.w_unit
        state = ram[entry + args.state_off] if args.state_off is not None else None
        img = decode_st_interleaved(ram, ptr, w, h, 4, palette) if w and h else None
        fname = f"slot{i:02d}_{ptr:x}_{w}x{h}.png"
        if img is not None:
            img.resize((img.width * args.scale, img.height * args.scale)).save(out_dir / fname)
            imgs.append(img)
        rows.append({"slot": i, "entry_addr": f"{entry:#x}", "state": state,
                      "width_px": w, "height_rows": h, "bitmap_ptr": f"{ptr:#x}",
                      "file": fname if img is not None else ""})
        print(f"slot {i:2d} entry={entry:#x} state={state} {w}x{h} ptr={ptr:#x} -> {fname}")

    with open(out_dir / "manifest.csv", "w", newline="") as f:
        wtr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wtr.writeheader()
        wtr.writerows(rows)
    print(f"wrote {out_dir/'manifest.csv'} ({len(rows)} entries)")

    if imgs:
        sheet = contact_sheet(imgs, args.cols, 2)
        sheet.save(out_dir / "contact_sheet.png")
        print(f"wrote {out_dir/'contact_sheet.png'} ({sheet.size[0]}x{sheet.size[1]})")


if __name__ == "__main__":
    main()
