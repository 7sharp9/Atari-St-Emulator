"""Section 4: CREATE / PLACE family: 36, 41, 44, 73, 84"""
from lib2 import *
import lib2

def size6(h, oid): return int.from_bytes(h.ram[h.rows[6][0] + 4 * oid:h.rows[6][0] + 4 * oid + 2], 'big')

def spawn_entry(h, d):
    """the entry the verb appended to the spawn list 1466(A5): count word, then 16-byte entries [size.w][clone ptr.l][x][y][z][facing][D6.w][template ptr.l]"""
    n = a5w(h, 1466, d)
    b = a5b(h, 1468 + 16 * (n - 1), 16, d)
    return n, {'size': int.from_bytes(b[0:2], 'big'), 'ptr': int.from_bytes(b[2:6], 'big'), 'x': b[6], 'y': b[7], 'z': b[8], 'f': b[9],
               'd6': int.from_bytes(b[10:12], 'big'), 'tmpl': int.from_bytes(b[12:16], 'big')}

def run():
    h = H(SNAP0); r = h.r
    # ---------------- 36 CREATE object o at fixed (x, y, z, facing): the level-0 uses: #447 (12,b,32,fe), #448 (26,11,b,fe), #466 (10,1b,2,fe)
    for oid, (x, y, z, f) in ((447, (0x12, 0x0b, 0x32, 0xfe)), (448, (0x26, 0x11, 0x0b, 0xfe)), (466, (0x10, 0x1b, 0x02, 0xfe))):
        d = h.call(36, [oid >> 8, oid & 255, x, y, z, f])
        n, e = spawn_entry(h, d)
        rec = h.obj(oid); sz = size6(h, oid)
        tmpl = h.res(2, int.from_bytes(h.ram[rec + 6:rec + 8], 'big'))
        lab = 'verb 36 CREATE #%d at (%x,%x,%x) facing %02x' % (oid, x, y, z, f)
        chk(lab + ': returns, consumes 6 bytes, no assert', d['ret'] and not d['thrown'] and d['da1'] == 6)
        chk(lab + ': spawn list count 1466(A5) 0 -> %d; entry x,y,z,facing = operands' % n, a5w(h, 1466) == 0 and n == 1 and (e['x'], e['y'], e['z'], e['f']) == (x, y, z, f), e)
        chk(lab + ': entry D6 word = $000f (fixed-position mode), size %d = index-entry size of #%d (%d), template ptr $%06x' % (e['size'], oid, sz, e['tmpl']), e['d6'] == 0x0f and e['size'] == sz and e['tmpl'] == tmpl)
        clone = after(h, d, e['ptr'], sz)
        src = r.mem(rec, sz)
        diff = [i for i in range(sz) if clone[i] != src[i]]
        chk(lab + ': a fresh type-9 slot $%06x (2120(A5)=%d) holds a copy of #%d\'s record (differs at %s)' % (e['ptr'], a5w(h, 2120, d), oid, diff), len(diff) <= 2 and e['ptr'] == a5l(h, 48, d), diff)
    # ---------------- 44 CREATE o2 next to o1 (slot, facing) / 84 CREATE o2 relative to o1 (dx, dy, z, facing): o1 = #193 (50,11,0)
    o1 = 193; p1 = r.mem(h.obj(o1), 3)
    d = h.call(44, [0, o1, 0x01, 0xc0, 6, 0xfe])
    n, e = spawn_entry(h, d)
    tb448 = tmpl_bytes(h, 448)
    chk('verb 44 CREATE #448 next to #193 (slot 6, facing fe): consumes 6 bytes; entry position = #193\'s (%d,%d,%d); facing fe' % tuple(p1), d['ret'] and d['da1'] == 6 and (e['x'], e['y'], e['z'], e['f']) == tuple(p1) + (0xfe,) and n == 1, e)
    tab5d2c = h.ram[0x5d2c:0x5d2c + 16]
    chk('verb 44 ... template #448 class byte22 = $%02x (bit 7 clear) so D6 = table $5d2c[slot 6] = $%02x' % (tb448[22], tab5d2c[6]), not tb448[22] & 0x80 and e['d6'] == tab5d2c[6], e)
    d = h.call(84, [0, o1, 0x01, 0xc0, 3, 4, 5, 0xfe])
    n, e = spawn_entry(h, d)
    chk('verb 84 CREATE #448 relative to #193 (dx 3, dy 4, z 5, facing fe): consumes 8 bytes; entry = (%d+3, %d+4, 5) facing fe' % (p1[0], p1[1]), d['ret'] and d['da1'] == 8 and (e['x'], e['y'], e['z'], e['f']) == (p1[0] + 3, p1[1] + 4, 5, 0xfe) and n == 1, e)
    # ---------------- 41 PLACE object in room r at (x, y, z)
    room16 = r.b(h.obj(16) + 10)
    ids_a0, sa0, _ = t5_list(h, 0x21); ids_b0, sb0, _ = t5_list(h, 0x25)
    d = h.call(41, [0, 16, 0x25, 0x10, 0x11, 0x02])
    a = h.obj(16)
    chk('verb 41 PLACE #16 (room $%02x) in room $25 (not the current room 0) at (16,17,2): consumes 6 bytes' % room16, d['ret'] and not d['thrown'] and d['da1'] == 6)
    ids_a1, sa1, _ = t5_list(h, 0x21, d); ids_b1, sb1, _ = t5_list(h, 0x25, d)
    rc = [x for x in changed(h, d, 't6/')]
    chk('verb 41 ... record: x,y,z = (%d,%d,%d), room byte +10 = $%02x, flags $%02x -> $%02x (bit 3 set: placed when the room is entered)' % (afterb(h, d, a), afterb(h, d, a + 1), afterb(h, d, a + 2), afterb(h, d, a + 10), r.b(a + 3), afterb(h, d, a + 3)),
        (afterb(h, d, a), afterb(h, d, a + 1), afterb(h, d, a + 2), afterb(h, d, a + 10)) == (0x10, 0x11, 0x02, 0x25) and afterb(h, d, a + 3) == r.b(a + 3) | 8)
    chk('verb 41 ... room $21 loses #16 (%d -> %d entries), room $25 gains it (%d -> %d), 1260(A5) := $25' % (sa0 // 2, sa1 // 2, sb0 // 2, sb1 // 2),
        16 in ids_a0 and 16 not in ids_a1 and 16 in ids_b1 and 16 not in ids_b0 and a5w(h, 1260, d) == 0x25)
    dcur = h.call(41, [0, 16, 0x00, 0x10, 0x11, 0x02]); dfe = h.call(41, [0, 16, 0xfe, 0x10, 0x11, 0x02])
    chk('verb 41 ... room operand $fe (= this room) gives the same delta as the explicit current room 0 (%d changed bytes)' % len(dcur['delta']), dcur['delta'] == dfe['delta'])
    a = h.obj(16)
    chk('verb 41 ... in the current room: room byte +10 = %d, x,y,z = (%d,%d,%d), sprite word +8 %s -> %s' % (afterb(h, dcur, a + 10), afterb(h, dcur, a), afterb(h, dcur, a + 1), afterb(h, dcur, a + 2), r.mem(a + 8, 2).hex(), after(h, dcur, a + 8, 2).hex()),
        afterb(h, dcur, a + 10) == 0 and (afterb(h, dcur, a), afterb(h, dcur, a + 1)) == (0x10, 0x11) and 16 in t5_list(h, 0, dcur)[0])
    d = h.call(41, [0, 237, 0x21, 0x10, 0x10, 0])
    chk('verb 41 PLACE #237 (template class 3 = creature): assert "CANT PUT CREATURE IN ROOM"', bool(d['thrown']) and not d['ret'])
    # ---------------- 73: the SECOND operand moves to the position (and room) of the FIRST
    for first, second in ((16, 60), (60, 16)):
        p1 = r.mem(h.obj(first), 3); rm1 = r.b(h.obj(first) + 10); a2 = h.obj(second)
        d = h.call(73, [first >> 8, first & 255, second >> 8, second & 255])
        pos2 = (afterb(h, d, a2), afterb(h, d, a2 + 1), afterb(h, d, a2 + 2)); rm2 = afterb(h, d, a2 + 10)
        exact = rm1 != 0
        chk('verb 73 [#%d, #%d]: consumes 4 bytes; #%d ends in room $%02x (the room of #%d = $%02x), position %s (first at %s)' % (first, second, second, rm2, first, rm1, pos2, tuple(p1)),
            d['ret'] and d['da1'] == 4 and rm2 == rm1 and (pos2 == tuple(p1) if exact else pos2[0] == p1[0]), d['thrown'])
        f1 = r.mem(h.obj(first), 16)
        chk('verb 73 [#%d, #%d]: the first operand\'s record is not written' % (first, second), all(afterb(h, d, h.obj(first) + i) == f1[i] for i in range(16)))
    h.close()
    # ---------------- natural: 36 through #82's event-7 block, drained by the frame service into a real new object
    noise = noise_for(SNAP0)
    h = H(SNAP0); r = h.r
    ids0, s0, _ = t5_list(h, 0); c27, c28, c29 = room_counts(h, 0)
    df, hits = inject_run(h, 82, 7, 0, steps=200000)
    ids1, s1, _ = t5_list(h, 0); n27, n28, n29 = room_counts(h, 0)
    new = [i for i in ids1 if i not in ids0]
    chk('natural[v36]  #82 event 7 = CREATE #447 (12,b,32,fe): consumer matched once; spawn list 1466(A5) drained back to 0', hits.get(0xfe24) == 1 and r.w(A5 + 1466) == 0, hits)
    chk('natural[v36]  #82: exactly one new id %s joined the current room list (%d -> %d entries), counters %s -> %s' % (new, s0 // 2, s1 // 2, (c27, c28, c29), (n27, n28, n29)), len(new) == 1 and s1 == s0 + 2 and (n27, n29) == (c27 + 1, c29 + 1) and new[0] >= 900)
    if new:
        idx6 = h.rows[6][0]; e = r.l(idx6 + 4 * new[0]); addr = h.rows[6][1] + (e & 0x1ffff); nb = r.mem(addr, 32)
        sb = r.mem(h.obj(447), 32)
        chk('natural[v36]  #82: the new type-6 record #%d has #447\'s template (+6 word %s), its own id (+4 = %d); placed at (%d,%d,%d) vs requested (18,11,50), room byte %d' % (new[0], nb[6:8].hex(), int.from_bytes(nb[4:6], 'big'), nb[0], nb[1], nb[2], nb[10]),
            nb[6:8] == sb[6:8] and int.from_bytes(nb[4:6], 'big') == new[0] and (e >> 16) == size6(h, 447) and nb[10] == 0)
    h.close()
    # ---------------- natural: #207 event 5 = HIDE 206, 208, 209; PLACE #203 -> room $15 (30,1f,4b); PLACE #204 -> room $15 (28,17,4e); 42 [0 2]
    h = H(SNAP0); r = h.r
    f0 = {o: r.b(h.obj(o) + 3) for o in (206, 208, 209)}
    df, hits = inject_run(h, 207, 5, 0)
    f1 = {o: r.b(h.obj(o) + 3) for o in (206, 208, 209)}
    chk('natural[v26,41,42]  #207 event 5: consumer matched once', hits.get(0xfe24) == 1, hits)
    chk('natural[v26]  #207: HIDE x3: flags %s -> %s (bit 7 set)' % (f0, f1), all(f1[o] == f0[o] | 0x80 for o in f0))
    p203 = r.mem(h.obj(203), 12); p204 = r.mem(h.obj(204), 12)
    chk('natural[v41]  #207: PLACE #203 -> room %02x (%d,%d,%d) and #204 -> room %02x (%d,%d,%d)' % (p203[10], p203[0], p203[1], p203[2], p204[10], p204[0], p204[1], p204[2]),
        (p203[10], p203[0], p203[1], p203[2]) == (0x15, 0x30, 0x1f, 0x4b) and (p204[10], p204[0], p204[1], p204[2]) == (0x15, 0x28, 0x17, 0x4e))
    chk('natural[v42]  #207: verb 42 [0 2]: 2462(A5) = %d, 2461(A5) = %d' % (r.b(A5 + 2462), r.b(A5 + 2461)), r.b(A5 + 2462) == 0 and r.b(A5 + 2461) in (2, 1))
    h.close()
    # ---------------- natural: #194 event 5 = MOVE (first operand actor = #194) -> #167 moves to #194's position and room
    h = H(SNAP0); r = h.r
    p194 = r.mem(h.obj(194), 3); rm194 = r.b(h.obj(194) + 10); p167_0 = r.mem(h.obj(167), 3); rm167_0 = r.b(h.obj(167) + 10)
    df, hits = inject_run(h, 194, 5, 0)
    p167 = r.mem(h.obj(167), 3); rm167 = r.b(h.obj(167) + 10)
    chk('natural[v73]  #194 event 5 (73 actor #167): #167 moves from room $%02x %s to room $%02x %s; #194 is at room $%02x %s' % (rm167_0, tuple(p167_0), rm167, tuple(p167), rm194, tuple(p194)),
        hits.get(0xfe24) == 1 and rm167 == rm194 and tuple(p167) == tuple(p194), hits)
    h.close()
    # ---------------- natural: #193 event 16 = `44 actor #448 6 fe`, `73 actor #163`, `12 actor`
    noise = noise_for(SNAP0)
    h = H(SNAP0); r = h.r
    a193 = h.obj(193); p193 = tuple(r.mem(a193, 3)); rm193 = r.b(a193 + 10); m193 = a193 + r.b(a193 + 13); mv0 = r.b(m193)
    p163 = tuple(r.mem(h.obj(163), 3)); rm163 = r.b(h.obj(163) + 10)
    ids0, s0, _ = t5_list(h, 0)
    df, hits = inject_run(h, 193, 16, 0, steps=250000)
    ids1, s1, _ = t5_list(h, 0); new = [i for i in ids1 if i not in ids0]
    chk('natural[v12,44,73]  #193 event 16: consumer matched once, spawn list drained (1466(A5) = %d)' % r.w(A5 + 1466), hits.get(0xfe24) == 1 and r.w(A5 + 1466) == 0, hits)
    chk('natural[v12]  #193: STOPMOVE actor: mover byte $%02x -> $%02x' % (mv0, r.b(m193)), r.b(m193) == 1)
    chk('natural[v73]  #193: `73 actor #163`: #163 moved from room $%02x %s to room $%02x %s (#193 is at room $%02x %s)' % (rm163, p163, r.b(h.obj(163) + 10), tuple(r.mem(h.obj(163), 3)), rm193, p193),
        r.b(h.obj(163) + 10) == rm193 and tuple(r.mem(h.obj(163), 3)) == p193)
    if len(new) == 1:
        idx6 = h.rows[6][0]; e = r.l(idx6 + 4 * new[0]); ad = h.rows[6][1] + (e & 0x1ffff); nb = r.mem(ad, 16)
        chk('natural[v44]  #193: `44 actor #448 6 fe` created object #%d in the current room: template word %s (#448: %s), placed at (%d,%d,%d) near #193\'s (%d,%d,%d)' % (new[0], nb[6:8].hex(), r.mem(h.obj(448) + 6, 2).hex(), nb[0], nb[1], nb[2], *p193),
            nb[6:8] == r.mem(h.obj(448) + 6, 2) and nb[10] == 0, nb.hex())
    else:
        chk('natural[v44]  #193: exactly one new object joined the current room list', False, new)
    h.close()
    # ---------------- natural: verb 42's countdown.  #207 event 5 arms 2462(A5) = 0, 2461(A5) = 2; the timer service $009094 decrements 2461 once per tick;
    # at 0 it sets 2462 := $ff and queues $4014 (event 20 on the room record) with the word 2462 held
    h = H(SNAP0); r = h.r
    inject5(h, 207, 0, 5)
    hh = r.hits(150000, 0xfe24)
    v = (r.b(A5 + 2462), r.b(A5 + 2461))
    hh = r.hits(1200000, 0x90c2, 0x90dc)
    chk('natural[v42]  #207 event 5 armed (2462,2461) = %s; over the next 1.2M steps the tick service reached the expiry $0090c2 %d time(s) and queued $4014 ($0090dc %d); now 2462(A5) = $%02x, 2461(A5) = %d' % (v, hh.get(0x90c2, 0), hh.get(0x90dc, 0), r.b(A5 + 2462), r.b(A5 + 2461)),
        v[0] == 0 and v[1] in (2, 1) and hh.get(0x90c2) == 1 and hh.get(0x90dc) == 1 and r.b(A5 + 2462) == 0xff and r.b(A5 + 2461) == 0)
    h.close()

if __name__ == '__main__':
    run(); print('ok %d bad %d' % (lib2.OK, lib2.BAD))
