"""door_walk.py - static door-connectivity walk (cadaver.md Open item 1).

For every populated type-3 room's 7 door-link slots (record +6..+19, mechanics.md sec14), resolve
the door id through the type-4 resource table (sec38a, 8-byte records, confirmed against the 3
known descriptors $6d4ea/$6d4f2/$6d532 in the one-disk build) to get each descriptor's candidate
entry coordinate (bytes +0/+1) and stated target-id word (+2). Then run the exact algorithm $de5e
uses (sec38d): linear scan over all type-3 rooms in slot order, first rectangle containing the
candidate (x,y) wins - and compare the resolved destination room against the door's owning room via
world_map.py's own adjacency() classifier.

Like world_map.py (sec59), type 3's and type 4's index-table/data-area pointers are **not** fixed
constants across builds - both are resolved fresh from each snapshot's own resource manager via
world_map.resource_type(), never hardcoded.

    python reversing/cadaver/py/door_walk.py <snap>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gfxview import load_ram, snapshot_regs  # noqa: E402
from world_map import SLOT_COUNT, ROOM_TYPE, resource_type, read_room, adjacency, \
    KNOWN_NAMES  # noqa: E402

DOOR_TYPE = 4
TYPE4_COUNT = 400


def u16(ram, base, addr):
    o = addr - base
    return int.from_bytes(ram[o:o + 2], "big")


def s16(ram, base, addr):
    v = u16(ram, base, addr)
    return v - 0x10000 if v >= 0x8000 else v


def read_door_slots(ram, base, rec):
    """7 door-link slots at rec+6..rec+19, 2 bytes each, $ffff = unused."""
    slots = []
    for i in range(7):
        v = u16(ram, base, rec + 6 + i * 2)
        if v != 0xffff:
            slots.append(v)
    return slots


def resolve_descriptor(ram, base, index_table, data_area, door_id):
    entry = index_table + door_id * 4
    size = u16(ram, base, entry)
    if size == 0 or door_id >= TYPE4_COUNT:
        return None
    offset = u16(ram, base, entry + 2)
    addr = data_area + offset
    cx = ram[addr - base]
    cy = ram[addr - base + 1]
    target_word = s16(ram, base, addr + 2)
    return {"addr": addr, "cx": cx, "cy": cy, "target_word": target_word}


def resolve_room_for_point(rooms, cx, cy):
    """Mirror $de5e (mechanics.md sec38d): linear scan in slot order, first containing rect wins."""
    for r in rooms:
        if r["x0"] <= cx <= r["x1"] and r["y0"] <= cy <= r["y1"]:
            return r
    return None


def main():
    snap = sys.argv[1]
    ram, base = load_ram(snap)
    regs, ok = snapshot_regs(snap)
    if not ok:
        raise SystemExit(f"{snap}: not a snapshot")
    a5 = regs["a5"] & 0xFFFFFF

    room_index, room_data, _ = resource_type(ram, base, a5, ROOM_TYPE)
    door_index, door_data, _ = resource_type(ram, base, a5, DOOR_TYPE)

    rooms = [r for s in range(SLOT_COUNT)
             if (r := read_room(ram, base, room_index, room_data, s)) is not None]
    by_slot = {r["slot"]: r for r in rooms}

    seen_doors = {}
    for r in rooms:
        for door_id in read_door_slots(ram, base, r["rec"]):
            desc = resolve_descriptor(ram, base, door_index, door_data, door_id)
            key = door_id
            if key in seen_doors:
                seen_doors[key]["rooms"].append(r["slot"])
                continue
            entry = {"door_id": door_id, "rooms": [r["slot"]], "desc": desc}
            seen_doors[key] = entry

    for door_id, info in sorted(seen_doors.items()):
        desc = info["desc"]
        owners = info["rooms"]
        if desc is None:
            print(f"door {door_id:#04x} owners={owners}: UNRESOLVED (no type-4 slot)")
            continue
        cx, cy, tw = desc["cx"], desc["cy"], desc["target_word"]
        dest = resolve_room_for_point(rooms, cx, cy)
        dest_slot = dest["slot"] if dest else None
        tag = ""
        if tw == 0:
            tag = "[id=0 hardcoded-link]"
        elif tw == -1:
            tag = "[id=-1 sound-cue-only, no room commit]"
        else:
            tag = f"[id={tw} generic-lookup, currently always-miss per sec14]"
        rel = []
        for owner in owners:
            if dest_slot is None:
                rel.append(f"{owner}->NONE")
            elif dest_slot == owner:
                rel.append(f"{owner}->self")
            else:
                kind = adjacency(by_slot[owner], by_slot[dest_slot])
                rel.append(f"{owner}->{dest_slot} ({kind or 'NON-ADJACENT (teleport)'})")
        print(f"door {door_id:#04x} candidate=({cx},{cy}) {tag} desc@{desc['addr']:#07x}: "
              f"{', '.join(rel)}")

    print(f"\n{len(seen_doors)} distinct door ids referenced across {len(rooms)} rooms")


if __name__ == "__main__":
    main()
