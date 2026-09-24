"""door_id_words.py - probe the 5 doors with a genuine positive id word (cadaver.md Open item 2).

For each of doors 53/73/155/167/244 (mechanics.md sec47b/47c), dumps the door descriptor's own
+4..+7 bytes (sec47a: "unread, not needed to close item 1") and checks whether the id word, read
as a type-6 object id (sec38a), resolves to a real populated record, and if so that record's own
+15 byte (LOCK/UNLOCK's bit-2 flag, sec22c/23c). Proof for sec49.

    python reversing/cadaver/py/door_id_words.py <snap>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gfxview import load_ram  # noqa: E402
from world_map import SLOT_COUNT, read_room  # noqa: E402
from door_walk import read_door_slots, resolve_descriptor  # noqa: E402

TYPE6_INDEX = 0x4b596
TYPE6_DATA = 0x6eb92
TYPE6_COUNT = 1000

POSITIVE_IDS = [53, 73, 155, 167, 244]


def u16(ram, base, addr):
    o = addr - base
    return int.from_bytes(ram[o:o + 2], "big")


def read_type6(ram, base, obj_id):
    if obj_id >= TYPE6_COUNT:
        return None
    entry = TYPE6_INDEX + obj_id * 4
    size = u16(ram, base, entry)
    if size == 0:
        return None
    offset = u16(ram, base, entry + 2)
    addr = TYPE6_DATA + offset
    o = addr - base
    return {"addr": addr, "size": size, "bytes": ram[o:o + max(size, 16)]}


def main():
    snap = sys.argv[1]
    ram, base = load_ram(snap)
    rooms = [r for s in range(SLOT_COUNT) if (r := read_room(ram, base, s)) is not None]

    seen = {}
    for r in rooms:
        for door_id in read_door_slots(ram, base, r["rec"]):
            if door_id in seen:
                continue
            desc = resolve_descriptor(ram, base, door_id)
            seen[door_id] = (r["slot"], desc)

    for door_id, (owner, desc) in sorted(seen.items()):
        if desc is None or desc["target_word"] not in POSITIVE_IDS:
            continue
        tw = desc["target_word"]
        addr = desc["addr"]
        o = addr - base
        tail = ram[o:o + 8]
        print(f"door {door_id:#04x} owner_room={owner} id_word={tw} desc@{addr:#07x} "
              f"bytes={tail.hex()}")
        rec = read_type6(ram, base, tw)
        if rec is None:
            print(f"  as type-6 id {tw}: NOT a populated object record")
        else:
            b = rec["bytes"]
            plus15 = b[15] if len(b) > 15 else None
            print(f"  as type-6 id {tw}: addr={rec['addr']:#07x} size={rec['size']} "
                  f"first16={b[:16].hex()} +15={plus15:#04x} bit2={'SET' if plus15 and plus15 & 4 else 'clear'}")


if __name__ == "__main__":
    main()
