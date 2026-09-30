"""Section 5: type-4 flag verbs (10, 27, 61) and PUT IN RUCK (35)"""
from lib2 import *
import lib2, re

def first_sound_d0(flag, script_for):
    """real run of a scratch script; D0 at the first entry of the sound routine $0158f8 after the event is injected"""
    h = H(SNAP0); r = h.r
    h.poke(h.flag_rec(flag) + 2, [0, 5])
    set_body(h, script_for); inject5(h)
    out = r.cmd('bp 158f8 400000')
    m = re.search(r'D0:([0-9a-f]+)', ' '.join(out)); h.close()
    return int(m.group(1), 16) if m else None

def run():
    h = H(SNAP0); r = h.r
    room0 = h.res(3, 0); roomflags = [int.from_bytes(h.ram[room0 + 6 + 2 * i:room0 + 8 + 2 * i], 'big') for i in range(7)]
    fw = lambda n: r.w(h.flag_rec(n) + 2)
    fa = lambda n: h.flag_rec(n) + 2
    # ---------------- verb 10 CLEAR FLAG n
    chk('flag records: type 4, 4 bytes each [id?][word value at +2]; flag $33 = $%04x, flag 50 = $%04x, room 0 flag list (record+6, 7 words) = %s' % (fw(0x33), fw(50), [hex(x) for x in roomflags]), fw(0x33) == 0xffff and roomflags[:2] == [50, 59])
    d = h.call(10, [0x33])
    chk('verb 10 CLEAR FLAG $33 (was $ffff): word -> $%04x, consumes 1 byte, only that record changes' % afterw(h, d, fa(0x33)), d['ret'] and d['da1'] == 1 and afterw(h, d, fa(0x33)) == 0 and [x[0] for x in changed(h, d, 't4/')] == ['t4/id51+2', 't4/id51+3'] and changed(h, d, '(A5)') == [])
    h.poke(fa(50), [0, 5]); d = h.call(10, [50])
    chk('verb 10 CLEAR FLAG 50 (was 5): word -> %d' % afterw(h, d, fa(50)), d['ret'] and afterw(h, d, fa(50)) == 0)
    h.poke(fa(0x33), [0, 0]); d = h.call(10, [0x33])
    chk('verb 10 CLEAR FLAG $33 when already 0: no state change at all (tst.w; beq rts), no sound', d['ret'] and d['da1'] == 1 and d['delta'] == {}, len(d['delta']))
    h.poke(fa(0x33), [0xff, 0xff])
    # ---------------- verb 27 SET FLAG n = word
    d = h.call(27, [0x33, 0, 7])
    chk('verb 27 SET FLAG $33 = 7 (was $ffff): word -> %d, consumes 3 bytes' % afterw(h, d, fa(0x33)), d['ret'] and d['da1'] == 3 and afterw(h, d, fa(0x33)) == 7 and [x[0] for x in changed(h, d, 't4/')] == ['t4/id51+2', 't4/id51+3'])
    d = h.call(27, [0x33, 0xff, 0xff])
    chk('verb 27 SET FLAG $33 = $ffff when already $ffff: no change, no sound', d['ret'] and d['da1'] == 3 and d['delta'] == {})
    h.poke(fa(50), [0, 5]); d = h.call(27, [50, 0, 3])
    chk('verb 27 SET FLAG 50 = 3 (was 5): -> %d' % afterw(h, d, fa(50)), afterw(h, d, fa(50)) == 3)
    # ---------------- verb 61 COND FLAG n set
    h.poke(A5 + 2270, [0]); d = h.call(61, [0x33])
    chk('verb 61 COND FLAG $33 (= $ffff, non-zero): 2270(A5) 0 -> %d (true adds 1), consumes 1 byte' % afterb(h, d, A5 + 2270), d['ret'] and d['da1'] == 1 and afterb(h, d, A5 + 2270) == 1 and len(d['delta']) == 1)
    h.poke(fa(0x33), [0, 0]); h.poke(A5 + 2270, [7]); d = h.call(61, [0x33])
    chk('verb 61 COND FLAG $33 (= 0): 2270(A5) 7 -> %d (false clears)' % afterb(h, d, A5 + 2270), afterb(h, d, A5 + 2270) == 0)
    h.close()
    # ---------------- sound played: $12 when the flag is on the room's flag list, $2a otherwise
    for verb, ops in ((10, []), (27, [0, 9])):
        for flag in (0x33, 50, 59):
            s = first_sound_d0(flag, [verb, flag] + ops)
            want = 0x12 if flag in roomflags else 0x2a
            chk('verb %d on flag %d (in the room-0 flag list: %s): first sound after the event = $%02x' % (verb, flag, flag in roomflags, s or 0), s == want)
    # ---------------- natural: lever #144 event 5 twice.  Block: 30 (cond bit0) 14 IF[27 33 ffff, 31] ELSE[10 33, 32]
    h = H(SNAP0); r = h.r
    a = h.obj(144); fa33 = h.flag_rec(0x33) + 2
    s0, f0 = r.b(a + 3), r.w(fa33)
    inject_run(h, 144, 5, 0); s1, f1 = r.b(a + 3), r.w(fa33)
    inject_run(h, 144, 5, 0); s2, f2 = r.b(a + 3), r.w(fa33)
    chk('natural[v10,27,31,32]  lever #144 event 5, first use: state byte %02x -> %02x, flag $33 $%04x -> $%04x (ELSE part: verb 10, verb 32)' % (s0, s1, f0, f1), (s0 & 1, s1 & 1, f0, f1) == (0, 1, 0xffff, 0))
    chk('natural[v10,27,31,32]  lever #144 event 5, second use: state byte %02x -> %02x, flag $33 $%04x -> $%04x (THEN part: verb 27 = $ffff, verb 31)' % (s1, s2, f1, f2), (s1 & 1, s2 & 1, f1, f2) == (1, 0, 0, 0xffff))
    h.close()

    # ---------------- verb 35 PUT IN RUCK
    h = H(SNAP0); r = h.r
    cap = r.b(A5 + 2149) if False else r.w(A5 + 2148)
    idx8, dat8, cnt8 = h.rows[8]
    for oid in (16, 27):
        room = r.b(h.obj(oid) + 10); ids0, s0, _ = t5_list(h, room); c = room_counts(h, room); q0 = r.l(A5 + 304); n0 = r.w(A5 + 1154)
        d = h.call(35, [oid >> 8, oid & 255])
        lab = 'verb 35 PUT IN RUCK #%d (room $%02x)' % (oid, room)
        chk(lab + ': returns, consumes 2 bytes, no assert; ruck count 2438(A5) %d -> %d (capacity 2148(A5) = %d)' % (r.b(A5 + 2438), afterb(h, d, A5 + 2438), cap), d['ret'] and not d['thrown'] and d['da1'] == 2 and afterb(h, d, A5 + 2438) == 1 and cap > 1)
        tmpl_idx = int.from_bytes(h.ram[h.obj(oid) + 6:h.obj(oid) + 8], 'big')
        first = after(h, d, dat8, 4)
        chk(lab + ': type-8 list record 0 = [id %d][template idx %d] (%s)' % (int.from_bytes(first[:2], 'big'), int.from_bytes(first[2:], 'big'), first.hex()), int.from_bytes(first[:2], 'big') == oid and int.from_bytes(first[2:], 'big') == tmpl_idx)
        e0 = afterl(h, d, idx8)
        chk(lab + ': type-8 index entry 0 = $%08x (size 4)' % e0, (e0 >> 16) == 4)
        ids1, s1, _ = t5_list(h, room, d); c1 = room_counts(h, room, d)
        chk(lab + ': removed from its room list (%d -> %d), counters %s -> %s' % (s0 // 2, s1 // 2, c, c1), oid in ids0 and oid not in ids1 and c1[2] == c[2] - 1)
        qe = after(h, d, q0, 8)
        chk(lab + ': queues event 0 for the object: ring entry %s at 304(A5) (opcode 0, record $%06x), write pointer +8, count %d -> %d' % (qe.hex(), h.obj(oid), n0, afterw(h, d, A5 + 1154)),
            int.from_bytes(qe[:2], 'big') == 0 and int.from_bytes(qe[2:6], 'big') == h.obj(oid) and afterl(h, d, A5 + 304) == q0 + 8 and afterw(h, d, A5 + 1154) == n0 + 1)
        chk(lab + ': 1164(A5) = %d, 104(A5) := record $%06x' % (afterw(h, d, A5 + 1164), a5l(h, 104, d)), afterw(h, d, A5 + 1164) == oid and a5l(h, 104, d) == h.obj(oid))
    h.poke(A5 + 2438, [cap & 0xff]); d = h.call(35, [0, 16])
    chk('verb 35 with the ruck full (2438(A5) = %d = 2148(A5)): assert "PUT IN RUCK RTN. RUCK FULL"' % cap, bool(d['thrown']) and not d['ret'])
    h.poke(A5 + 2438, [0]); d = h.call(35, [0x03, 0xde])
    chk('verb 35 on the absent id 990: assert "PUT IN RUCK AN OBJECT THAT DOSNT EXIST"', bool(d['thrown']) and not d['ret'])
    h.close()
    # natural: PUT IN RUCK #27 through the consumer; the queued event 0 runs #27's own block (5 = XP += 26)
    lib2.noise = None
    h = H(SNAP0); r = h.r
    xp0 = r.l(A5 + 1192)
    set_body(h, [35, 0, 27]); q0 = r.l(A5 + 304)
    inject5(h); hh = r.hits(300000, 0xfe24, 0x10816, 0x102cc)
    xp1 = r.l(A5 + 1192)
    chk('natural[v35,5]  scratch [35 #27] under the consumer: verb 35 ran ($010816 queue push hits %s), #27\'s event-0 block ran (consumer matches %s), XP %d -> %d (+26 = verb 5)' % (hh.get(0x10816), hh.get(0xfe24), xp0, xp1), hh.get(0x10816) == 1 and hh.get(0xfe24) == 2 and hh.get(0x102cc) == 1 and xp1 == xp0 + 26, hh)
    ruck = r.mem(dat8, 4)
    chk('natural[v35]  ... the ruck holds #27 (%s), count 2438(A5) = %d' % (ruck.hex(), r.b(A5 + 2438)), int.from_bytes(ruck[:2], 'big') == 27 and r.b(A5 + 2438) == 1)
    # verb 34 sees it
    h.close()

if __name__ == '__main__':
    run(); print('ok %d bad %d' % (lib2.OK, lib2.BAD))
