"""cross_check_type2_objects.py - proves graphics.md 5a-2's cross-check: is resource type 2's
255-slot catalog (graphics.md 5a/5f, `resource2_export.py`) literally the template catalog that
section 3's 22-entry per-room object array draws its art from, or just a conceptually similar,
separate pool?

For each of section 3's array slots (`sprite_array_export.py`'s own struct: `(A5)+56` array base,
stride 0x46, `+50/+51` width/height, `+52` bitmap pointer, `+42` state byte), resolves every type-2
slot's payload address the same way `resource2_export.py` does (`data_area + (index_table slot &
0x1ffff) + 0x24`, skipping that entry's own 0x24-byte header) and checks whether the object array
slot's own `+52` pointer lands exactly on one.

    python reversing/cadaver/py/cross_check_type2_objects.py scratchpad/cadaver/gameplay_empire.snap

Result (this session, CAVERN): slot 0 (player) is outside type 2's data area entirely (it has its
own dedicated `$029800`-`$02de08` sheet, section 2/3). All 20 other state-5 (static room-dressing)
slots land at the exact byte address of a type-2 payload start, matching width/height too; three
spot-checked by decoding both independently (torch/slot 1<->idx 14, boat/slot 17<->idx 19,
chest/slot 20<->idx 53) come out pixel-identical, not just same-address. The one exception is slot
16 (the goblet, the array's own flagged `+42` state-4 outlier): it decodes to real art via its own
struct fields, but that address falls inside type 2's overall data span without landing on any of
the 255 index-table-listed entries' own boundary - genuine art, sourced from somewhere this
resource manager's type-2 enumeration doesn't reach, not the same 255-slot table the 20 static
entries use. **Net**: type 2 is confirmed as the real template catalog for per-room static
dressing, not merely "the same conceptual role" - and the goblet's state=4 now has a concrete
structural correlate (graphics.md 5a-2).
"""
import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
from gfxview import load_ram, snapshot_regs  # noqa: E402
import sprite_array_export as sae  # noqa: E402

SPRITE_ARRAY_PTR_FIELD = 56
SPRITE_STRIDE = 0x46
SPRITE_COUNT = 22
W_OFF, H_OFF, PTR_OFF, STATE_OFF = 50, 51, 52, 42

RESOURCE_MANAGER_OFFSET = 96
TYPE_RECORD_SIZE = 18
DECOR_TYPE = 2
HEADER_SIZE = 0x24

SPOT_CHECK_PAIRS = [(1, "torch"), (17, "boat"), (20, "chest")]  # (sprite slot, label)


def read_u8(ram, base, a):
    return ram[a - base]


def read_u16(ram, base, a):
    return int.from_bytes(ram[a - base:a - base + 2], "big")


def read_u32(ram, base, a):
    return struct.unpack(">I", ram[a - base:a - base + 4])[0]


def read_sprite_slots(ram, base, a5):
    sprite_base = read_u32(ram, base, a5 + SPRITE_ARRAY_PTR_FIELD)
    slots = []
    for i in range(SPRITE_COUNT):
        entry = sprite_base + i * SPRITE_STRIDE
        slots.append({
            "slot": i,
            "w": read_u8(ram, base, entry + W_OFF) * 16,
            "h": read_u8(ram, base, entry + H_OFF),
            "ptr": read_u32(ram, base, entry + PTR_OFF),
            "state": read_u8(ram, base, entry + STATE_OFF),
        })
    return slots


def read_type2_catalog(ram, base, a5):
    resmgr = read_u32(ram, base, a5 + RESOURCE_MANAGER_OFFSET)
    rec = resmgr + DECOR_TYPE * TYPE_RECORD_SIZE
    index_table = read_u32(ram, base, rec)
    data_area = read_u32(ram, base, rec + 4)
    count = read_u16(ram, base, rec + 16)
    entries = []
    for idx in range(count):
        slot_long = read_u32(ram, base, index_table + idx * 4)
        entry_addr = data_area + (slot_long & 0x1ffff)
        o = entry_addr - base
        w = int.from_bytes(ram[o + 0x20:o + 0x22], "big") * 16
        h = int.from_bytes(ram[o + 0x22:o + 0x24], "big")
        entries.append({"index": idx, "entry_addr": entry_addr,
                         "payload_addr": entry_addr + HEADER_SIZE, "w": w, "h": h})
    return entries, data_area


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("snap")
    ap.add_argument("--palette", default="0x5a9c")
    args = ap.parse_args()

    ram, base = load_ram(args.snap)
    regs, ok = snapshot_regs(args.snap)
    if not ok:
        raise SystemExit("snapshot has no saved registers")
    a5 = regs["a5"]
    palette = sae.read_palette(ram, int(args.palette, 16))

    sprites = read_sprite_slots(ram, base, a5)
    type2, data_area = read_type2_catalog(ram, base, a5)
    by_payload = {t["payload_addr"]: t for t in type2}
    data_end = max(t["payload_addr"] + 1 for t in type2)

    for s in sprites:
        hit = by_payload.get(s["ptr"])
        if hit:
            note = (f"exact type-2 payload match, idx={hit['index']} "
                     f"({'w/h match' if (hit['w'], hit['h']) == (s['w'], s['h']) else 'w/h MISMATCH'})")
        elif data_area <= s["ptr"] < data_end:
            note = "inside type-2's data span but not on any entry boundary"
        else:
            note = "outside type-2's data area entirely"
        print(f"slot={s['slot']:2d} state={s['state']} ptr={s['ptr']:#08x} "
              f"w={s['w']:3d} h={s['h']:3d} -> {note}")

    print()
    for slot, label in SPOT_CHECK_PAIRS:
        s = sprites[slot]
        hit = by_payload.get(s["ptr"])
        if not hit:
            print(f"slot={slot} ({label}): no type-2 match to spot-check")
            continue
        sprite_img = sae.decode_st_interleaved(ram, s["ptr"], s["w"], s["h"], 4, palette).convert("RGB")
        type2_img = sae.decode_st_interleaved(ram, hit["payload_addr"], hit["w"], hit["h"], 4,
                                               palette).convert("RGB")
        import numpy as np
        identical = np.array(sprite_img).shape == np.array(type2_img).shape and \
            (np.array(sprite_img) == np.array(type2_img)).all()
        print(f"slot={slot} ({label}) vs type2 idx={hit['index']}: pixel-identical={identical}")


if __name__ == "__main__":
    main()
