#!/usr/bin/env python3
"""Create a blank, valid .ST floppy image: real BPB, formatted FAT12 + empty
root directory, but no files (so no \\AUTO\\*.PRG can ever be found) - the
"valid disk, no AUTO program" milestone image described in
atari-st-emulator-next-instructions memory.

Byte layout ported directly from Hatari's own src/createBlankImage.c
(CreateBlankImage_CreateFile) - not guessed - so the produced image matches
what a real Atari FDC/BPB implementation expects. Defaults to 80 tracks,
9 sectors/track, 1 side (360KB, single-sided) specifically to avoid needing
any PSG/side-select emulation for this milestone: every sector - boot,
both FAT copies, and the root directory - lives on side 0, track 0-7.
"""
import argparse
import random
import struct

NUMBYTESPERSECTOR = 512


def create_blank_image(tracks: int, sectors: int, sides: int) -> bytes:
    if sectors >= 18:
        sides = 2  # HD/ED disks are always double-sided (Hatari's own rule)

    disk_size = tracks * sectors * sides * NUMBYTESPERSECTOR
    disk = bytearray(disk_size)

    disk[0] = 0xE9  # MS-DOS compatibility byte
    disk[2:8] = b"\x4e" * 6  # 'Loader' filler

    struct.pack_into("<H", disk, 8, random.randint(0, 0xFFFF))  # serial number
    disk[10] = random.randint(0, 0xFF)

    struct.pack_into("<H", disk, 11, NUMBYTESPERSECTOR)  # BPS

    spc = 1 if (tracks == 40 and sides == 1) else 2
    disk[13] = spc

    struct.pack_into("<H", disk, 14, 1)  # RES: reserved sectors
    disk[16] = 2  # FAT: number of FAT copies

    if spc == 1:
        n_dir = 64
    elif sectors < 18:
        n_dir = 112
    else:
        n_dir = 224
    struct.pack_into("<H", disk, 17, n_dir)  # DIR: root dir entries

    struct.pack_into("<H", disk, 19, tracks * sectors * sides)  # SEC: total sectors

    if sectors >= 18:
        media = 0xF0
    else:
        media = 0xFC if tracks <= 42 else 0xF8
        if sides == 2:
            media |= 0x01
    disk[21] = media

    if sectors >= 18:
        spf = 9
    elif tracks >= 80:
        spf = 5
    else:
        spf = 2
    struct.pack_into("<H", disk, 22, spf)  # SPF: sectors per FAT

    struct.pack_into("<H", disk, 24, sectors)  # SPT: sectors per track
    struct.pack_into("<H", disk, 26, sides)  # SIDE: number of sides
    struct.pack_into("<H", disk, 28, 0)  # HID: hidden sectors

    # Media byte + 2 reserved 0xFF FAT-ID bytes at the start of each FAT copy.
    disk[512] = media
    disk[513] = disk[514] = 0xFF
    disk[512 + spf * 512] = media
    disk[513 + spf * 512] = disk[514 + spf * 512] = 0xFF

    return bytes(disk)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("out", nargs="?", default="blank_80ss.st")
    p.add_argument("--tracks", type=int, default=80)
    p.add_argument("--sectors", type=int, default=9)
    p.add_argument("--sides", type=int, default=1)
    p.add_argument("--seed", type=int, default=1, help="deterministic serial number")
    args = p.parse_args()

    random.seed(args.seed)
    image = create_blank_image(args.tracks, args.sectors, args.sides)
    with open(args.out, "wb") as f:
        f.write(image)
    print(f"Wrote {args.out}: {len(image)} bytes "
          f"({args.tracks} tracks x {args.sectors} sectors x {args.sides} side(s))")
