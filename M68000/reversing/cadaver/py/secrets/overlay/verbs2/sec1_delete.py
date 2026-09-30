"""Section 1: DELETE (0, 2), HIDE (26), SHOW (1)"""
from lib2 import *

def run(h_factory=None):
    h = H(SNAP0); r = h.r
    # ---------------- verb 0 DELETE object: 240 (plain), 237 (template class 3), 56 (template +12 bit 0 clear)
    for oid, want_bit15 in ((240, False), (237, True), (56, False)):
        room = r.b(h.obj(oid) + 10); tb = tmpl_bytes(h, oid)
        ids0, size0, off0 = t5_list(h, room); c27, c28, c29 = room_counts(h, room)
        d = h.call(0, [oid >> 8, oid & 255])
        lab = 'verb 0  DELETE #%d (room %d, tmpl class %02x, tmpl+12 bit0 %d)' % (oid, room, tb[22], tb[12] & 1)
        chk(lab + ': returns, operand 2 bytes, no assert', d['ret'] and not d['thrown'] and d['da1'] == 2)
        chk(lab + ': 1164(A5) = %d' % oid, a5w(h, 1164, d) == oid)
        chk(lab + ': pending-delete list 1386(A5) count 0 -> 1', a5w(h, 1386) == 0 and a5w(h, 1386, d) == 1)
        e = a5w(h, 1388, d)
        chk(lab + ': list entry = $%04x (bit 15 %s)' % (e, 'set for class 3' if want_bit15 else 'clear'), e == oid | (0x8000 if want_bit15 else 0))
        ids1, size1, off1 = t5_list(h, room, d)
        chk(lab + ': removed from room %d list (%d -> %d bytes)' % (room, size0, size1), oid in ids0 and oid not in ids1 and size1 == size0 - 2 and off1 == off0 and [i for i in ids0 if i != oid] == ids1)
        n27, n28, n29 = room_counts(h, room, d)
        exp = (c27 - 1, c28, c29 - 1) if tb[12] & 1 else (c27, c28 - 1, c29 - 1)
        chk(lab + ': room record counters (+27,+28,+29) %s -> %s' % ((c27, c28, c29), (n27, n28, n29)), (n27, n28, n29) == exp)
        rec_changes = [x for x in changed(h, d, 't6/')]
        chk(lab + ': no type-6 record byte changed by the call itself', rec_changes == [], rec_changes[:3])
    # ---------------- verb 2 DELETE the current object: 348(A5) := record
    ref = h.call(0, [0, 240]); st_ref = sorted(h.structural(ref['delta'])[0])
    h.poke(A5 + 348, h.obj(240).to_bytes(4, 'big'))
    d = h.call(2, [])
    chk('verb 2  DELETE current (348(A5) -> record of #240): consumes no operand', d['ret'] and d['da1'] == 0)
    chk('verb 2  delta identical to verb 0 #240 (structural items, %d)' % len(st_ref), sorted(h.structural(d['delta'])[0]) == st_ref)
    h.close()
    # ---------------- natural: object 239's own event-18 block (gate 00 f0): CLEAR FLAG 23..26, DELETE #240.  Inject opcode 18, word $00f0.
    noise = noise_for(SNAP0)
    h = H(SNAP0); r = h.r
    idx6 = h.rows[6][0]
    room = r.b(h.obj(240) + 10)
    ids0, size0, _ = t5_list(h, room); c27, c28, c29 = room_counts(h, room)
    e0 = r.l(idx6 + 4 * 240); flags0 = [r.w(h.flag_rec(n) + 2) for n in (0x23, 0x24, 0x25, 0x26)]
    df, hits = inject_run(h, 239, 0x12, 0x00f0)
    df = {a: v for a, v in df.items() if a not in noise}
    chk('natural[v0,10]  #239 event 18 (gate 00 f0): consumer matched a block once', hits.get(0xfe24) == 1, hits)
    e1 = r.l(idx6 + 4 * 240)
    chk('natural[v0]  #239: pending-delete count back to 0 after the frame service drained it (1386(A5))', r.w(A5 + 1386) == 0 and r.w(A5 + 1388) == 240)
    chk('natural[v0]  #239: type-6 index entry of #240 freed: size $%04x -> $%04x, later records slid down by $20' % (e0 >> 16, e1 >> 16), (e0 >> 16) == 0x20 and (e1 >> 16) == 0 and (r.l(idx6 + 4 * 241) & 0x1ffff) == (h.rows[6][0] and (int.from_bytes(h.ram[idx6 + 4 * 241:idx6 + 4 * 241 + 4], 'big') & 0x1ffff) - 0x20))
    ids1, size1, _ = t5_list(h, room); n27, n28, n29 = room_counts(h, room)
    chk('natural[v0]  #239: #240 gone from room %d list (%d -> %d bytes), counters %s -> %s' % (room, size0, size1, (c27, c28, c29), (n27, n28, n29)), 240 in ids0 and 240 not in ids1 and size1 == size0 - 2 and (n27, n29) == (c27 - 1, c29 - 1))
    chk('natural[v10]  #239: flags 23..26 (verb 10 x4) end at 0 (were %s)' % flags0, [r.w(h.flag_rec(n) + 2) for n in (0x23, 0x24, 0x25, 0x26)] == [0, 0, 0, 0])
    h.close()
    # ---------------- natural: #107 event 12 (gate 00) = `73 actor #12` then `2` (DELETE the current object = #107 itself)
    noise = noise_for(SNAP0)
    h = H(SNAP0); r = h.r
    idx6 = h.rows[6][0]
    e0 = r.l(idx6 + 4 * 107); rm107 = r.b(h.obj(107) + 10); p107 = tuple(r.mem(h.obj(107), 3)); ids0, s0, _ = t5_list(h, rm107)
    df, hits = inject_run(h, 107, 12, 0)
    e1 = r.l(idx6 + 4 * 107)
    chk('natural[v2,73]  #107 event 12 (gate 00; `73 actor #12`, `2`): consumer matched once', hits.get(0xfe24) == 1, hits)
    chk('natural[v2]  #107: verb 2 deleted the current object: 1386(A5) drained (count %d, entry %d), type-6 index entry of #107 freed ($%04x -> $%04x)' % (r.w(A5 + 1386), r.w(A5 + 1388), e0 >> 16, e1 >> 16), r.w(A5 + 1386) == 0 and r.w(A5 + 1388) == 107 and (e0 >> 16) > 0 and (e1 >> 16) == 0)
    ids1, s1, _ = t5_list(h, rm107)
    chk('natural[v2]  #107 gone from its room list (room $%02x: %d -> %d bytes)' % (rm107, s0, s1), 107 in ids0 and 107 not in ids1)
    p12 = tuple(r.mem(h.obj(12), 3)); rm12 = r.b(h.obj(12) + 10)
    chk('natural[v73]  #12 moved to the position and room of the actor #107: room $%02x %s (was at %s in room $%02x)' % (rm12, p12, p107, rm107), rm12 == rm107 and p12 == p107)
    h.close()

if __name__ == '__main__':
    run(); print('ok %d bad %d' % (OK, BAD))
