#!/usr/bin/env python3
"""snap_render.py - render a .snap's *live* screen straight to a PNG.

Reads base/rez/palette from the real shifter registers via gfxview.load_video_regs
(the same VideoDisplayRegisters bank the emulator's own headless frame recorder
uses), not a guessed/cached buffer address - immune to games that swap which of
two back buffers is "live" from frame to frame (Cadaver does this; see
reversing/cadaver/README.md's 10th-pass entry on the ScreenBufferA/B trap).

Currently handles rez 0 (320x200x4bpp st-interleaved) only, the only mode any
game reversed in this repo so far has used for live gameplay; extend the
per-rez decode below if a future game needs rez 1/2.

Usage: python tools/snap_render.py foo.snap foo.png
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from gfxview import load_ram, load_video_regs
from PIL import Image


def st_colour(word):
    r, g, b = (word >> 8) & 7, (word >> 4) & 7, word & 7
    return (r * 36, g * 36, b * 36)


def render(snap_path, out_path):
    ram, _ = load_ram(snap_path)
    regs = load_video_regs(snap_path)
    if regs is None:
        sys.exit(f"{snap_path}: not a .snap (no VideoDisplayRegisters bank)")
    base, w, h, bpp = regs["base"], regs["w"], regs["h"], regs["bpp"]
    if (w, h, bpp) != (320, 200, 4):
        sys.exit(f"rez {regs['rez']} ({w}x{h}x{bpp}) not supported yet - only rez 0 is")
    palette = [st_colour(word) for word in regs["palette_words"]]
    img = Image.new("RGB", (w, h))
    px = img.load()
    row_bytes = w * bpp // 8
    for y in range(h):
        row_off = base + y * row_bytes
        for xw in range(0, w, 16):
            word_off = row_off + (xw // 16) * 8
            planes = [int.from_bytes(ram[word_off + p * 2: word_off + p * 2 + 2], "big")
                      for p in range(4)]
            for bit in range(16):
                shift = 15 - bit
                idx = 0
                for p in range(4):
                    idx |= ((planes[p] >> shift) & 1) << p
                px[xw + bit, y] = palette[idx]
    img.save(out_path)
    print(f"wrote {out_path} (base=${base:06x} rez={regs['rez']})", file=sys.stderr)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("snap")
    ap.add_argument("out")
    args = ap.parse_args()
    render(args.snap, args.out)
