"""full_room_name_census.py - combine the static per-room object-id census (room_object_census.py's
resolvers, type 5) with the live-driven array back-pointer writes captured by driving $00e854 (the
real room-transition trigger, mechanics.md section 4) for every room slot in one REPL session, to
resolve every placed object's own live display-name index for ALL 72 rooms from a single base
snapshot (gameplay_empire.snap) - not just the currently-loaded one. mechanics.md section 8 has the full
writeup and proof (23/23 cross-room validation, the GIANT RAT/slot-27 finding); this docstring only
covers how to re-run the tool.

The REPL driver (`w 185e0 <(slot<<16)|0x2888>; watch 38338 2200; callcap e854 2000000 -; unwatch`,
repeated once per slot 0-71 in one session) and its combined stdout+stderr transcript are the
`<combined_log>` argument below - see `M68000/scratchpad/ANCHORS.md` for where the corpus from the
73rd pass is kept. Each callcap is isolated (snapshot-restoring) so all 72 rooms are driven from the
SAME base snapshot with no cumulative drift; slot_off is `70 * (object's rank in its room's own
type-5 id list)`. The live_rec addresses this reveals are themselves persistent, pre-existing data
(not freshly allocated by the switch) - reading name_idx = u16(live_rec+10) directly from the
UNCHANGED base snapshot's own memory (no live driving needed for this second step) reproduces every
already-known value exactly (BOAT/PICKAXE/LEVER/SCONCE, 4/4) and extends cleanly to
never-before-loaded rooms (shared decorative records, e.g. slot 2's objects landing on CAVERN's own
already-known FUNGHI records).

    python full_room_name_census.py <combined_log> <base_snap>
"""
import re
import struct
import sys
from pathlib import Path

_M68000_ROOT = Path(__file__).resolve().parents[3]  # .../M68000
sys.path.insert(0, str(_M68000_ROOT / "tools"))
sys.path.insert(0, str(_M68000_ROOT / "reversing" / "cadaver" / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gfxview import load_ram, snapshot_regs  # noqa: E402
from room_object_census import resource_type, resolve  # noqa: E402
from name_strings import decode_index  # noqa: E402
from parse_rooms import parse as parse_rooms  # noqa: E402

MONSTER_LO, MONSTER_HI = 224, 234  # SCONCE..SKELETON cluster, mechanics.md section 8/sec65b


def u16(ram, base, addr):
    return struct.unpack(">H", ram[addr - base:addr - base + 2])[0]


def main():
    combined_log, snap = sys.argv[1], sys.argv[2]
    rooms_ce78 = parse_rooms(combined_log)

    ram, base = load_ram(snap)
    regs, _ = snapshot_regs(snap)
    a5 = regs["a5"]
    room_idx, room_dat, room_cnt = resource_type(ram, base, a5, 3)
    obj_idx, obj_dat, obj_cnt = resource_type(ram, base, a5, 5)
    t168 = struct.unpack(">I", ram[a5 + 168 - base:a5 + 172 - base])[0]
    t172 = struct.unpack(">I", ram[a5 + 172 - base:a5 + 176 - base])[0]

    hits = []
    print(f"{'slot':>4} {'id':>4} {'live_rec':>9} {'name_idx':>8}  name")
    for slot in range(100):
        rec = resolve(ram, base, room_idx, room_dat, slot)
        if rec is None:
            continue
        objcount = ram[rec - base + 29]
        stream = resolve(ram, base, obj_idx, obj_dat, slot)
        if stream is None:
            continue
        ids = [u16(ram, base, stream + 2 * i) for i in range(objcount + 1)]
        ids_trimmed = ids[:-1] if ids and ids[-1] == 0 else ids  # drop trailing sentinel, sec66/72nd-pass census convention
        ce78 = rooms_ce78[slot] if slot < len(rooms_ce78) else []
        if len(ce78) != len(ids_trimmed):
            print(f"  ** slot {slot}: MISMATCH ce78 hits={len(ce78)} vs trimmed census ids={len(ids_trimmed)} - ids={ids} **")
        for (idx, addr, live_rec), oid in zip(ce78, ids_trimmed):
            if oid == 0:
                continue  # array sentinel, not a real object
            name_idx = u16(ram, base, live_rec + 10)
            name = decode_index(ram, base, t168, t172, name_idx) if name_idx != 0xFFFF else b"<none>"
            flag = ""
            if MONSTER_LO <= name_idx < MONSTER_HI:
                flag = "  <-- MONSTER CLUSTER"
                hits.append((slot, oid, live_rec, name_idx, name))
            print(f"{slot:4d} {oid:4d} {live_rec:#08x} {name_idx:8d}  {name!r}{flag}")

    print("\n=== monster-cluster (224-233) hits across all rooms ===")
    if not hits:
        print("NONE - no room's object roster carries a monster-name index (224-233) under this field")
    for slot, oid, live_rec, name_idx, name in hits:
        print(f"slot {slot} id {oid} live_rec={live_rec:#08x} name_idx={name_idx} name={name!r}")


if __name__ == "__main__":
    main()
