"""The town layouts `$2eac`/`$2fc0` place a lord's buildings from, and the building names.

A lord's kind (byte 1 of his `$4e514` record) selects a stream of 3-byte records (dx, dy, building kind) at `$3078 + word[$3078 + 2*kind]`,
ended by a record whose first byte is `$9d`. The building kind names are the game's own table `housenam` at `$a15a` (printed by `$9ccc`).

    cd M68000 && python reversing/powermonger/py/town_layouts.py [snap-or-ram]   (default scratchpad/pm139/jobs/pop_done.snap)

Prints each kind's records and an ASCII picture (one letter per building: H TownHall, V Tavern, I FishHut, F FarmHouse, R Ranch, B Barn,
C Church, W WorkShop, U Turret, S Square, X Ruin, T Tower, M Mine; the y axis is the stored dy, which way it points on screen is not established).
`economy.md` "Buildings and town layouts": kinds 1 to 6 are real layouts, kinds 0, 7 and 8 index past the table.
"""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from disassemble import ram_from_snap

src = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "scratchpad/pm139/jobs/pop_done.snap")
r = Path(src).read_bytes() if src.endswith(".ram") else ram_from_snap(src)
names = []
for k in range(13):
    a = 0xa15a + 26 + struct.unpack_from(">H", r, 0xa15a + 2 * k)[0]
    names.append(bytes(r[a:a + 20]).split(b"\0")[0].decode())
print("building kinds:", ", ".join(f"{k} {n}" for k, n in enumerate(names)))
LETTER = {"TownHall": "H", "Tavern": "V", "FishHut": "I", "FarmHouse": "F", "Ranch": "R", "Barn": "B", "Church": "C",
          "WorkShop": "W", "Turret": "U", "Square": "S", "Ruin": "X", "Tower": "T", "Mine": "M"}
s8 = lambda v: v - 256 if v >= 128 else v
for kind in range(1, 7):
    a = 0x3078 + struct.unpack_from(">H", r, 0x3078 + 2 * kind)[0]
    recs = []
    while r[a] != 0x9d and len(recs) < 64:
        recs.append((s8(r[a]), s8(r[a + 1]), r[a + 2]))
        a += 3
    print(f"\nlord kind {kind}: {len(recs)} buildings")
    for dx, dy, k in recs:
        print(f"   ({dx:+d},{dy:+d}) {names[k] if k < 13 else k}")
    xs = [x for x, _, _ in recs]
    ys = [y for _, y, _ in recs]
    grid = {(x, y): LETTER[names[k]] for x, y, k in recs}
    for y in range(min(ys), max(ys) + 1):
        print("   " + " ".join(grid.get((x, y), ".") for x in range(min(xs), max(xs) + 1)))
