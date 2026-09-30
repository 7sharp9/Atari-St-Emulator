"""teleport_live.py: inject a 'touched' (opcode 5) event for an object whose script block contains verb 37 (teleport, $010974) and watch
the room change.  Objects (census in script_census.py): id 86 LEVER (slot 37): `46 3a 25 22 02 02 00` -> room $22 at (2,2) facing 0;
id 2 BUTTON (slot 34): `... 25 25 02 02 00` -> room $25; id 56 STONE SHELF (slot 38) -> room $25.  Start snapshot
scratchpad/cadaver/gameplay_empire.snap (CAVERN loaded; every type-6 record is resident, so any object's script can be run).
Expected for id 86: $00fe24=1 $00fe30=1 $010974=1 $00e854=1, room 0000 -> 0022.  Usage: python3 teleport_live.py [object id].  Prints hits on $010974 (verb 37 entry), $00e854 (room load), (A5)+1166 before/after."""
import sys
sys.path.insert(0, 'reversing/cadaver/py/secrets/overlay'); sys.path.insert(0, 'reversing/cadaver/py'); sys.path.insert(0, 'tools')
from ov import *
from gfxview import load_ram, snapshot_regs
from room_object_census import resource_type, resolve
oid = int(sys.argv[1]) if len(sys.argv) > 1 else 86
ram, base = load_ram('scratchpad/cadaver/gameplay_empire.snap'); regs, _ = snapshot_regs('scratchpad/cadaver/gameplay_empire.snap')
t6i, t6d, _ = resource_type(ram, base, regs['a5'], 6)
rec = resolve(ram, base, t6i, t6d, oid)
print('object id %d record $%06x, script bytes %s' % (oid, rec, bytes(ram[rec + 0x10:rec + 0x30]).hex()))
r = Repl()
q = int.from_bytes(r.mem(a5(152), 4), 'big')
wl(r, q, 0x00050000 | (rec >> 16)); wl(r, q + 4, ((rec & 0xffff) << 16)); ww(r, a5(1154), 1)
print('room before', r.mem(a5(1166), 2).hex(), 'queue', r.mem(q, 10).hex())
h = r.hits(400000, 0xfe24, 0xfe30, 0x10974, 0xe854, 0x72ac)
print({hex(k): v for k, v in h.items()}, 'room after', r.mem(a5(1166), 2).hex(), '2134..2138', r.mem(a5(2134), 6).hex())
r.close()
