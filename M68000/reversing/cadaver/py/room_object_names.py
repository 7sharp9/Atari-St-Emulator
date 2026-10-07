"""room_object_names.py - for the CURRENTLY LOADED room only, resolve every placed object's own
live display-name index and decode it to real text, closing cadaver.md open item 1's missing link.

72nd pass. The field is NOT in the type-6 template (mechanics.md section 8's own read of the raw
template bytes found no match for the lever's known index 200 anywhere in the record) - it is a
separate, room-load-populated "live instance" record, reached by the exact chain disassembled at
$009440 (mechanics.md section 6, the icon-panel/status-bar proximity check):

    template = resolve(type=6, id)          # sec65a/door_id_words.py's read_type6
    slot_off = u16(template + 8)            # the object's own currently-assigned array-slot byte
                                             # offset, written by the room loader ($00ce5c-$00ce60,
                                             # mechanics.md section 5) at room-entry time - only valid
                                             # while this object is instantiated in the CURRENT room
    slot_addr = u32((A5)+56) + slot_off      # SpriteObjectArrayPtr_A5Plus56 + slot_off (sec21a/43)
    live_rec = u32(slot_addr + 6)            # NOT the room-record back-pointer sec37d's prose
                                             # claimed ($00ce78's `move.l A0,6(A1)` is only this
                                             # field's transient room-load value; by the time any
                                             # steady-state snapshot exists it has already been
                                             # overwritten to point at a genuinely different, richer
                                             # per-object record - the writer is still unidentified,
                                             # see the module docstring's own open item below)
    name_index = u16(live_rec + 10)          # matches name_strings.py's table exactly

Verified byte-for-byte against room2_tunnel_entry.snap in its pristine, never-stepped state (no
emulator run needed - this is a pure static read): id 144 (LEVER) decodes to index 200, matching
mechanics.md section 8's already-proven live name exactly. Live `bpc 946a`/register capture during a
real Left-hold approach (this pass) confirms the same chain executes for real at
`$00944e`-`$00947c` (`move.w 10(A4),D0; cmp.w 1222(A5),D0`) with identical addresses.

**Still open**: who writes `slot_addr+6` after the room loader's own initial (and evidently
superseded) write, and whether `live_rec`'s underlying array is itself resident for every room
simultaneously (making a name census of all 72 rooms possible from one snapshot) or is rebuilt
per-room like the 70-byte placement array itself (mechanics.md section 6) - not yet determined. This
script only resolves objects belonging to the room actually loaded in the given snapshot.

    python reversing/cadaver/py/room_object_names.py <snap>
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gfxview import load_ram, snapshot_regs  # noqa: E402
from room_object_census import resource_type, resolve  # noqa: E402
from name_strings import decode_index  # noqa: E402

ARRAY_BASE_OFFSET = 56  # SpriteObjectArrayPtr_A5Plus56, mechanics.md sections 3 and 6


def u32(ram, base, addr):
    return struct.unpack(">I", ram[addr - base:addr - base + 4])[0]


def u16(ram, base, addr):
    return struct.unpack(">H", ram[addr - base:addr - base + 2])[0]


def main():
    snap = sys.argv[1]
    ram, base = load_ram(snap)
    regs, _ = snapshot_regs(snap)
    a5 = regs["a5"]

    room_idx, room_dat, room_cnt = resource_type(ram, base, a5, 3)
    obj_idx, obj_dat, obj_cnt = resource_type(ram, base, a5, 5)
    type6_idx, type6_dat, _ = resource_type(ram, base, a5, 6)

    slot = u16(ram, base, a5 + 1166)
    rec = resolve(ram, base, room_idx, room_dat, slot)
    objcount = ram[rec - base + 29]
    stream = resolve(ram, base, obj_idx, obj_dat, slot)
    ids = [u16(ram, base, stream + 2 * i) for i in range(objcount + 1)]

    array_base = u32(ram, base, a5 + ARRAY_BASE_OFFSET)
    t168 = u32(ram, base, a5 + 168)
    t172 = u32(ram, base, a5 + 172)

    print(f"room slot {slot}: {len(ids)} objects")
    for oid in ids:
        tmpl = resolve(ram, base, type6_idx, type6_dat, oid)
        if tmpl is None:
            print(f"  id {oid:4d}: no type-6 template")
            continue
        slot_off = u16(ram, base, tmpl + 8)
        slot_addr = array_base + slot_off
        live_rec = u32(ram, base, slot_addr + 6)
        name_idx = u16(ram, base, live_rec + 10) if live_rec else None
        name = decode_index(ram, base, t168, t172, name_idx) if name_idx not in (None, 0xFFFF) else b"<none>"
        print(f"  id {oid:4d}: slot_off={slot_off:#06x} live_rec={live_rec:#08x} "
              f"name_idx={name_idx} name={name!r}")


if __name__ == "__main__":
    main()
