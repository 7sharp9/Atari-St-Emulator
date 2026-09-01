"""Turn a directory of ATARI_FRAME_DIR frame dumps into a video.

The emulator's headless frame recorder (ATARI_FRAME_DIR=<dir>, see Program.fs)
writes one fNNNNNN.bin per captured VBL:  [rez:1][palette:32][screen:32000].
This decodes each with the same planar logic as screendump.py, writes PNGs, and
(unless --no-video) runs ffmpeg to stitch them into an mp4.

  ATARI_FRAME_DIR=frames ATARI_FRAME_EVERY=2 \
    dotnet exec bin/Debug/net8.0/M68000.dll <n> --disk-a "Super Sprint.ST"
  python tools/frames_to_video.py frames --out race.mp4 --fps 25 --scale 3
"""
import argparse
import glob
import os
import subprocess
import sys

MODES = {0: (320, 200, 4), 1: (640, 200, 2), 2: (640, 400, 1)}


def ste_colour(word):
    r, g, b = (word >> 8) & 0xF, (word >> 4) & 0xF, word & 0xF
    if r > 7 or g > 7 or b > 7:
        return (r * 255 // 15, g * 255 // 15, b * 255 // 15)
    return (r * 255 // 7, g * 255 // 7, b * 255 // 7)


def decode(blob, Image):
    rez = blob[0] & 3
    w, h, planes = MODES[rez]
    pal_bytes = blob[1:33]
    screen = blob[33:33 + w * h * planes // 8]
    if rez == 2:
        palette = [(255, 255, 255), (0, 0, 0)]
    else:
        palette = [ste_colour((pal_bytes[2 * i] << 8) | pal_bytes[2 * i + 1])
                   for i in range(1 << planes)]
    img = Image.new("RGB", (w, h))
    px = img.load()
    row_bytes = w * planes // 8
    for y in range(h):
        base = y * row_bytes
        for x in range(w):
            word_idx, bit = x // 16, 15 - (x % 16)
            idx = 0
            for p in range(planes):
                off = base + word_idx * 2 * planes + p * 2
                idx |= (((screen[off] << 8) | screen[off + 1]) >> bit & 1) << p
            px[x, y] = palette[idx]
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", help="directory of fNNNNNN.bin frame dumps")
    ap.add_argument("--out", default="frames.mp4")
    ap.add_argument("--fps", type=int, default=25)
    ap.add_argument("--scale", type=int, default=3)
    ap.add_argument("--no-video", action="store_true", help="just write PNGs")
    args = ap.parse_args()

    from PIL import Image

    blobs = sorted(glob.glob(os.path.join(args.dir, "f*.bin")))
    if not blobs:
        sys.exit(f"no f*.bin frames in {args.dir}")
    png_dir = os.path.join(args.dir, "png")
    os.makedirs(png_dir, exist_ok=True)
    for i, path in enumerate(blobs):
        img = decode(open(path, "rb").read(), Image)
        if args.scale > 1:
            img = img.resize((img.width * args.scale, img.height * args.scale), Image.NEAREST)
        img.save(os.path.join(png_dir, f"{i:06d}.png"))
    print(f"decoded {len(blobs)} frames -> {png_dir}")

    if args.no_video:
        return
    cmd = ["ffmpeg", "-y", "-framerate", str(args.fps),
           "-i", os.path.join(png_dir, "%06d.png"),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", args.out]
    subprocess.run(cmd, check=True)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
