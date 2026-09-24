"""disk_layout.py - data-only inspection of the one-disk Empire crack's raw .st image, to check
Open item 1 (cadaver.md, 50th-pass handoff): does the disk hold more than the 72-room map already
decoded (a second level), independent of the loaded-image caller search §48c/§48d/§50 already ran.

Two checks, no emulator stepping needed:

1. Root directory: is this actually a FAT12 volume with listable files, or a non-filesystem
   self-booting disk (like the Medway Boys compilation's Disk B, README "Disk images")? The boot
   sector's BPB fields parse as a plausible FAT12 superblock, but the root directory is all 0xE5
   ("deleted entry") bytes -- there is no real file table, so a level pack can't be sitting there
   as a second named file; whatever exists must be read by absolute sector number from the boot
   loader's own code, like Disk B.

2. Data/blank sector layout: which 512-byte sectors are real data vs. uniform filler (blank/erase
   pattern), to see whether the disk is packed near-full (consistent with more content than one
   level) or has one contiguous real-data region with the rest padding (consistent with a single
   level plus normal crack-disk slack).

    python reversing/cadaver/py/disk_layout.py "<path to the .st image>"
"""
import struct
import sys


def parse_bpb(boot):
    return {
        "bytes_per_sector": struct.unpack_from("<H", boot, 0x0b)[0],
        "sectors_per_cluster": boot[0x0d],
        "reserved_sectors": struct.unpack_from("<H", boot, 0x0e)[0],
        "num_fats": boot[0x10],
        "root_entries": struct.unpack_from("<H", boot, 0x11)[0],
        "total_sectors": struct.unpack_from("<H", boot, 0x13)[0],
        "media": boot[0x15],
        "sectors_per_fat": struct.unpack_from("<H", boot, 0x16)[0],
        "sectors_per_track": struct.unpack_from("<H", boot, 0x18)[0],
        "sides": struct.unpack_from("<H", boot, 0x1a)[0],
    }


def root_dir_files(data, bpb):
    fat_start = bpb["reserved_sectors"] * bpb["bytes_per_sector"]
    root_start = fat_start + bpb["num_fats"] * bpb["sectors_per_fat"] * bpb["bytes_per_sector"]
    root_size = bpb["root_entries"] * 32
    root = data[root_start:root_start + root_size]
    files = []
    for i in range(0, len(root), 32):
        e = root[i:i + 32]
        if e[0] == 0x00:
            break
        if e[0] == 0xE5:
            continue
        name = e[0:8].decode("ascii", "replace").strip()
        ext = e[8:11].decode("ascii", "replace").strip()
        size = struct.unpack_from("<I", e, 28)[0]
        files.append((f"{name}.{ext}", size))
    return files, root_start, root_size


def data_blank_runs(data, sector_size=512):
    n = len(data) // sector_size
    is_blank = [len(set(data[i * sector_size:(i + 1) * sector_size])) <= 1 for i in range(n)]
    runs = []
    cur, start = is_blank[0], 0
    for i in range(1, n):
        if is_blank[i] != cur:
            runs.append((start, i - 1, cur))
            start, cur = i, is_blank[i]
    runs.append((start, n - 1, cur))
    return runs


def main():
    path = sys.argv[1]
    with open(path, "rb") as f:
        data = f.read()
    boot = data[:512]
    bpb = parse_bpb(boot)
    print(f"image size {len(data)} bytes ({len(data) // 512} sectors)")
    print("BPB:", bpb)

    files, root_start, root_size = root_dir_files(data, bpb)
    print(f"\nroot dir @ {root_start:#x} ({root_size} bytes, {bpb['root_entries']} entries):")
    if files:
        for name, size in files:
            print(f"  {name} {size} bytes")
    else:
        print(f"  no real entries -- raw bytes: {data[root_start:root_start + 16].hex()}"
              " (non-filesystem, self-booting disk; data is read by absolute sector, not by name)")

    runs = data_blank_runs(data)
    print("\ndata/blank sector runs:")
    total_data = 0
    for s, e, blank in runs:
        length = e - s + 1
        kind = "blank" if blank else "data "
        if not blank:
            total_data += length * 512
        print(f"  {kind} sectors {s:4d}-{e:4d} ({length:4d} sectors, {length * 512:6d} bytes)"
              f"  offset {s * 512:#x}-{(e + 1) * 512:#x}")
    print(f"\ntotal real (non-blank) data: {total_data} bytes of {len(data)} "
          f"({100 * total_data / len(data):.1f}%)")


if __name__ == "__main__":
    main()
