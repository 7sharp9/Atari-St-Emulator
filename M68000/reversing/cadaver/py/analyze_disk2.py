"""agent_disk2_analysis: characterize Disk 2's real (non-blank) data runs more precisely than
disk_layout.py's coarse blank/data split -- entropy per run, fixed-stride periodicity search,
embedded ASCII string scan, and a structural comparison against Disk 1 / the one-disk release.

Read-only, no emulator. Reuses disk_layout.py's run-detection logic.
"""
import math
import re
import sys
from collections import Counter

sys.path.insert(0, "/Users/davethomas/GitHub/Atari-St-Emulator/M68000/reversing/cadaver/py")
from disk_layout import parse_bpb, root_dir_files, data_blank_runs  # noqa: E402

DISK1 = "/Users/davethomas/GitHub/Atari-St-Emulator/Cadaver/disk1_empire/Cadaver (1990)(Image Works)(M3)(Disk 1 of 2)[cr Empire][t].st"
DISK2 = "/Users/davethomas/GitHub/Atari-St-Emulator/Cadaver/disk2_empire/Cadaver (1990)(Image Works)(M3)(Disk 2 of 2)(Level)[cr Empire][t].st"
ONEDISK = "/Users/davethomas/GitHub/Atari-St-Emulator/Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st"


def entropy(buf):
    if not buf:
        return 0.0
    c = Counter(buf)
    n = len(buf)
    return -sum((v / n) * math.log2(v / n) for v in c.values())


def best_stride_score(buf, strides=(2, 4, 6, 8, 10, 12, 16, 20, 24, 32, 64)):
    """For each candidate record stride, measure how often byte[i] == byte[i+stride]
    compared to a random baseline (~1/256), as a crude periodicity signal."""
    results = []
    for s in strides:
        if len(buf) < s * 4:
            continue
        matches = 0
        total = 0
        for i in range(0, len(buf) - s, s):
            if buf[i] == buf[i + s]:
                matches += 1
            total += 1
        if total:
            results.append((s, matches / total))
    return results


def ascii_strings(buf, min_len=4):
    pattern = re.compile(rb"[\x20-\x7e]{%d,}" % min_len)
    return [m.group().decode("ascii") for m in pattern.finditer(buf)]


def analyze(path, label):
    with open(path, "rb") as f:
        data = f.read()
    boot = data[:512]
    bpb = parse_bpb(boot)
    runs = data_blank_runs(data)
    data_runs = [(s, e) for s, e, blank in runs if not blank]

    print(f"\n{'=' * 70}\n{label}: {path}\n{'=' * 70}")
    print(f"size {len(data)} bytes, {len(data_runs)} non-blank sector runs")

    total_data_bytes = 0
    strings_found = []
    for s, e in data_runs:
        off_lo, off_hi = s * 512, (e + 1) * 512
        buf = data[off_lo:off_hi]
        total_data_bytes += len(buf)
        ent = entropy(buf)
        strides = best_stride_score(buf)
        top_strides = sorted(strides, key=lambda t: -t[1])[:3]
        strs = ascii_strings(buf)
        strings_found.extend((off_lo + m.start(), m.group().decode()) for m in
                              re.finditer(rb"[\x20-\x7e]{4,}", buf))
        print(f"  run sectors {s:4d}-{e:4d} ({e - s + 1:4d} sec, {len(buf):7d} B) "
              f"offset {off_lo:#07x}-{off_hi:#07x}  entropy={ent:.3f} b/B  "
              f"top strides(len,match%)={[(l, f'{p*100:.1f}%') for l, p in top_strides]}")

    print(f"\n  total real data: {total_data_bytes} bytes "
          f"({100 * total_data_bytes / len(data):.1f}%)")

    print(f"\n  ascii strings len>=4 found in data runs ({len(strings_found)} total):")
    for off, s in strings_found[:60]:
        print(f"    {off:#07x}: {s!r}")
    if len(strings_found) > 60:
        print(f"    ... {len(strings_found) - 60} more")

    return data, data_runs, strings_found


def compare_identical_fraction(a, b, label):
    n = min(len(a), len(b))
    same = sum(1 for i in range(0, n, 4) if a[i:i+4] == b[i:i+4]) # sampled every 4 bytes, 4-byte compare
    total = len(range(0, n, 4))
    print(f"\n{label}: sampled 4-byte-aligned identical fraction "
          f"{same}/{total} = {100*same/total:.1f}%")


def main():
    d1, d1_runs, _ = analyze(DISK1, "Disk 1 (Level)")
    d2, d2_runs, d2_strings = analyze(DISK2, "Disk 2 (Level)")
    d0, d0_runs, _ = analyze(ONEDISK, "One-disk release")

    compare_identical_fraction(d1, d2, "Disk1 vs Disk2")
    compare_identical_fraction(d1, d0, "Disk1 vs one-disk")
    compare_identical_fraction(d2, d0, "Disk2 vs one-disk")

    print("\nDisk2 run-size histogram (sector counts):")
    sizes = sorted((e - s + 1) for s, e in d2_runs)
    print(" ", sizes)


if __name__ == "__main__":
    main()
