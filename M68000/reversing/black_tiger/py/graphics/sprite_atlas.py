"""sprite_atlas.py - atlases of every BTSPR bank (all contiguous frame slots from the data extent)
and the BTMAN hero bank.  Extent comes from the data: a bank's frame area runs from its first
referenced frame to the next bank start (or file end); slots are H*bytes-per-row*pieces long."""
import os

from bt_common import *  # noqa
from sprites import *  # noqa


def bank_extent(buf, base, end):
    b = parse_bank(buf, base)
    code = max((a["code"] for a in b["anims"]), key=lambda c: piece_bytes(c, b["H"]))
    slot = piece_bytes(code, b["H"])
    refs = sorted(set(f for a in b["anims"] for f in a["frames"]))
    first = refs[0]
    n = (end - base - first) // slot
    rem = (end - base - first) - n * slot
    return b, code, slot, first, n, rem, refs


def main():
    t0 = read_file("T0")
    pal = pal_from_bytes(t0, 0)
    spr = read_file("BTSPR")
    offs = [l32(spr, 4 * i) for i in range(17)]
    ends = sorted(set(offs + [len(spr)]))
    report = []
    for i, o in enumerate(offs):
        if i > 0 and o == offs[i - 1]:
            continue
        end = min(e for e in ends if e > o)
        b, code, slot, first, n, rem, refs = bank_extent(spr, o, end)
        frames = []
        for k in range(n):
            off = first + k * slot
            frames.append((0, k, off, code, decode_frame(spr, o + off, code, b["H"])))
        unref = [k for k in range(n) if first + k * slot not in refs]
        im = sheet_image(frames, pal, cols=8, scale=2)
        name = "spr_BTSPR_bank%02d.png" % (i + 1)
        im.save(os.path.join(PNG, name))
        report.append("bank %2d at BTSPR+$%05x end $%05x H=%2d code=%d slots=%2d (referenced %2d, unreferenced slots %s, trailing bytes %d)" %
                      (i + 1, o, end, b["H"], code, n, len(refs), unref, rem))
    # hero
    man = read_file("BTMAN")
    b, code, slot, first, n, rem, refs = bank_extent(man, 0, len(man))
    frames = [(0, k, first + k * slot, code, decode_frame(man, first + k * slot, code, b["H"])) for k in range(n)]
    sheet_image(frames, pal, cols=8, scale=2).save(os.path.join(PNG, "spr_BTMAN_hero.png"))
    report.append("BTMAN: H=%d code=%d slots=%d first $%x trailing %d" % (b["H"], code, n, first, rem))
    print("\n".join(report))
    open(os.path.join(OUT, "sprite_banks.txt"), "w").write("\n".join(report) + "\n")


if __name__ == "__main__":
    main()
