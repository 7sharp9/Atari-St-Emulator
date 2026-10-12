"""Gate the minimap people dots ($165b2 -> $16738 -> $e6ee) against a snapshot's screen.

usage: uv run python peep_dots.py <snap> [...]

Transcribes the two dot loops of $165b2 (read from the body, m1_s0.ram):
  1. every object record $51b66..$57f66 (stride 50) with side byte 5 > 0 and
     (side == [$57ffe] or [$5809a] != 0);
  2. for each of the player side's six groups ($51538 + side*$13c, word slot D3 = 0..10)
     with an owner (word 28) and state word 76 == $10: the lead, then, when lead
     byte 7 bit 7 is set, the other party's members (bit 6 clear: the $4f916/$4e514
     chain via +10/+24/+8; set: the $51538 chain via -36/+26).
$16738 colours each dot t_peep_col[$1675a + (signed side) + D4], D4 = 15 when [$4bb41]
bit 0 is set, else 0; a negative byte skips. $e6ee then sets pixel
(record[8], record[10] + 6) with the plane bytes at $e6ae + 4*colour, read from RAM,
so an out-of-range colour (side 6's $10) reproduces whatever the game reads there.

For each blink phase the script predicts every dot and counts how many match the
draw buffer [$2df7c] and the displayed buffer (shifter base). A dot is a hit when the
pixel's 4-bit index equals the predicted index. Dots plotted twice at one pixel
keep the last colour, as the game's draw order does.
"""
import os
import struct
import sys

here = os.path.dirname(os.path.abspath(__file__))
root = here
while not os.path.exists(os.path.join(root, "tools", "rdis.py")):
    root = os.path.dirname(root)
sys.path.insert(0, os.path.join(root, "tools"))
from gfxview import load_ram, load_video_regs  # noqa: E402

RECS, RECS_END, STRIDE = 0x51B66, 0x57F66, 50
SIDES, SIDE_STRIDE = 0x51538, 0x13C
PEEP_COL, PIXCOL = 0x1675A, 0xE6AE


def w(ram, a):
    return struct.unpack_from(">H", ram, a)[0]


def sw(ram, a):
    return struct.unpack_from(">h", ram, a)[0]


def sb(b):
    return b - 256 if b >= 128 else b


def dots(ram, d4):
    """Ordered list of (x, y, colour) the routine plots in this blink phase."""
    out = []

    def plot(side_byte, rec):
        idx = sb(side_byte & 0xFF) + d4
        c = ram[PEEP_COL + idx]
        if c >= 0x80:
            return
        out.append((ram[rec + 8], ram[rec + 10] + 6, c))

    player = w(ram, 0x57FFE)
    show_all = w(ram, 0x5809A) != 0
    for rec in range(RECS, RECS_END, STRIDE):
        s = sb(ram[rec + 5])
        if s > 0 and (show_all or (s & 0xFF) == (player & 0xFF)):
            plot(s, rec)

    a3 = SIDES + (player * SIDE_STRIDE & 0xFFFF)
    for d3 in range(0, 12, 2):
        owner = w(ram, a3 + 28 + d3)
        if owner == 0 or w(ram, a3 + 76 + d3) != 0x10:
            continue
        a6 = RECS + sw(ram, a3 + 64 + d3)
        plot(owner, a6)
        if not ram[a6 + 7] & 0x80:
            continue
        if not ram[a6 + 7] & 0x40:
            a5 = 0x4F916 + sw(ram, a6 + 34)
            a2 = 0x4E514 + sw(ram, a5 + 14)
            d0 = w(ram, a2 + 2)
            while d0:
                a5 = 0x4F916 + sb16(d0)
                d0 = w(ram, a5 + 10)
                while d0:
                    a4 = RECS + sb16(d0)
                    if sb(ram[a4 + 5]) > 0 and a4 != a6:
                        plot(ram[a4 + 5], a4)
                    d0 = w(ram, a4 + 24)
                d0 = w(ram, a5 + 8)
        else:
            a4 = RECS + sw(ram, a6 + 28)
            a2 = SIDES + sw(ram, a4 + 42)
            d0 = w(ram, a2 - 36)
            while d0:
                a4 = RECS + sb16(d0)
                if sb(ram[a4 + 5]) > 0 and a4 != a6:
                    plot(ram[a4 + 5], a4)
                d0 = w(ram, a4 + 26)
    return out


def sb16(v):
    return v - 0x10000 if v >= 0x8000 else v


def pixel_index(ram, base, x, y):
    a = base + y * 160 + (x >> 4) * 8 + ((x >> 3) & 1)
    bit = 7 - (x & 7)
    return sum(((ram[a + 2 * p] >> bit) & 1) << p for p in range(4))


def colour_index(ram, c, x):
    """The 4-bit index $e6ee writes for colour c at column x (plane bytes $e6ae+4c)."""
    bit = 7 - (x & 7)
    return sum(((ram[PIXCOL + 4 * c + p] >> bit) & 1) << p for p in range(4))


def main():
    for snap in sys.argv[1:]:
        ram, _ = load_ram(snap)
        shown = load_video_regs(snap)["base"]
        draw = struct.unpack_from(">I", ram, 0x2DF7C)[0]
        print(f"{os.path.basename(snap)}: player side {w(ram, 0x57FFE)}, $5809a {w(ram, 0x5809A)}, "
              f"$4bb41 bit0 {ram[0x4BB41] & 1}, draw ${draw:06x}, shown ${shown:06x}")
        for d4 in (0, 15):
            ds = dots(ram, d4)
            final = {}
            for x, y, c in ds:
                final[(x, y)] = colour_index(ram, c, x)
            cols = sorted({c for _, _, c in ds})
            res = []
            for name, base in (("draw", draw), ("shown", shown)):
                hit = sum(pixel_index(ram, base, x, y) == i for (x, y), i in final.items())
                res.append(f"{name} {hit}/{len(final)}")
            print(f"  D4={d4:2}: {len(ds)} plots, {len(final)} pixels, colours {cols}: " + ", ".join(res))


if __name__ == "__main__":
    main()
