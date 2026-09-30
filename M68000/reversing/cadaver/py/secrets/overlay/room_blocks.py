"""room_blocks.py [snap ...] [--dump]: the script blocks of the ROOM records (type 3, 100 index slots), the second block list
that events 19 (verb 9) and 20 (room countdown, verb 42) run against.

The consumer $00fdbc walks blocks at +$10 (count at +11) or, when the queued opcode has bit 14 set, at +$20 (count at +31).
Events 19 and 20 are queued as $4013 / $4014 with the ROOM record as the object, so a room's blocks live at +$20, count at +31.
The room record itself is 122+ bytes (CAVERN 122): door-link words, floor clamps, object count at +29 (the type-5 list length
minus one), and the block count at +31.

A block is [len][event | $80][gate bytes][verb bytes][$17] followed by ONE pad byte when the content through the $17 has an
odd length: every block `len` in both levels is even (rooms 59 + 90 blocks, objects 212 + 264), so blocks are word aligned.
The pad is uninitialised in room records (40, 02, c1, 50, ... ; only sometimes $17), so a room block does NOT end on $17 at
len-1 the way verb_decode.collect() requires of object blocks (that filter is why the object census saw only $17 pads).

Self-check per block: len is even; the grammar decodes gate + verbs to the first $17; the tail is 0 bytes if the content
(2 + gate + verbs + $17) is even and exactly 1 byte if it is odd; and the blocks tile the record from +$20 for the count at +31.

Run from M68000/:  python reversing/cadaver/py/secrets/overlay/room_blocks.py [snap ...] [--dump]"""
import sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[5]                        # M68000/
sys.path.insert(0, str(ROOT / 'reversing/cadaver/py')); sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import verb_decode as vd
from gfxview import load_ram, snapshot_regs
from room_object_census import resource_type, resolve

SNAPS = [str(ROOT / 'scratchpad/cadaver/gameplay_empire.snap'), str(ROOT / 'scratchpad/cadaver/level1_loaded.snap')]


def room_blocks(snap):
    """-> (rows, problems, nrooms).  rows = (slot, event byte, gate+verb body, block offset in the record)."""
    ram, base = load_ram(snap); regs, _ = snapshot_regs(snap); a5 = regs['a5']
    ridx, rdat, rcnt = resource_type(ram, base, a5, 3)
    rows, problems, nrooms = [], [], 0
    for slot in range(rcnt):
        a = resolve(ram, base, ridx, rdat, slot)
        if a is None: continue
        nrooms += 1
        cnt = ram[a + 31]
        if cnt == 0: continue
        p = a + 0x20
        if cnt > 12: problems.append('room %d: count %d' % (slot, cnt)); continue
        for i in range(cnt):
            ln = ram[p]
            if ln < 4 or ln % 2:
                problems.append('room %d block %d: len %d' % (slot, i, ln)); break
            rows.append((slot, ram[p + 1], bytes(ram[p + 2:p + ln]), p - a)); p += ln
    return rows, problems, nrooms


if __name__ == '__main__':
    snaps = [a for a in sys.argv[1:] if not a.startswith('--')] or SNAPS
    for snap in snaps:
        if '--dump' in sys.argv: vd.load_text(snap)
        rows, problems, nrooms = room_blocks(snap)
        good = 0; ev = collections.Counter(); used = collections.Counter(); rooms = set(); bad = []
        for slot, e, body, off in rows:
            try:
                out = []; g = vd.GATE.get(e & 0x7f, 0)
                if (e & 0x7f) > 28: raise vd.Bad('event beyond the gate table')
                out.append((0, -1, ['%02x' % b for b in body[:g]], 'GATE for event %d' % (e & 0x7f)))
                q = vd.parse(body, g, len(body), 0x17, out)
                if len(body) - q != (2 + q) % 2: raise vd.Bad('pad %d after content of %d' % (len(body) - q, 2 + q))
            except vd.Bad as ex:
                bad.append((slot, e, body.hex(), str(ex))); continue
            good += 1; ev[e & 0x7f] += 1; rooms.add(slot)
            for d, v, a, n in out:
                if v >= 0: used[v] += 1
            if '--dump' in sys.argv:
                print('room %d  +$%02x  event $%02x (%d)%s' % (slot, off, e & 0x7f, e & 0x7f, '  keep' if e & 0x80 else ''))
                print(vd.fmt(out))
        print('%s: %d rooms, %d rooms with blocks, %d blocks, %d decode to their first $17 with the right pad; events %s'
              % (Path(snap).name, nrooms, len(rooms), len(rows), good, dict(sorted(ev.items()))))
        for b in bad: print('  BAD', b)
        for p in problems: print('  PROBLEM', p)
        print('  verbs used:', dict(sorted(used.items())))
