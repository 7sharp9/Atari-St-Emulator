"""m56.py: verb 56 ($010d5c, COND object in box) measured by callcap on a scratch script (every face, the room byte, signed byte compare, template offsets,
a missing object) and inside the live game through the consumer $00fdbc (IF block); prints `<label> ok|BAD` and per-verb tallies.
Run: cd M68000 && .venv/bin/python reversing/cadaver/py/secrets/overlay/verbs3/m56.py"""
from lib2 import *
import lib2, re

OID = 60            # level-0 object in room 0 (CAVERN)

def box_call(h, oid, room, x0, x1, y0, y1, z0, z1):
    h.poke(A5 + 2270, [0])
    d = h.call(56, [oid >> 8, oid & 255, room, x0, x1, y0, y1, z0, z1])
    ok = d['ret'] and d['da1'] == 9
    return ok, afterb(h, d, A5 + 2270), d

def run():
    h = H(SNAP0); r = h.r
    a = h.obj(OID); ta = h.res(2, int.from_bytes(h.ram[a + 6:a + 8], 'big'))
    saved_t = r.mem(ta, 24)
    def setpos(x, y, z, room=0): h.poke(a, [x, y, z]); h.poke(a + 10, [room])
    def setadj(ax=0, ay=0, az=0):
        # adj x = w4*8 + w16, adj y = w6*8 + w18, adj z = w20 (template words); poked as w16/w18/w20 only, w4 = w6 = 0
        h.poke(ta + 4, [0, 0]); h.poke(ta + 6, [0, 0]); h.poke(ta + 16, [ax >> 8, ax & 255]); h.poke(ta + 18, [ay >> 8, ay & 255]); h.poke(ta + 20, [az >> 8, az & 255])
    chk('verb 56 setup: object #%d record %s, template words +4 %d +6 %d +16 %d +18 %d +20 %d (adj x = w4*8+w16, adj y = w6*8+w18, adj z = w20)' % (
        OID, r.mem(a, 12).hex(), r.w(ta + 4), r.w(ta + 6), r.w(ta + 16), r.w(ta + 18), r.w(ta + 20)), True)
    # ---------- with zero template offsets
    setadj(); X, Y, Z = 20, 30, 5; setpos(X, Y, Z)
    ok, v, d = box_call(h, OID, 0, 10, 30, 20, 40, 0, 10)
    chk('verb 56 [#60 room0 box x10..30 y20..40 z0..10] object (20,30,5): consumes 9 bytes, 2270(A5) 0 -> %d (true), delta addresses %s' % (v, sorted(hex(x) for x in d['delta'])), ok and v == 1 and set(d['delta']) <= {A5 + 2270}, d['thrown'])
    ok, v, d = box_call(h, OID, 0, 10, 30, 20, 40, 0, 10)
    h.poke(A5 + 2270, [7]); d = h.call(56, [0, OID, 0, 99, 100, 20, 40, 0, 10])
    chk('verb 56 false case clears 2270(A5) 7 -> %d (x0 = 99 > x 20), consumes 9 bytes' % afterb(h, d, A5 + 2270), d['ret'] and d['da1'] == 9 and afterb(h, d, A5 + 2270) == 0)
    # x faces: operand byte 0 = x0 (raw x >= x0), byte 1 = x1 (adjusted x < x1)
    for lab, args, want in (
        ('x0 = x (20)', (20, 30, 20, 40, 0, 10), 1), ('x0 = x + 1', (21, 30, 20, 40, 0, 10), 0),
        ('x1 = x + 1 (exclusive upper)', (10, 21, 20, 40, 0, 10), 1), ('x1 = x', (10, 20, 20, 40, 0, 10), 0),
        ('y0 = y (30)', (10, 30, 30, 40, 0, 10), 1), ('y0 = y + 1', (10, 30, 31, 40, 0, 10), 0),
        ('y1 = y + 1 (exclusive upper)', (10, 30, 20, 31, 0, 10), 1), ('y1 = y', (10, 30, 20, 30, 0, 10), 0),
        ('z0 = z (5)', (10, 30, 20, 40, 5, 10), 1), ('z0 = z + 1', (10, 30, 20, 40, 6, 10), 0),
        ('z1 = z (inclusive upper)', (10, 30, 20, 40, 0, 5), 1), ('z1 = z - 1', (10, 30, 20, 40, 0, 4), 0)):
        # the x1 cases need x1 > x0 only formally: the handler does not check ordering
        ok, v, d = box_call(h, OID, 0, *args)
        chk('verb 56 face %-30s box %s object (%d,%d,%d), zero template offsets: 2270(A5) -> %d (want %d)' % (lab, list(args), X, Y, Z, v, want), ok and v == want)
    # ---------- the object far outside on each axis, and the operand order x0 x1 y0 y1 z0 z1 (not x0 y0 z0 x1 y1 z1)
    for lab, args, want in (('x far below', (30, 40, 20, 40, 0, 10), 0), ('x far above', (0, 10, 20, 40, 0, 10), 0), ('y far below', (10, 30, 35, 45, 0, 10), 0), ('y far above', (10, 30, 0, 10, 0, 10), 0),
                            ('z below', (10, 30, 20, 40, 8, 12), 0), ('z above', (10, 30, 20, 40, 0, 3), 0),
                            ('order check: (x0,y0,z0,x1,y1,z1) = (10,20,0,30,40,10) read as x0 x1 y0 y1 z0 z1 = x 10..20, y 30..40 -> false', (10, 20, 30, 40, 0, 10), 0)):
        ok, v, d = box_call(h, OID, 0, *args); chk('verb 56 %-32s box %s: 2270(A5) -> %d (want %d)' % (lab, list(args), v, want), ok and v == want)
    # ---------- room byte
    ok, v, d = box_call(h, OID, 1, 10, 30, 20, 40, 0, 10)
    chk('verb 56 room byte 1 vs record +10 = 0: false (box would contain the object): 2270(A5) -> %d' % v, ok and v == 0)
    ok, v, d = box_call(h, OID, 0xfe, 10, 30, 20, 40, 0, 10)
    chk('verb 56 room byte $fe is NOT special-cased: record +10 = 0 (this room is 0, 1166(A5) = %d) -> false, 2270(A5) -> %d' % (r.w(A5 + 1166), v), ok and v == 0)
    setpos(X, Y, Z, 5)
    ok, v, d = box_call(h, OID, 5, 10, 30, 20, 40, 0, 10)
    chk('verb 56 object with record +10 = 5 (another room), operand room 5: true: 2270(A5) -> %d' % v, ok and v == 1)
    ok, v, d = box_call(h, OID, 0, 10, 30, 20, 40, 0, 10)
    chk('verb 56 object with record +10 = 5, operand room 0 (this room): false: 2270(A5) -> %d' % v, ok and v == 0)
    ok, v, d = box_call(h, OID, 6, 10, 30, 20, 40, 0, 10)
    chk('verb 56 object with record +10 = 5, operand room 6: false: 2270(A5) -> %d' % v, ok and v == 0)
    setpos(X, Y, Z, 0)
    # ---------- signed byte compares
    setpos(0x90, Y, Z)
    for lab, args, want in (('x = $90: x0 = $80 (signed -112 >= -128)', (0x80, 0xa0, 20, 40, 0, 10), 1), ('x = $90: x0 = $7f (-112 < 127: false)', (0x7f, 0xa0, 20, 40, 0, 10), 0),
                            ('x = $90: x1 = $7f (-112 >= 127 is false, passes)', (0x80, 0x7f, 20, 40, 0, 10), 1), ('x = $90: x1 = $90 (equal: fails)', (0x80, 0x90, 20, 40, 0, 10), 0)):
        ok, v, d = box_call(h, OID, 0, *args); chk('verb 56 signed byte: %-52s 2270(A5) -> %d (want %d)' % (lab, v, want), ok and v == want)
    setpos(X, 0x90, Z)
    for lab, args, want in (('y = $90: y0 = $80', (10, 30, 0x80, 0xa0, 0, 10), 1), ('y = $90: y0 = $7f', (10, 30, 0x7f, 0xa0, 0, 10), 0), ('y = $90: y1 = $7f (passes)', (10, 30, 0x80, 0x7f, 0, 10), 1)):
        ok, v, d = box_call(h, OID, 0, *args); chk('verb 56 signed byte: %-52s 2270(A5) -> %d (want %d)' % (lab, v, want), ok and v == want)
    setpos(X, Y, 0x90)
    for lab, args, want in (('z = $90: z1 = $7f (-112 > 127 false, passes)', (10, 30, 20, 40, 0x80, 0x7f), 1), ('z = $90: z1 = $80 (-112 > -128 true, fails)', (10, 30, 20, 40, 0x80, 0x80), 0)):
        ok, v, d = box_call(h, OID, 0, *args); chk('verb 56 signed byte: %-52s 2270(A5) -> %d (want %d)' % (lab, v, want), ok and v == want)
    setpos(X, Y, Z)
    # ---------- template offsets: x1 and y1 compare x - (w4*8 + w16), y - (w6*8+w18) ; z0 compares z + w20; the lower x0, y0 and upper z1 compare the raw values
    setadj(14, 0, 0)    # adjusted x = 20 - 14 = 6
    for lab, args, want in (('adj x = 6: x1 = 7', (10, 7, 20, 40, 0, 10), 1), ('adj x = 6: x1 = 6', (10, 6, 20, 40, 0, 10), 0), ('adj x = 6: x1 = 30 but x0 = 21 (raw lower bound)', (21, 30, 20, 40, 0, 10), 0), ('adj x = 6: x0 = 20 (raw)', (20, 30, 20, 40, 0, 10), 1)):
        ok, v, d = box_call(h, OID, 0, *args); chk('verb 56 template w16 = 14: %-50s box %s: 2270(A5) -> %d (want %d)' % (lab, list(args), v, want), ok and v == want)
    setadj(0, 15, 0)    # adjusted y = 30 - 15 = 15
    for lab, args, want in (('adj y = 15: y1 = 16', (10, 30, 20, 16, 0, 10), 1), ('adj y = 15: y1 = 15', (10, 30, 20, 15, 0, 10), 0), ('adj y = 15: y0 = 30 (raw lower)', (10, 30, 30, 40, 0, 10), 1), ('adj y = 15: y0 = 31', (10, 30, 31, 40, 0, 10), 0)):
        ok, v, d = box_call(h, OID, 0, *args); chk('verb 56 template w18 = 15: %-50s box %s: 2270(A5) -> %d (want %d)' % (lab, list(args), v, want), ok and v == want)
    setadj(0, 0, 10)    # adjusted z = 5 + 10 = 15
    for lab, args, want in (('adj z = 15: z0 = 15', (10, 30, 20, 40, 15, 20), 1), ('adj z = 15: z0 = 16', (10, 30, 20, 40, 16, 20), 0), ('adj z = 15: z1 = 5 (raw z, inclusive)', (10, 30, 20, 40, 15, 5), 1), ('adj z = 15: z1 = 4', (10, 30, 20, 40, 15, 4), 0)):
        ok, v, d = box_call(h, OID, 0, *args); chk('verb 56 template w20 = 10: %-50s box %s: 2270(A5) -> %d (want %d)' % (lab, list(args), v, want), ok and v == want)
    # w4 and w6 count in units of 8
    h.poke(ta + 4, [0, 1]); h.poke(ta + 16, [0, 6]); h.poke(ta + 20, [0, 0])     # adj x = 1*8 + 6 = 14
    ok, v, d = box_call(h, OID, 0, 10, 7, 20, 40, 0, 10); ok2, v2, d2 = box_call(h, OID, 0, 10, 6, 20, 40, 0, 10)
    chk('verb 56 template w4 = 1 (8 units) + w16 = 6: adj x = 6, x1 = 7 -> %d, x1 = 6 -> %d (want 1, 0)' % (v, v2), ok and ok2 and v == 1 and v2 == 0)
    h.poke(ta + 4, [0, 0]); h.poke(ta + 16, [0, 0]); h.poke(ta + 6, [0, 2]); h.poke(ta + 18, [0, 1])    # adj y = 2*8 + 1 = 17 -> 13
    ok, v, d = box_call(h, OID, 0, 10, 30, 20, 14, 0, 10); ok2, v2, d2 = box_call(h, OID, 0, 10, 30, 20, 13, 0, 10)
    chk('verb 56 template w6 = 2 (8 units) + w18 = 1: adj y = 13, y1 = 14 -> %d, y1 = 13 -> %d (want 1, 0)' % (v, v2), ok and ok2 and v == 1 and v2 == 0)
    h.poke(ta, saved_t)
    # real template restored
    chk('verb 56 template restored to its snapshot bytes', r.mem(ta, 24) == saved_t)
    # ---------- the template offsets really are the ones in the live template of #60 (no poke)
    ax = r.w(ta + 4) * 8 + r.w(ta + 16); ay = r.w(ta + 6) * 8 + r.w(ta + 18); az = r.w(ta + 20)
    setpos(0x40, 0x40, 3); axw, ayw = (0x40 - ax), (0x40 - ay)
    ok, v, d = box_call(h, OID, 0, 0x40, (axw + 1) & 255, 0x40, (ayw + 1) & 255, (3 + az) & 255, 3)
    ok2, v2, d2 = box_call(h, OID, 0, 0x40, axw & 255, 0x40, (ayw + 1) & 255, (3 + az) & 255, 3)
    ok3, v3, d3 = box_call(h, OID, 0, 0x40, (axw + 1) & 255, 0x40, ayw & 255, (3 + az) & 255, 3)
    ok4, v4, d4 = box_call(h, OID, 0, 0x40, (axw + 1) & 255, 0x40, (ayw + 1) & 255, (4 + az) & 255, 3)
    chk('verb 56 live template of #60 (adj x -%d, y -%d, z +%d): a box tight on every adjusted face is true (%d), one off on x1 / y1 / z0 is false (%d %d %d)' % (ax, ay, az, v, v2, v3, v4),
        ok and ok2 and ok3 and ok4 and v == 1 and v2 == 0 and v3 == 0 and v4 == 0)
    # ---------- missing object and the running object
    setadj(); setpos(X, Y, Z)
    dat6 = h.rows[6][1]
    # a missing id resolves ($00c542 -> $00c5ac) to the index entry's offset 0 = the first byte of the type-6 data, and verb 56 does not test the Z flag of $010738
    idx6, _, cnt6 = h.rows[6]
    miss = [i for i in range(cnt6) if (r.l(idx6 + 4 * i) >> 16) == 0][0]       # an unused slot of the type-6 index (size 0)
    mh, ml = miss >> 8, miss & 255
    ent = r.l(idx6 + 4 * miss); dat6 = dat6 + (ent & 0xffff); sv = r.mem(dat6, 12)    # $00c5ac: A0 = data base + the entry's low word, whatever its size field
    h.poke(dat6, [20, 30, 5, 0, 0, 0, 0, 27, 0, 0, 0, 0])      # x y z, template index 27 (= #60's) at +6, room 0 at +10
    h.poke(A5 + 2270, [0]); d = h.call(56, [mh, ml, 0, 10, 30, 20, 40, 0, 10])
    chk('verb 56 object id %d (unused index slot): no assert, ret=%s thrown=%s, consumes 9; A0 = type-6 data base + the empty entry low word = $%x: box test reads those bytes (poked 20,30,5 room 0): 2270(A5) -> %d (want 1)' % (miss, d['ret'], d['thrown'][:1], dat6, afterb(h, d, A5 + 2270)), d['ret'] and d['da1'] == 9 and not d['thrown'] and afterb(h, d, A5 + 2270) == 1)
    h.poke(dat6, [90, 30, 5, 0, 0, 0, 0, 27, 0, 0, 0, 0])
    h.poke(A5 + 2270, [0]); d = h.call(56, [mh, ml, 0, 10, 30, 20, 40, 0, 10])
    chk('verb 56 absent id with first-record x = 90 (outside): 2270(A5) -> %d (want 0)' % afterb(h, d, A5 + 2270), d['ret'] and afterb(h, d, A5 + 2270) == 0)
    h.poke(dat6, list(sv))
    sv348 = r.mem(A5 + 348, 4)
    h.poke(A5 + 348, a.to_bytes(4, 'big'))
    for box, want in (((10, 30, 20, 40, 0, 10), 1), ((10, 20, 20, 40, 0, 10), 0)):
        h.poke(A5 + 2270, [0]); d = h.call(56, [0xff, 0xff, 0] + list(box))
        chk('verb 56 object ffff (the running object, 348(A5) -> #60 at (20,30,5)) box %s: consumes 9 bytes, 2270(A5) -> %d (want %d)' % (list(box), afterb(h, d, A5 + 2270), want), d['ret'] and d['da1'] == 9 and afterb(h, d, A5 + 2270) == want)
    h.poke(A5 + 348, list(sv348))
    h.close()

    # ---------- live: IF block through the consumer
    def live(box, oid_pos, room_poke=None, label='', want=1):
        h = H(SNAP0); r = h.r; h.owner = 2
        a = h.obj(OID); ta = h.res(2, int.from_bytes(h.ram[a + 6:a + 8], 'big'))
        h.poke(ta + 4, [0, 0]); h.poke(ta + 6, [0, 0]); h.poke(ta + 16, [0, 0]); h.poke(ta + 18, [0, 0]); h.poke(ta + 20, [0, 0])
        h.poke(a, list(oid_pos))
        if room_poke is not None: h.poke(a + 10, [room_poke])
        script = [56, 0, OID] + list(box) + [14, 5, 38, 9, 1, 22]    # 56 box; IF: VAR 9 = 1; end
        h.poke(A5 + 2282 + 9, [0])
        set_body(h, script); inject5(h)
        hh = r.hits(150000, 0xfe24, 0x10d5c, 0x10630)
        v9 = r.b(A5 + 2282 + 9); pos = r.mem(a, 3)
        h.close()
        chk('live[v56]  scratch [56 #60 %s; IF VAR9 = 1] under the consumer: verb 56 handler entered %d, IF body ran %d, VAR 9 -> %d (want %d), object still at %s %s' % (list(box), hh.get(0x10d5c, 0), hh.get(0x10630, 0), v9, want, list(pos), label),
            hh.get(0x10d5c) == 1 and v9 == want and list(pos) == list(oid_pos), hh)
    live((0, 10, 30, 20, 40, 0, 10), (20, 30, 5), None, 'inside', 1)
    live((0, 10, 20, 20, 40, 0, 10), (20, 30, 5), None, 'x1 = x', 0)
    live((0, 10, 21, 20, 40, 0, 10), (20, 30, 5), None, 'x1 = x + 1', 1)
    live((0, 10, 30, 20, 40, 6, 10), (20, 30, 5), None, 'z0 = z + 1', 0)
    live((0, 10, 30, 20, 40, 0, 5), (20, 30, 5), None, 'z1 = z (inclusive)', 1)
    live((9, 10, 30, 20, 40, 0, 10), (20, 30, 5), 9, 'other room 9, operand 9', 1)
    live((0, 10, 30, 20, 40, 0, 10), (20, 30, 5), 9, 'object in room 9, operand 0', 0)

if __name__ == '__main__':
    run(); print('ok %d bad %d' % (lib2.OK, lib2.BAD))
    print('per-verb evidence (ok/bad):', ', '.join('%d: %d/%d' % (v, c[0], c[1]) for v, c in sorted(lib2.TALLY.items())))
