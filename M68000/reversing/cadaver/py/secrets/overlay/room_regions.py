"""room_regions.py [snap ...]: the region list that follows a room record's script blocks, and its match with the gate bytes of the
room's event-15 / event-17 blocks.

Room record (type 3): 32-byte header, script blocks from +$20 (count at +31, tiled by their len byte), then, when the index size
word leaves bytes over, a count byte N (then a zero byte) followed by N six-byte records (CAVERN: 3, room 2: 1, room 27: 2).  The contact test
$009160-$0092e6 tests the moving object's box against region D7 = 1..4 and queues event 15 (the hero, word 4(A1) == 0) or event 17
(any other object) for the room with D7 as the gate byte, so a room's event-15/17 gates must lie in 1..N.  Prints, per snapshot,
how many rooms have a region list, how many event-15/17 blocks there are, and how many gates lie inside 1..N (all of them if the
reading is right) and whether every region has at least one block."""
import sys, struct
from pathlib import Path
ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / 'reversing/cadaver/py')); sys.path.insert(0, str(ROOT / 'tools'))
from gfxview import load_ram, snapshot_regs
from room_object_census import resource_type, resolve
SNAPS = [str(ROOT / 'scratchpad/cadaver/gameplay_empire.snap'), str(ROOT / 'scratchpad/cadaver/level1_loaded.snap')]
for snap in (sys.argv[1:] or SNAPS):
    ram, base = load_ram(snap); a5 = snapshot_regs(snap)[0]['a5']
    ri, rd, rc = resource_type(ram, base, a5, 3)
    rooms = tail_rooms = blocks = inside = b0ok = 0; flags = {}; b0bad = []; uncovered = []; badtail = []; gate_no_region = []
    for s in range(rc):
        a = resolve(ram, base, ri, rd, s)
        if a is None: continue
        rooms += 1
        size = struct.unpack_from('>H', ram, ri + s * 4 - base)[0]
        p = a + 0x20; gates = []
        for i in range(ram[a + 31]):
            ln = ram[p]; ev = ram[p + 1] & 0x7f
            if ev in (15, 17): gates.append(ram[p + 2])
            p += ln
        tail = size - (p - a)
        if ram[a] == p - a: b0ok += 1
        else: b0bad.append((s, ram[a], p - a))
        flags.setdefault((ram[a + 23] >> 1 & 1, ram[a + 23] >> 4 & 1, 1 if tail else 0), []).append(s)
        n = 0
        if tail:
            n = ram[p]
            if tail != 2 + 6 * n: badtail.append((s, tail, n))
            tail_rooms += 1
        blocks += len(gates); inside += sum(1 for g in gates if 1 <= g <= n)
        if gates and not n: gate_no_region.append(s)
        if n and set(range(1, n + 1)) - set(gates): uncovered.append((s, n, sorted(set(gates))))
    print('%s: %d rooms, %d with a region list, tails that are not 2+6N: %s; event-15/17 blocks %d, gate in 1..N: %d; '
          'rooms with gates but no region list: %s; rooms with a region that has no 15/17 block: %s'
          % (Path(snap).name, rooms, tail_rooms, badtail, blocks, inside, gate_no_region, uncovered))
    print('  byte 0 == end of the blocks: %d of %d (bad %s)' % (b0ok, rooms, b0bad[:5]))
    print('  (byte23 bit1, bit4, has region list) -> room count:', {k: len(v) for k, v in sorted(flags.items())})
