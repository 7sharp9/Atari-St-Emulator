"""Render an Atari ST framebuffer dump to a PNG.

Added in the thirty-fourth pass of atari-st-emulator-next-instructions, once a diskless
cold boot was confirmed to reach the GEM desktop and paint it into screen RAM - there was
no way to actually *look* at the emulator's video output before this.

Feed it the raw bytes of screen RAM (32000 bytes starting at _v_bas_ad / $44e, which the
REPL's `m <base> 32000` prints as space-separated hex), plus the shifter resolution byte
($FFFF8260 & 3) and, for the colour modes, the 16-word palette ($FFFF8240..$FFFF825F).

  # in the emulator REPL, with PC parked anywhere sane:
  #   m ffff8260 1      -> rez
  #   m ffff8240 32     -> palette (16 big-endian words, $0RGB, 3 bits/gun)
  #   m f8000 32000     -> screen bytes  (use the real _v_bas_ad from `m 44e 4`)

  python tools/screendump.py --rez 2 --screen screen_hex.txt --out screen.png

--screen takes a file of whitespace-separated hex byte tokens (what `m` prints).
--palette is optional (ignored for rez 2 / mono).
"""
import argparse
import sys

MODES = {
    0: (320, 200, 4),   # low res, 16 colours, 4 planes
    1: (640, 200, 2),   # med res, 4 colours, 2 planes
    2: (640, 400, 1),   # high res, mono, 1 plane
}


def read_hex_bytes(path):
    text = sys.stdin.read() if path == "-" else open(path).read()
    toks = text.split()
    out = bytearray()
    for t in toks:
        try:
            out.append(int(t, 16))
        except ValueError:
            pass  # skip stray non-hex tokens (e.g. a leaked status line)
    return bytes(out)


def ste_colour(word):
    """$0RGB, 3 bits per gun on the STF (bit layout r2 r1 r0 in bits 10..8 etc.).
    The STE 4th (low) bit lives in bit 3 of each nibble; handle both by treating
    each gun as a 4-bit value with the STF's LSB-missing case scaled up."""
    r = (word >> 8) & 0xF
    g = (word >> 4) & 0xF
    b = word & 0xF
    # STF: 3 bits per gun (value 0..7), a near-linear DAC - so v*255/7 (7 -> full
    # 0xFF white, 0 -> black). STE adds a 4th, least-significant bit at nibble bit 3;
    # detect it by any gun exceeding 7 and treat the gun as a linear 4-bit value.
    if r > 7 or g > 7 or b > 7:
        return (r * 255 // 15, g * 255 // 15, b * 255 // 15)
    return (r * 255 // 7, g * 255 // 7, b * 255 // 7)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rez", type=int, required=True, choices=(0, 1, 2))
    ap.add_argument("--screen", required=True, help="file of hex byte tokens, or - for stdin")
    ap.add_argument("--palette", help="file of hex byte tokens (16 big-endian words)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=int, default=1)
    args = ap.parse_args()

    from PIL import Image

    w, h, planes = MODES[args.rez]
    data = read_hex_bytes(args.screen)
    need = w * h * planes // 8
    if len(data) < need:
        sys.exit(f"screen dump too short: got {len(data)} bytes, need {need}")

    if args.rez == 2:
        palette = [(255, 255, 255), (0, 0, 0)]
    else:
        pal_bytes = read_hex_bytes(args.palette) if args.palette else b""
        palette = []
        for i in range(1 << planes):
            if 2 * i + 1 < len(pal_bytes):
                word = (pal_bytes[2 * i] << 8) | pal_bytes[2 * i + 1]
            else:
                word = 0
            palette.append(ste_colour(word))

    img = Image.new("RGB", (w, h))
    px = img.load()
    row_bytes = w * planes // 8
    for y in range(h):
        base = y * row_bytes
        for x in range(w):
            word_idx = x // 16
            bit = 15 - (x % 16)
            idx = 0
            for p in range(planes):
                off = base + word_idx * 2 * planes + p * 2
                word = (data[off] << 8) | data[off + 1]
                idx |= ((word >> bit) & 1) << p
            px[x, y] = palette[idx]

    if args.scale > 1:
        img = img.resize((w * args.scale, h * args.scale), Image.NEAREST)
    img.save(args.out)
    print(f"wrote {args.out} ({img.size[0]}x{img.size[1]})")


if __name__ == "__main__":
    main()
