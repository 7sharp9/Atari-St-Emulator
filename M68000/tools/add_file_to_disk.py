#!/usr/bin/env python3
"""Inject a host file into an existing FAT12 .ST floppy image: a root-directory
(or \\AUTO\\) entry, a FAT cluster chain, and the cluster data. The companion to
make_blank_disk.py - that one produces an empty formatted image, this one puts a
program on it so TOS can actually load and run something.

Reads the image's own BPB rather than assuming a geometry, so it works for any
image make_blank_disk.py can produce. FAT12 only (every real ST floppy).

    python tools/add_file_to_disk.py blank_80ss.st TEST.PRG --auto --out disk_auto.st

--auto places the file in \\AUTO\\ (TOS runs \\AUTO\\*.PRG at boot with no user
interaction - the deterministic way to get a program running headless); without
it the file lands in the root directory.
"""
import argparse
import struct
import sys

SECSZ = 512


class Fat12:
    def __init__(self, image: bytes):
        d = bytearray(image)
        self.d = d
        self.bps = struct.unpack_from("<H", d, 11)[0]
        self.spc = d[13]
        self.res = struct.unpack_from("<H", d, 14)[0]
        self.nfat = d[16]
        self.ndir = struct.unpack_from("<H", d, 17)[0]
        self.spf = struct.unpack_from("<H", d, 22)[0]
        if self.bps != SECSZ:
            sys.exit(f"unexpected bytes/sector {self.bps}")
        self.clustersz = self.spc * self.bps
        self.fat_start = self.res
        self.dir_start = self.res + self.nfat * self.spf
        self.dir_sectors = (self.ndir * 32 + self.bps - 1) // self.bps
        self.data_start = self.dir_start + self.dir_sectors
        total = struct.unpack_from("<H", d, 19)[0]
        self.total_clusters = (total - self.data_start) // self.spc

    # --- FAT12 entry access (first FAT copy; mirrored to the rest on save) ---
    def get_fat(self, n: int) -> int:
        off = self.fat_start * self.bps + n * 3 // 2
        pair = self.d[off] | (self.d[off + 1] << 8)
        return pair & 0x0FFF if n % 2 == 0 else pair >> 4

    def set_fat(self, n: int, val: int):
        off = self.fat_start * self.bps + n * 3 // 2
        pair = self.d[off] | (self.d[off + 1] << 8)
        if n % 2 == 0:
            pair = (pair & 0xF000) | (val & 0x0FFF)
        else:
            pair = (pair & 0x000F) | ((val & 0x0FFF) << 4)
        self.d[off] = pair & 0xFF
        self.d[off + 1] = pair >> 8

    def alloc_chain(self, nbytes: int) -> list[int]:
        need = max(1, (nbytes + self.clustersz - 1) // self.clustersz)
        free = []
        for n in range(2, self.total_clusters + 2):
            if self.get_fat(n) == 0:
                free.append(n)
                if len(free) == need:
                    break
        if len(free) < need:
            sys.exit("not enough free clusters on the image")
        for i, c in enumerate(free):
            self.set_fat(c, 0xFFF if i == need - 1 else free[i + 1])
        return free

    def cluster_offset(self, n: int) -> int:
        return (self.data_start + (n - 2) * self.spc) * self.bps

    def write_clusters(self, chain: list[int], data: bytes):
        for i, c in enumerate(chain):
            seg = data[i * self.clustersz:(i + 1) * self.clustersz]
            off = self.cluster_offset(c)
            self.d[off:off + len(seg)] = seg

    def mirror_fats(self):
        fat1 = self.d[self.fat_start * self.bps: (self.fat_start + self.spf) * self.bps]
        for k in range(1, self.nfat):
            start = (self.fat_start + k * self.spf) * self.bps
            self.d[start:start + len(fat1)] = fat1

    # --- directory ---
    @staticmethod
    def dirent(name83: str, attr: int, cluster: int, size: int) -> bytes:
        if name83 in (".", ".."):
            raw = name83.ljust(11).encode("ascii")   # "." / ".." are literal, space-padded
        else:
            base, _, ext = name83.partition(".")
            raw = f"{base:<8}{ext:<3}".upper().encode("ascii")
        e = bytearray(32)
        e[0:11] = raw
        e[11] = attr
        struct.pack_into("<H", e, 22, 0)      # time
        struct.pack_into("<H", e, 24, 0x4021)  # date = 2012-01-01, arbitrary but valid
        struct.pack_into("<H", e, 26, cluster)
        struct.pack_into("<I", e, 28, size)
        return bytes(e)

    def root_slots(self):
        for i in range(self.ndir):
            off = self.dir_start * self.bps + i * 32
            if self.d[off] in (0x00, 0xE5):
                yield off

    def add_root_entry(self, ent: bytes):
        off = next(self.root_slots(), None)
        if off is None:
            sys.exit("root directory is full")
        self.d[off:off + 32] = ent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("image")
    p.add_argument("file")
    p.add_argument("--name", help="8.3 name on the disk (default: derived from file)")
    p.add_argument("--auto", action="store_true", help="place in \\AUTO\\ (TOS boot-runs it)")
    p.add_argument("--out", help="output image (default: overwrite input)")
    args = p.parse_args()

    payload = open(args.file, "rb").read()
    fs = Fat12(open(args.image, "rb").read())

    name = args.name
    if not name:
        import os
        name = os.path.basename(args.file).upper()

    prg_chain = fs.alloc_chain(len(payload))
    fs.write_clusters(prg_chain, payload)

    if args.auto:
        auto_cl = fs.alloc_chain(fs.clustersz)  # one cluster for the AUTO directory
        dirbuf = bytearray(fs.clustersz)
        dot = fs.dirent(".", 0x10, auto_cl[0], 0)
        dotdot = fs.dirent("..", 0x10, 0, 0)
        prg = fs.dirent(name, 0x20, prg_chain[0], len(payload))
        dirbuf[0:32] = dot
        dirbuf[32:64] = dotdot
        dirbuf[64:96] = prg
        fs.write_clusters(auto_cl, bytes(dirbuf))
        fs.add_root_entry(fs.dirent("AUTO", 0x10, auto_cl[0], 0))
        where = f"\\AUTO\\{name}"
    else:
        fs.add_root_entry(fs.dirent(name, 0x20, prg_chain[0], len(payload)))
        where = f"\\{name}"

    fs.mirror_fats()
    out = args.out or args.image
    open(out, "wb").write(fs.d)
    print(f"Wrote {out}: {where} = {len(payload)} bytes, "
          f"clusters {prg_chain}{' + AUTO dir ' + str(auto_cl) if args.auto else ''}")


if __name__ == "__main__":
    main()
