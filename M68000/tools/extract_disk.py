"""extract_disk.py - dump every file of a FAT12 .ST image (recursing into directories).

    python tools/extract_disk.py "<image.st>" <outdir>

Working data goes under scratchpad, never the repo: the game files are commercial.
"""
import os
import struct
import sys


def main(img_path, out):
    d = open(img_path, "rb").read()
    bps = struct.unpack_from("<H", d, 0x0B)[0]
    spc = d[0x0D]
    rsv = struct.unpack_from("<H", d, 0x0E)[0]
    nfat = d[0x10]
    nroot = struct.unpack_from("<H", d, 0x11)[0]
    spf = struct.unpack_from("<H", d, 0x16)[0]
    fat = d[rsv * bps:(rsv + spf) * bps]
    root = (rsv + nfat * spf) * bps
    data0 = root + nroot * 32
    cl = bps * spc

    def nxt(c):
        o = c * 3 // 2
        v = fat[o] | (fat[o + 1] << 8)
        return (v >> 4) if c & 1 else (v & 0xFFF)

    def chain(c, size=None):
        b = bytearray()
        while 2 <= c < 0xFF8:
            o = data0 + (c - 2) * cl
            b += d[o:o + cl]
            c = nxt(c)
        return bytes(b if size is None else b[:size])

    def walk(raw, path):
        for i in range(0, len(raw), 32):
            e = raw[i:i + 32]
            if e[0] == 0:
                break
            if e[0] == 0xE5 or e[11] & 0x08 or e[0] == 0x2E:
                continue
            name = e[:8].decode("ascii", "replace").strip()
            ext = e[8:11].decode("ascii", "replace").strip()
            fn = name + ("." + ext if ext else "")
            c = struct.unpack_from("<H", e, 26)[0]
            size = struct.unpack_from("<I", e, 28)[0]
            if e[11] & 0x10:
                walk(chain(c), os.path.join(path, fn))
            else:
                os.makedirs(path, exist_ok=True)
                with open(os.path.join(path, fn), "wb") as f:
                    f.write(chain(c, size))
                print(f"{os.path.join(path, fn)}  {size}")

    walk(d[root:root + nroot * 32], out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
