"""room_mosaic.py - render a room's real screen-placed terrain mosaic from a live, mid-draw snapshot,
and (--diff) score it pixel-exact against a gameplay screenshot.

Proven mechanism (graphics.md 5th section, 5h/5i): at room entry, `$00e7b0` builds a per-cell
screen-offset table at (A5)+2634 (5h's formula: offset(row,col) = base_offset + row*0x4f8 +
col*0x508). `$00cab6` then walks the room's decoded tile-id grid (A5)+2914 and, for each visible
cell, calls `$00d1f8`, which looks up that cell's screen offset in the (A5)+2634 table, applies a
sub-pixel shift via a table at `$5692`, and appends a 16-byte draw descriptor to a list:
`y0,y1` (bytes 0-1, absolute screen-row clip bounds), `w` (byte 2, width in 16px words, always 2 =
32px here), `h` (byte 3, a secondary height field that occasionally disagrees with `y1-y0` by a few
px - `y1-y0` is the one to trust, see below), `x0,x1` (words at bytes 4-6 and 6-8, absolute screen-
pixel clip bounds, `x1-x0` always 32 in this data), the screen byte-offset (word, byte 8), the
source tile pointer (long, byte 10), and a per-room-constant sub-pixel shift param (word, byte 14).
**(A5)+72 holds a POINTER to that list's base, not the list itself** (`movea.l 72(A5),A3`
dereferences it) - this is the bug that cost an earlier pass its first few live-read attempts, see
graphics.md 5i.

**x0/y0 are already the exact absolute screen pixel position - no further shift-table math needed.**
Earlier passes assumed the descriptor's screen-offset word (byte 8) needed `$5692`'s per-entry
sub-pixel correction applied before use, since offset alone only gives row/col at ~2px granularity.
Reading `x0`/`y0` directly instead (rather than re-deriving position from the offset word) settles
it: across all 76 real entries in the captured room, `x0 == (offset % 160) * 2` and
`y0 == offset // 160` exactly, i.e. the two are mathematically identical, and a per-mosaic (dx,dy)
grid search against the real screenshot found (0,0) was already optimal - there is no residual
uniform sub-pixel offset to correct. The `shift` field (byte 14) is a room-wide constant (128 in
this capture) unrelated to per-tile x/y placement.

`y0,y1` (and `x0,x1`) are the tile's on-screen CLIP window, not just informational: when a tile
partially runs off the drawable area (`y1-y0 < 32`), the visible slice is the BOTTOM `y1-y0` rows of
the 32px source tile (its top `32-(y1-y0)` rows are the off-screen part) - confirmed by the tile
stacks running off the top of the screen (smaller `y1-y0` the further a stack's tile sits above
row 0) and by the resulting pixel match (below).

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
        --out reversing/cadaver/tiles/cavern_mosaic.png --diff reversing/cadaver/gameplay.png

**Match count (CAVERN, this capture): 19079/19749 = 96.6% of covered pixels exact**, drawing tiles
in the list's own order (natural paint order - both a global (dx,dy) search and every row-sorted
paint-order alternative scored worse, confirming list order is correct). The residual ~3.4% clusters
at the overlap edges between adjacent tiles in a stack (same-value palette pixels shuffled by ~1px,
not a wrong tile or wrong position) - plausibly a finer overlap/z-order detail this pass didn't chase
further, not a placement-formula error; not yet fully explained.

**TUNNEL (captured the same way, via the CAVERN->TUNNEL "documented zigzag" - `mechanics.md`
`kbd ff 08`/1.2M, `kbd ff 01`/0.5M, `kbd ff 08`/1.2M, `kbd ff 01`/1.2M from `gameplay_empire.snap`,
`bpc cab6 1 <budget>` armed per leg - hits 52887 steps into the final leg): **10604/11069 = 95.8%
exact against `room2_tunnel_entry.png`** (`--palette-formula st`, matching that screenshot's own
generating tool) - in line with CAVERN. A first pass at this score (1961/9932 = 19.7%, tile-only)
looked like a real content gap (right wall matching, left wall rendering as "generic" art) and sent a
later pass chasing graphics.md 5f's `0xc2` marker byte as the explanation; that marker is real (5f
resolves it fully) but turned out not to be the cause of *that* gap - the actual explanation
(graphics.md 5i-3) was that this file's own palette conversion
(`sprite_array_export.decode_st_interleaved`, `gun*255//7`) disagrees with `tools/snap_render.py`'s
`st_colour` (`gun*36`), the tool that produced `room2_tunnel_entry.png`; `gameplay.png` (CAVERN's
reference) happens to use this file's own formula, which is why only TUNNEL looked broken. The two
formulas were later confirmed unfixable-and-unnecessary to unify (graphics.md 5i-3 addendum: neither
reference is an authentic Hatari render, so there's no ground truth to converge on) - a low `--diff`
score against an older reference screenshot is worth checking against the *other* `--palette-formula`
before trusting it as a content bug. The `0xc2` marker's own item-catalog overlay (graphics.md 5f) -
TUNNEL's one non-tile descriptor entry, previously dropped by the tile-range filter below - is now
rendered too (source pointer and size come straight off the descriptor, no separate catalog lookup
needed), which is what moved TUNNEL's score from 9534/9932 (tile-only) to the total above.
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
SCREEN_W, SCREEN_H = 320, 200


def read_u32(ram, base, a):
    return int.from_bytes(ram[a - base:a - base + 4], "big")


def read_s32(ram, base, a):
    v = read_u32(ram, base, a)
    return v - 0x100000000 if v >= 0x80000000 else v


def read_descriptor_list(ram, base, a5):
    """(A5)+72 is a POINTER to the list, not the list's own base - dereference it."""
    listbase = read_u32(ram, base, a5 + 72)
    entries = []
    for i in range(400):
        addr = listbase + i * LIST_ENTRY_STRIDE
        f10 = read_s32(ram, base, addr + 10)
        if f10 == -1:
            break
        raw = ram[addr - base:addr - base + LIST_ENTRY_STRIDE]
        y0, y1 = raw[0], raw[1]
        x0 = int.from_bytes(raw[4:6], "big")
        entries.append({"y0": y0, "y1": y1, "x0": x0, "w_field": raw[2], "h_field": raw[3],
                         "ptr": f10 & 0xffffffff})
    return entries


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("snap", help="a mid-draw snapshot, see the recipe in this file's docstring")
    ap.add_argument("--palette", default="0x5a9c")
    ap.add_argument("--palette-formula", choices=["ste", "st", "hatari"], default="ste",
                     help="gun-to-RGB conversion: 'ste' is gfxview.ste_colour's gun*255//7 "
                          "(matches gameplay.png, CAVERN's reference); 'st' is snap_render.py's "
                          "st_colour, gun*36 (matches room2_tunnel_entry.png, TUNNEL's reference); "
                          "'hatari' is Hatari's own ConvST_SetupRGBTable (conv_st.c), gun*34 - the "
                          "real emulator conversion, confirmed against Hatari source, but it scores "
                          "0/N exact against BOTH known references (graphics.md 5i-3): neither "
                          "gameplay.png nor room2_tunnel_entry.png is an authentic Hatari-palette "
                          "render, so there is no single formula to unify on - match each reference "
                          "with the formula that was actually used to make it.")
    ap.add_argument("--out", required=True)
    ap.add_argument("--diff", help="gameplay screenshot to score the render against (pixel-exact "
                                    "match count over the tile-covered area)")
    args = ap.parse_args()

    if args.palette_formula == "st":
        def _st_colour(word):
            r, g, b = (word >> 8) & 7, (word >> 4) & 7, word & 7
            return (r * 36, g * 36, b * 36)
        sae.ste_colour = _st_colour
    elif args.palette_formula == "hatari":
        def _hatari_colour(word):
            r, g, b = (word >> 8) & 7, (word >> 4) & 7, word & 7
            return (r * 34, g * 34, b * 34)
        sae.ste_colour = _hatari_colour

    ram, base = load_ram(args.snap)
    regs, ok = snapshot_regs(args.snap)
    if not ok:
        raise SystemExit("snapshot has no saved registers")
    a5 = regs["a5"]

    tile_base = read_u32(ram, base, a5 + 16)
    tile_size = read_u32(ram, base, a5 + 24)
    palette = sae.read_palette(ram, int(args.palette, 16))

    entries = read_descriptor_list(ram, base, a5)
    tiles = [e for e in entries if tile_base <= e["ptr"] < tile_base + tile_size]
    # A non-tile entry's ptr sits in the type-2 item catalog's data area instead (graphics.md
    # 5f's 0xc2 marker): its source pointer is already past that entry's 0x20+4-byte header, and
    # its own full size is the descriptor's w_field*16 x h_field (unlike a tile, where w_field is
    # always 2/32px and h_field can disagree with the real clip height y1-y0).
    items = [e for e in entries if not (tile_base <= e["ptr"] < tile_base + tile_size)]
    print(f"A5={a5:#x}  list entries={len(entries)}  tile entries={len(tiles)}  "
          f"item-catalog entries={len(items)} (graphics.md 5f's 0xc2-sourced overlays)")
    if not tiles:
        raise SystemExit("no tile-catalog entries found - is this really a mid-cab6 snapshot? "
                          "(see the capture recipe in this file's docstring)")

    from PIL import Image
    canvas = Image.new("RGB", (SCREEN_W, SCREEN_H), (0, 0, 0))
    coverage = Image.new("L", (SCREEN_W, SCREEN_H), 0)

    def paste(addr, src_w, src_h, e):
        h = e["y1"] - e["y0"]
        img = sae.decode_st_interleaved(ram, addr, src_w, src_h, 4, palette).convert("RGB")
        # Each source image is a shape on a black (palette index 0) background, not a full
        # rectangle of art - pasting opaquely lets its black corners stomp over the previous
        # entry in the ~50% column/row overlap this placement relies on, producing a comb of
        # gaps instead of a continuous wall. Palette index 0 is the real transparent background
        # here (graphics.md 5i); mask it out.
        idx_img = sae.decode_st_interleaved(ram, addr, src_w, src_h, 4, None)  # "L" mode, idx*17
        # A clipped entry (h < src_h) shows its BOTTOM h rows - the top (src_h-h) ran off-screen.
        top_crop = src_h - h
        crop_img = img.crop((0, top_crop, src_w, src_h))
        mask = idx_img.crop((0, top_crop, src_w, src_h)).point(lambda v: 255 if v != 0 else 0)
        canvas.paste(crop_img, (e["x0"], e["y0"]), mask)
        coverage.paste(mask, (e["x0"], e["y0"]), mask)

    for e in tiles:
        addr = tile_base + (e["ptr"] - tile_base) // TILE_STRIDE * TILE_STRIDE
        paste(addr, 32, 32, e)
    for e in items:
        paste(e["ptr"], e["w_field"] * 16, e["h_field"], e)
    canvas.save(args.out)
    print("wrote", args.out, canvas.size)

    if args.diff:
        import numpy as np
        gameplay = Image.open(args.diff).convert("RGB")
        c = np.array(canvas)
        g = np.array(gameplay)
        m = np.array(coverage) > 0
        total = int(m.sum())
        match = int(((c == g).all(axis=2) & m).sum())
        print(f"diff vs {args.diff}: {match}/{total} covered pixels exact "
              f"({match / total:.4f})")


if __name__ == "__main__":
    main()
