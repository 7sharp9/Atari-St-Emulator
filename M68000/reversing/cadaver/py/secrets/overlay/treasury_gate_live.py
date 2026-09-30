"""treasury_gate_live.py [snap]: run id 2 BUTTON's own script (touched, event 5) under the real consumer with the type-8 list
empty and with the four objects 16, 32, 28 and 26 in it, and count the verb handlers that run.  The decoded script
(verb_decode.py) is `34 10  34 20  34 1c  34 1a  58 4 [ 70 3a  37 25 2 2 0  41 x4 ] 0f [ 28 f6 ]`:
four COND-in-type-8-list tests, IF (2270 == 4): sound $3a, teleport to room $25, the four objects placed in room $21;
ELSE message 246 (ONLY THE KING MAY ENTER HIS TREASURY).

The type-8 list (resource 8: 64 index words [id/flag, data offset], 4-byte data records [id, +2]) is empty in gameplay_empire.snap;
the four entries are poked as index words (1, i*4) and data words (id, 0).  Result (three runs from a fresh REPL each):
    list empty:            verbs 34 x4, 58 x1, 28 x1 (the ELSE message); 37, 70, 41 not hit; room 0000 -> 0000
    list 16, 32, 28, 26:   34 x4, 58 x1, 70 x1, 37 x1, 41 x4, 28 not hit; room 0000 -> 0025 (the consumer's gate hit count is 2:
                           a second event is queued during the room load, not examined)
    list 16, 32, 28:       as the empty list (one item short takes the ELSE part)
Run from M68000/: `uv run python reversing/cadaver/py/secrets/overlay/treasury_gate_live.py`."""
import sys
sys.path.insert(0, 'reversing/cadaver/py/secrets/overlay'); sys.path.insert(0, 'reversing/cadaver/py'); sys.path.insert(0, 'tools')
from ov import *
from gfxview import load_ram, snapshot_regs
from room_object_census import resource_type, resolve
import struct

snap = sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/cadaver/gameplay_empire.snap'
ram, base = load_ram(snap); regs, _ = snapshot_regs(snap)
t6i, t6d, _ = resource_type(ram, base, regs['a5'], 6)
rec = resolve(ram, base, t6i, t6d, 2)
u32 = lambda a: struct.unpack_from('>I', ram, a)[0]
d8 = u32(regs['a5'] + 96) + 8 * 0x12
idx8, dat8 = u32(d8), u32(d8 + 4)
VERB = {'34 in list': 0x1079c, '58 IF ==n': 0x1061a, '70 sound': 0x10ec8, '37 teleport': 0x10974, '41 place': 0x10aaa, '28 message': 0x11230}


def run(items):
    r = Repl(snap)
    for i, oid in enumerate(items):
        wl(r, idx8 + 4 * i, 0x0001_0000 | (4 * i))          # index word: occupied, data offset 4*i
        wl(r, dat8 + 4 * i, (oid << 16))                    # data record: id, +2 = 0
    q = int.from_bytes(r.mem(a5(152), 4), 'big')
    wl(r, q, 0x00050000 | (rec >> 16)); wl(r, q + 4, (rec & 0xffff) << 16); ww(r, a5(1154), 1)
    room0 = r.mem(a5(1166), 2).hex()
    h = r.hits(600000, 0xfe24, *VERB.values())
    room1 = r.mem(a5(1166), 2).hex()
    r.close()
    return {k: h.get(a, 0) for k, a in VERB.items()}, h.get(0xfe24, 0), room0, room1


for label, items in (('type-8 list empty', []), ('list = 16, 32, 28, 26', [16, 32, 28, 26]), ('list = 16, 32, 28 (one short)', [16, 32, 28])):
    v, gate, r0, r1 = run(items)
    print('%-32s gate matched %d  %s  room %s -> %s' % (label, gate, v, r0, r1))
