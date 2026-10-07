"""resource2_export.py - render every entry of the resource-manager's type-2 catalog (graphics.md
5f/5a) to a contact sheet + manifest, the same way tiles/contact_sheet.png proves the terrain
catalog and sprites/ proves the object array.

Resource type 2 (mechanics.md section 2's manager, `(A5)+96` -> 18-byte row * 2) is a 255-entry catalog
of wall-panel/building/item art, reached only through a dedicated fetch primitive at `$00c576`
(hardcoded `moveq #2,D0`, distinct from the generic `(type,index)` fetch `$00c5a8` that graphics.md
5a's original census grepped for - that's why the census concluded type 2 was dead when it's
actually the single most-called resource type in the program, 28+ call sites). `$00e872`/`$00cbf0`
(graphics.md 5f) is its main consumer: the terrain-grid's top-bit marker byte `0xc2` (gated
`D7 & 0x44 == 0x40`) selects an entry by `(marker & 0xf) - 1` and draws it through the same
`$00d1f8` placement routine as an ordinary tile, i.e. a decorative wall panel overlaid on top of
the flat 80-tile terrain catalog at a specific grid cell - not an "object anchor" as earlier passes
guessed before this one traced `$92e8`/`$c576` in full.

Each catalog entry is a self-contained resource: a 0x20-byte header (fields not yet decoded past
offset 0, all zero in every entry sampled so far), then a big-endian `w` word (width in 16px words)
and `h` word (height in rows) at +0x20/+0x22, then `w*16` x `h` pixels of standard ST-interleaved
4bpp planar data starting at +0x24. Confirmed against the live resource-manager table, not guessed:
`$00c576`'s own body decodes the index-table slot as one big-endian long, low 17 bits = byte offset
into the data area, high word (>>1) = entry byte size - matches `w*16*h/4` (planar row bytes) +
0x24 header exactly for every entry checked.

    python reversing/cadaver/py/resource2_export.py scratchpad/cadaver/gameplay_empire.snap \
        --out-dir reversing/cadaver/decor

Any snapshot works - like the terrain catalog (graphics.md 5d), this table is boot-time-loaded and
build-global, not per-room; re-resolve `(A5)+96`/`(A5)+16` fresh per snapshot rather than hardcoding
the addresses (build/relocation warning already documented in world_map.py's docstring).
"""
import argparse
import csv
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
from gfxview import load_ram, snapshot_regs  # noqa: E402
import sprite_array_export as sae  # noqa: E402

RESOURCE_MANAGER_OFFSET = 96
TYPE_RECORD_SIZE = 18
DECOR_TYPE = 2
HEADER_SIZE = 0x24  # 0x20-byte header + w,h words


def read_u16(ram, base, a):
    return int.from_bytes(ram[a - base:a - base + 2], "big")


def read_u32(ram, base, a):
    return struct.unpack(">I", ram[a - base:a - base + 4])[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("snap")
    ap.add_argument("--palette", default="0x5a9c")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    ram, base = load_ram(args.snap)
    regs, ok = snapshot_regs(args.snap)
    if not ok:
        raise SystemExit("snapshot has no saved registers")
    a5 = regs["a5"]

    resmgr = read_u32(ram, base, a5 + RESOURCE_MANAGER_OFFSET)
    rec = resmgr + DECOR_TYPE * TYPE_RECORD_SIZE
    index_table = read_u32(ram, base, rec)
    data_area = read_u32(ram, base, rec + 4)
    count = read_u16(ram, base, rec + 16)
    palette = sae.read_palette(ram, int(args.palette, 16))
    print(f"A5={a5:#x} resmgr={resmgr:#x} type2: index_table={index_table:#x} "
          f"data_area={data_area:#x} count={count}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    imgs = []
    for idx in range(count):
        slot_addr = index_table + idx * 4
        slot_long = read_u32(ram, base, slot_addr)
        offset = slot_long & 0x1ffff
        size = (slot_long >> 16) & 0xffff
        ptr = data_area + offset
        o = ptr - base
        w = int.from_bytes(ram[o + 0x20:o + 0x22], "big")
        h = int.from_bytes(ram[o + 0x22:o + 0x24], "big")
        if w == 0 or h == 0 or w > 20 or h > 400:
            print(f"idx={idx} skip implausible w={w} h={h} (slot={slot_long:#x})")
            continue
        img = sae.decode_st_interleaved(ram, o + HEADER_SIZE, w * 16, h, 4, palette).convert("RGB")
        fname = f"decor{idx:03d}_{ptr:x}_{w*16}x{h}.png"
        img.save(out_dir / fname)
        manifest.append({"index": idx, "addr": hex(ptr), "w": w * 16, "h": h, "size": size,
                          "file": fname})
        imgs.append(img)

    with open(out_dir / "manifest.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["index", "addr", "w", "h", "size", "file"])
        writer.writeheader()
        writer.writerows(manifest)

    sheet = sae.contact_sheet(imgs, ncols=16, scale=1)
    sheet.save(out_dir / "contact_sheet.png")
    print(f"wrote {len(imgs)} entries to {out_dir}, contact sheet {sheet.size}")


if __name__ == "__main__":
    main()
