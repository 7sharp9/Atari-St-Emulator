"""room_object_census.py - for every populated room in the type-3 table (world_map.py's own 72
slots), statically read that room's own object-id list and print it, without ever driving the
player there.

Found this pass by disassembling the room-load routine (`$00cd50`, mechanics.md sec37d) in full:
it resolves the room's object list via `bsr $c5a8` with **type 5**, index = the room's own slot
number (confirmed live: `(A5)+1166` reads 0 in gameplay_empire.snap/CAVERN and 1 in
room2_tunnel_entry.snap/TUNNEL, exactly world_map.py's own slot numbering) - a resource type this
spike had never resolved before (types 3/6/8/9 were already known, sec23c/38a). The stream is
`(room_record+29)+1` big-endian 16-bit words, each one a **type 6** object id to instantiate.

Cross-checked against already-proven ground truth: slot 0 (CAVERN) decodes to 22 objects matching
graphics.md's own 22-entry sprite-object-array export, and slot 1 (TUNNEL) decodes to exactly
`[0, 144]` - id 144 is the already-triple-confirmed lever object (mechanics.md sec23d). Both
match, 2/2 - this is a real resource type, not a guess.

**Does not, on its own, identify which room has a creature.** An object's own display-name index
(the string table `name_strings.py` decodes) is a separate numbering space from its type-6 id -
proven distinct by the lever itself (id 144, name index 200) - so a room's object id merely
matching a name-string index number (e.g. slot 27 containing id 226, the same number as
name_strings.py's "GIANT RAT" entry) is very likely coincidence, not a real reference, until the
type-6 record's own name-index field is found and read directly. That field is still the open
item (mechanics.md's own standing "proximity-icon writer... unidentified" note).

    python reversing/cadaver/py/room_object_census.py <snap>
"""
import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
from gfxview import load_ram, snapshot_regs  # noqa: E402

RESOURCE_MANAGER_OFFSET = 96
TYPE_RECORD_SIZE = 18
ROOM_TYPE = 3
OBJLIST_TYPE = 5
SLOT_COUNT = 100


def u32(ram, base, addr):
    o = addr - base
    return struct.unpack(">I", ram[o:o + 4])[0]


def u16(ram, base, addr):
    o = addr - base
    return struct.unpack(">H", ram[o:o + 2])[0]


def u8(ram, base, addr):
    return ram[addr - base]


def resource_type(ram, base, a5, type_id):
    resmgr = u32(ram, base, a5 + RESOURCE_MANAGER_OFFSET)
    rec = resmgr + type_id * TYPE_RECORD_SIZE
    return u32(ram, base, rec), u32(ram, base, rec + 4), u16(ram, base, rec + 16)


def resolve(ram, base, idx_ptr, data_ptr, index):
    # An index entry is one long: size = entry >> 17, offset = entry & $1ffff (17 bits).  Reading only the low word of the long
    # (the old code) is right for types 3-6, whose data areas are under $10000, but puts every type-2 class template at offset
    # >= $10000 (level 1: indices 100-254) $10000 too low.
    entry = idx_ptr + index * 4
    e = u32(ram, base, entry)
    if (e >> 17) == 0:
        return None
    return data_ptr + (e & 0x1FFFF)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("snap")
    args = ap.parse_args()

    ram, base = load_ram(args.snap)
    regs, _ = snapshot_regs(args.snap)
    a5 = regs["a5"]

    room_idx, room_dat, room_cnt = resource_type(ram, base, a5, ROOM_TYPE)
    obj_idx, obj_dat, obj_cnt = resource_type(ram, base, a5, OBJLIST_TYPE)

    for slot in range(room_cnt):
        rec = resolve(ram, base, room_idx, room_dat, slot)
        if rec is None:
            continue
        objcount = u8(ram, base, rec + 29)
        stream = resolve(ram, base, obj_idx, obj_dat, slot)
        if stream is None:
            print(f"slot {slot:3d} objcount={objcount:3d} ids=<no type-5 stream>")
            continue
        ids = [u16(ram, base, stream + 2 * i) for i in range(objcount + 1)]
        print(f"slot {slot:3d} objcount={objcount:3d} ids={ids}")


if __name__ == "__main__":
    main()
