"""script_census.py [snap]: census of the per-object event scripts run by the ring-304 consumer $00fdbc.  Format (read off
$00fdbc-$00fe70): an object record (type 6) has a block count at +11 and its blocks start at +$10 (queue opcodes without bit 14), or
a count at +31 and blocks at +$20 (opcode bit 14 set).  Block = [len][event opcode | $80 keep][verb bytes ... $17]; len includes
itself.  Event opcode = the ring-304 opcode that was queued (5 = touched, ...).  Verb bytes index the table at $00ffba (see
verb_table94.py): verb 37 = $010974 (teleport: room byte + 3 bytes), verb 51 = $010410 (LOAD LEVEL operand+1), verb 55 = POISON.
Prints the number of objects with blocks, the event-opcode histogram, and the blocks that contain byte $25 (37) / $33 (51) at a
position that is an opcode under a naive walk (operands not decoded: candidates only)."""
import sys, struct, collections
sys.path.insert(0, 'reversing/cadaver/py'); sys.path.insert(0, 'tools')
from gfxview import load_ram, snapshot_regs
from room_object_census import resource_type, resolve
snap = sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/cadaver/gameplay_empire.snap'
ram, base = load_ram(snap); regs, _ = snapshot_regs(snap); a5 = regs['a5']
t6i, t6d, n6 = resource_type(ram, base, a5, 6)
ev = collections.Counter(); objs = 0; blocks = 0; cand = []
for oid in range(1000):
    a = resolve(ram, base, t6i, t6d, oid)
    if a is None: continue
    for cntoff, start in ((11, 0x10), (31, 0x20)):
        cnt = ram[a + cntoff]
        if not 0 < cnt < 12: continue
        p = a + start; ok = True; bl = []
        for _ in range(cnt):
            ln = ram[p]
            if ln < 3 or ln > 120 or ram[p + ln - 1] != 0x17: ok = False; break
            bl.append((ram[p + 1], bytes(ram[p + 2:p + ln - 1]))); p += ln
        if ok:
            objs += 1; blocks += len(bl)
            for e, body in bl:
                ev[(e & 0x7f) | (0x4000 if start == 0x20 else 0)] += 1
                if 0x25 in body or 0x33 in body: cand.append((oid, start, e, body.hex()))
print('type-6 records with well-formed script blocks: %d objects, %d blocks' % (objs, blocks))
print('event opcodes (bit 14 set = blocks at +$20):', dict(sorted(ev.items())))
print('blocks containing $25 or $33 (candidates, %d):' % len(cand))
for c in cand[:40]: print('  id %4d blocks@+$%02x event $%02x: %s' % c)
