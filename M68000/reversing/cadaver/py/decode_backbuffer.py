"""decode_backbuffer.py - decode Cadaver's 120(A5) resident buffer into a normal
320x200x4bpp st-interleaved raster.

`$0144b8` (ScreenFlip_ScanlineCopy) copies this buffer to the visible double-buffer using
`movem.l (A0)+,#$fcff` / `movem.l #$ff3f,-(A1)` pairs: 14 registers (D0-D7,A2-A7) read forward
from the source, written with predecrement into the destination. Predecrement mode processes
registers in the reverse order of postincrement mode for the same mask, so each 56-byte chunk's
*internal* byte order is preserved, but chunk order across the whole 32000-byte transfer is
reversed end-to-end (first chunk read lands at the highest destination address, last chunk read
lands at the lowest). A one-off 24-byte chunk (mask 0x003f/0xfc00, D0-D5) runs either before all
571 of the 56-byte chunks (if `$5a99` is nonzero at entry) or after all of them (if `$5a99` is
zero) - exactly one of the two, gated by `tst.b $5a99.l`.

Verified byte-exact against a live snapshot (mechanics.md 34th/35th pass): decoding
`120(A5)`'s buffer this way reproduces `(A5)+0`'s displayed frame with 0/32000 byte diffs.

    python reversing/cadaver/py/decode_backbuffer.py <snap> [--out out.png]

Reads `120(A5)` and `$5a99` live from the snapshot (both are per-snapshot, not fixed).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
from gfxview import load_ram, ste_colour  # noqa: E402

CHUNK = 56
NCHUNKS = 571
TAIL = 24
FRAME_BYTES = NCHUNKS * CHUNK + TAIL  # 32000 = one 320x200x4bpp frame
A5_120_OFF = 0x18152 + 120  # fallback only; real value is read from (A5) below when --a5 given


def read_long(ram, addr, base):
    o = addr - base
    return int.from_bytes(ram[o:o + 4], "big")


def read_byte(ram, addr, base):
    return ram[addr - base]


def decode_backbuffer(ram, base, buf_addr, flag_5a99):
    off = buf_addr - base
    buf = bytes(ram[off:off + FRAME_BYTES])
    chunks = [buf[i * CHUNK:(i + 1) * CHUNK] for i in range(NCHUNKS)]
    tail = buf[NCHUNKS * CHUNK:NCHUNKS * CHUNK + TAIL]
    if flag_5a99 != 0:
        # leading tail chunk: read first -> lands at the highest dest address (end of output)
        return b"".join(reversed(chunks)) + tail
    # trailing tail chunk: read last -> lands at the lowest dest address (start of output)
    return tail + b"".join(reversed(chunks))


def decode_st_interleaved(buf, width=320, height=200, bpp=4):
    import numpy as np

    row_bytes = width // 16 * 2 * bpp
    a = np.frombuffer(buf[:row_bytes * height], np.uint8).reshape(height, row_bytes)
    idx = np.zeros((height, width), np.uint8)
    for x in range(width):
        wg, bit = x // 16, 15 - (x % 16)
        val = np.zeros(height, np.uint8)
        for p in range(bpp):
            o = wg * bpp * 2 + p * 2
            word = (a[:, o].astype(np.uint16) << 8) | a[:, o + 1]
            val |= (((word >> bit) & 1) << p).astype(np.uint8)
        idx[:, x] = val
    return idx


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("snap")
    ap.add_argument("--a5", help="A5 base (hex); default: read live from the snapshot's saved A5")
    ap.add_argument("--palette", default="0x5a9c", help="palette address (hex)")
    ap.add_argument("--out", help="write decoded PNG here")
    args = ap.parse_args()

    ram, base = load_ram(args.snap)

    if args.a5:
        a5 = int(args.a5, 16)
    else:
        from gfxview import snapshot_regs
        regs, ok = snapshot_regs(args.snap)
        if not ok:
            raise SystemExit("snapshot has no saved registers; pass --a5 explicitly")
        a5 = regs["a5"]

    buf_addr = read_long(ram, a5 + 120, base)
    flag = read_byte(ram, 0x5a99, base)
    print(f"A5={a5:#x}  120(A5)={buf_addr:#x}  $5a99={flag}")

    raw = decode_backbuffer(ram, base, buf_addr, flag)

    if args.out:
        from PIL import Image
        pal_addr = int(args.palette, 16)
        palette = [int.from_bytes(ram[pal_addr - base + k * 2:pal_addr - base + k * 2 + 2], "big")
                   for k in range(16)]
        colors = [ste_colour(w) for w in palette]
        idx = decode_st_interleaved(raw)
        import numpy as np
        rgb = np.zeros((*idx.shape, 3), np.uint8)
        for i, c in enumerate(colors):
            rgb[idx == i] = c
        Image.fromarray(rgb, "RGB").save(args.out)
        print("wrote", args.out)


if __name__ == "__main__":
    main()
