"""Parse all_rooms_combined.log (72 sequential `w 185e0.. / watch / callcap e854 / unwatch` blocks,
one per room slot, stdout+stderr interleaved in real execution order) into a per-room list of
(array_index, live_rec) pairs, using the $00ce78 WriteWord pairs as the array back-pointer writer
(mechanics.md sec66's slot_addr+6 field). Room boundaries are found via each block's own
"Watching [$lo,$hi]" stdout marker (72 of them, one per `watch` command re-issued per room).
"""
import re
import sys

ARRAY_BASE = 0x38338
SLOT_SIZE = 0x46

def parse(path):
    with open(path) as f:
        text = f.read()
    # split on the "Watching [" marker lines - each room re-issues `watch`, so there are 72 splits
    parts = text.split("Watching [")
    # parts[0] is the preamble before the first watch; parts[1..] are one per room
    room_blocks = parts[1:]
    assert len(room_blocks) == 72, f"expected 72 room blocks, got {len(room_blocks)}"
    rooms = []
    for slot, block in enumerate(room_blocks):
        pairs = []
        # find consecutive $00ce78 WriteWord hi then lo (same step)
        lines = block.splitlines()
        i = 0
        hits = []
        for line in lines:
            m = re.match(r"WATCH: step=(\d+) pc=\$00ce78 WriteWord \$([0-9a-f]+) <- \$([0-9a-f]+)", line)
            if m:
                hits.append((int(m.group(1)), int(m.group(2), 16), int(m.group(3), 16)))
        # group into pairs (hi word write, lo word write) by address adjacency (addr, addr+2)
        j = 0
        while j + 1 < len(hits):
            (s0, a0, v0), (s1, a1, v1) = hits[j], hits[j+1]
            if a1 == a0 + 2 and s0 == s1:
                live_rec = (v0 << 16) | v1
                idx = (a0 - 6 - ARRAY_BASE) // SLOT_SIZE
                pairs.append((idx, a0, live_rec))
                j += 2
            else:
                j += 1
        rooms.append(pairs)
    return rooms


if __name__ == "__main__":
    rooms = parse(sys.argv[1])
    for slot, pairs in enumerate(rooms):
        print(f"slot {slot:3d}: {len(pairs)} ce78 hits: " +
              " ".join(f"idx{idx}:{lr:#08x}" for idx, addr, lr in pairs))
