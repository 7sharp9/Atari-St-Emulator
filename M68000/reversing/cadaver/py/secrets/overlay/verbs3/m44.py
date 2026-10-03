"""m44.py: verb 44 ($01083e, CREATE o2 next to o1) and its two branches, plus the shared spawn-list code of verbs 36/44/84 ($0108ce-$010912).
Branch test = bit 7 of the class byte (template +22) of o2, read at $01084a.  callcap on scratch scripts for the spawn entry (1466(A5): count word, 16-byte entries
[size.w][copy ptr.l][x][y][z][room][D6.w][template ptr.l]), a labelled poke of the class byte of one template, and the live frame service $00e38c that drains the list.
Run: cd M68000 && .venv/bin/python reversing/cadaver/py/secrets/overlay/verbs3/m44.py"""
from place_lib import *
import lib2

def box_of(h, oid):
    r = h.r; a = h.obj(oid); off = int.from_bytes(r.mem(a + 8, 2), 'big')
    return list(r.mem(r.l(A5 + 56) + off, 6))     # x_hi y_hi x_lo y_lo z_hi z_lo

def predict_launch(box, nib, w16, w18):
    """$00f44a: the launch position of a class-bit-7 clone for direction nibble nib of o1's placement box"""
    xh, yh, xl, yl, zh, zl = box
    h_ = (zh - zl) & 255; z = (zl + (h_ >> 1) + ((h_ >> 1) >> 1)) & 255        # z_lo + h/2 + h/4 (byte shifts)
    t = {1: (xh, yl - 2), 2: (xh, yh + 1 + w18), 8: (xh + 1 + w16, yh), 4: (xl - 2, yh), 9: (xh + 1 + w16, yl - 1), 5: (xl - 2, yl - 2),
         6: (xl - 2, yh + 1 + w18), 10: (xh + 1 + w16, yh + 1 + w18)}
    if nib in t: x, y = t[nib]; return (x & 255, y & 255, z)
    return (255, 0, z)

def run():
    h = H(SNAP0); r = h.r
    o1 = 60; a1 = h.obj(o1); pos1 = tuple(r.mem(a1, 3)); box1 = box_of(h, o1)
    TAB = list(r.mem(0x5d2c, 14))
    def entry(d): return after(h, d, A5 + 1468, 16)
    def fields(e): return dict(size=int.from_bytes(e[0:2], 'big'), ptr=int.from_bytes(e[2:6], 'big'), pos=tuple(e[6:9]), room=e[9], d6=int.from_bytes(e[10:12], 'big'), tmpl=int.from_bytes(e[12:16], 'big'))
    def tmpl_of(oid): a = h.obj(oid); return h.res(2, int.from_bytes(h.ram[a + 6:a + 8], 'big'))
    o_plain, o_cls = 448, 463
    tp, tc = tmpl_of(o_plain), tmpl_of(o_cls)
    chk('verb 44 operands: o2 #%d template class byte %02x (bit 7 clear), o2 #%d class byte %02x (bit 7 set); o1 #%d at %s, placement box [x_hi y_hi x_lo y_lo z_hi z_lo] %s' % (o_plain, h.ram[tp + 22], o_cls, h.ram[tc + 22], o1, pos1, box1), h.ram[tp + 22] & 0x80 == 0 and h.ram[tc + 22] & 0x80 != 0)
    # ---- branch B (class bit 7 clear)
    for b1 in range(14):
        d = h.call(44, [0, o1, o_plain >> 8, o_plain & 255, b1, 0xfe]); f = fields(entry(d))
        chk('verb 44 branch B (#%d, bit 7 clear) slot %2d: consumes 6 bytes, count 1466(A5) 0 -> %d, entry position %s = o1\'s %s, room byte $%02x = operand, D6 field $%02x = table $5d2c[%d] = $%02x, template ptr $%x = o2\'s' % (o_plain, b1, afterw(h, d, A5 + 1466), f['pos'], pos1, f['room'], f['d6'], b1, TAB[b1], f['tmpl']),
            d['ret'] and d['da1'] == 6 and afterw(h, d, A5 + 1466) == 1 and f['pos'] == pos1 and f['room'] == 0xfe and f['d6'] == TAB[b1] and f['tmpl'] == tp and f['size'] > 0)
    # the copy record: a type-9 copy of o2's record (size = o2 record size), id in 2120(A5)
    d = h.call(44, [0, o1, o_plain >> 8, o_plain & 255, 2, 0xfe]); f = fields(entry(d))
    cp = after(h, d, f['ptr'], f['size'])
    src = r.mem(h.obj(o_plain), f['size'])
    chk('verb 44 B: the entry\'s copy record ($%x, %d bytes) is a copy of o2\'s record except the id word: %d of %d bytes equal; 2120(A5) -> %d (the type-9 id)' % (f['ptr'], f['size'], sum(a == b for a, b in zip(cp, src)), f['size'], afterw(h, d, A5 + 2120)),
        sum(a == b for a, b in zip(cp, src)) >= f['size'] - 2)
    # ---- room operand
    for rb in (0x21, 0xfe, 0):
        d = h.call(44, [0, o1, o_plain >> 8, o_plain & 255, 2, rb]); f = fields(entry(d))
        chk('verb 44 B: 4th operand byte $%02x -> entry room byte $%02x (the byte is a ROOM, $fe = this room, not a facing)' % (rb, f['room']), f['room'] == rb)
    # ---- o1 with bit 7 of record +10 set: the hero's record is the origin
    hero = r.l(A5 + 160); hp = tuple(r.mem(hero, 3))
    h.poke(a1 + 10, [0x80]); d = h.call(44, [0, o1, o_plain >> 8, o_plain & 255, 2, 0xfe]); f = fields(entry(d)); h.poke(a1 + 10, [0])
    chk('verb 44 B with o1 record +10 = $80 (bit 7): position %s = the hero record 160(A5) %s' % (f['pos'], hp), f['pos'] == hp)
    # ---- branch A (class bit 7 set): launch positions by direction nibble
    w16, w18 = r.w(tc + 16), r.w(tc + 18)
    nok = 0
    for b1 in range(15):
        d = h.call(44, [0, o1, o_cls >> 8, o_cls & 255, b1, 0xfe]); f = fields(entry(d))
        pred = predict_launch(box1, b1 & 15, w16, w18) if b1 else pos1
        chk('verb 44 branch A (#%d, class $%02x, extents w16 %d w18 %d) direction %2d: entry position %s (predicted %s from o1\'s box), D6 field %d = the raw operand, room $%02x, template ptr $%x' % (o_cls, h.ram[tc + 22], w16, w18, b1, f['pos'], pred, f['d6'], f['room'], f['tmpl']),
            d['ret'] and d['da1'] == 6 and f['pos'] == pred and f['d6'] == b1 and f['tmpl'] == tc)
    chk('verb 44 branch A direction 15: the jump table $00f40e has 15 entries, the 16th long is $%08x (code bytes of the next routine): direction nibble 15 jumps to an odd address, undefined' % r.l(0xf40e + 60), r.l(0xf40e + 60) == 0x48e70002)
    # second o1 with a different box
    o1b = 14; boxb = box_of(h, o1b); posb = tuple(r.mem(h.obj(o1b), 3))
    for b1 in (1, 2, 4, 5, 6, 8, 9, 10, 3):
        d = h.call(44, [0, o1b, o_cls >> 8, o_cls & 255, b1, 0xfe]); f = fields(entry(d))
        pred = predict_launch(boxb, b1, w16, w18)
        chk('verb 44 branch A from #%d (box %s) direction %d: entry position %s (predicted %s)' % (o1b, boxb, b1, f['pos'], pred), f['pos'] == pred)
    # ---- override 2481..2483
    h.poke(A5 + 2481, [7, 8, 9]); d = h.call(44, [0, o1, o_cls >> 8, o_cls & 255, 2, 0xfe]); f = fields(entry(d))
    chk('verb 44 branch A with 2481..2483(A5) = (7,8,9): entry position %s = the override (the launch routine runs with D6 = 0 and leaves it alone), D6 field %d = the operand' % (f['pos'], f['d6']), f['pos'] == (7, 8, 9) and f['d6'] == 2)
    d = h.call(44, [0, o1, o_plain >> 8, o_plain & 255, 2, 0xfe]); f = fields(entry(d))
    chk('verb 44 branch B with the same override set: entry position %s = o1\'s (branch B ignores 2481..2483)' % (f['pos'],), f['pos'] == pos1)
    h.poke(A5 + 2481, [0, 0, 0])
    # ---- the class byte is the selector: flip bit 7 of o2\'s template (labelled poke) and back
    sv = h.ram[tp + 22]
    h.poke(tp + 22, [sv | 0x80]); d = h.call(44, [0, o1, o_plain >> 8, o_plain & 255, 2, 0xfe]); fa = fields(entry(d))
    h.poke(tp + 22, [sv]); d = h.call(44, [0, o1, o_plain >> 8, o_plain & 255, 2, 0xfe]); fb = fields(entry(d))
    chk('verb 44 poke: class byte of #%d\'s template $%02x -> $%02x (bit 7 set): entry position %s (branch A, predicted %s), D6 %d; restored: position %s, D6 $%02x (branch B)' % (o_plain, sv, sv | 0x80, fa['pos'], predict_launch(box1, 2, r.w(tp + 16), r.w(tp + 18)), fa['d6'], fb['pos'], fb['d6']),
        fa['pos'] == predict_launch(box1, 2, r.w(tp + 16), r.w(tp + 18)) and fa['d6'] == 2 and fb['pos'] == pos1 and fb['d6'] == TAB[2])
    h.poke(tc + 22, [h.ram[tc + 22] & 0x7f]); d = h.call(44, [0, o1, o_cls >> 8, o_cls & 255, 2, 0xfe]); fb2 = fields(entry(d))
    chk('verb 44 poke: class byte of #%d\'s template $%02x -> $%02x (bit 7 cleared): position %s = o1\'s, D6 $%02x (branch B)' % (o_cls, h.ram[tc + 22], h.ram[tc + 22] & 0x7f, fb2['pos'], fb2['d6']), fb2['pos'] == pos1 and fb2['d6'] == TAB[2])
    h.poke(tc + 22, [h.ram[tc + 22]])
    # ---- spawn list capacity
    r.cmd('w %x %08x' % (A5 + 1466, 20 << 16)); d = h.call(44, [0, o1, o_plain >> 8, o_plain & 255, 2, 0xfe])
    chk('verb 44 with 20 entries pending (1466(A5) = 20): accepted, count -> %d' % afterw(h, d, A5 + 1466), d['ret'] and afterw(h, d, A5 + 1466) == 21)
    r.cmd('w %x %08x' % (A5 + 1466, 21 << 16)); d = h.call(44, [0, o1, o_plain >> 8, o_plain & 255, 2, 0xfe])
    chk('verb 44 with 21 entries pending (1466(A5) = 21): assert "EXCEEDED ADD LIST SPACE" ($011788 entered; thrown=%s)' % (d['thrown'][:1],), bool(d['thrown']) and not d['ret'])
    r.cmd('w %x %08x' % (A5 + 1466, 0))
    h.close()

    # ---- live: the frame service $00e38c drains the entry.  Branch B (class bit 7 clear) calls the search $008e38 (D6 forced to $3f at $00e48e) unless the D6 field has bit 7
    # ($ff, slot 12); branch A (bit 7 set) never calls it and goes through the launch routine $008870 ($00e3fa).  $008870 is also a collision test the game calls itself,
    # so counts are compared with a control run of the same length.  The position handed to $00c24e (D0-D2, room D4) is read at its entry.
    def live(o2, b1, room=0xfe, inject=True):
        h = H(SNAP0); r = h.r; h.owner = 2
        idx, dat, cnt = h.rows[6]; before = set(i for i in range(cnt) if r.l(idx + 4 * i) >> 16)
        if inject: set_body(h, [44, 0, o1, o2 >> 8, o2 & 255, b1, room]); inject5(h)
        hh = r.hits(150000, 0xe38c, 0x8870, PSEARCH, 0xc24e)
        h.close()
        h = H(SNAP0); r = h.r; h.owner = 2
        if inject: set_body(h, [44, 0, o1, o2 >> 8, o2 & 255, b1, room]); inject5(h)
        out = r.cmd('bp c24e 300000'); g = regs(out) if 'hit' in out[0].split('(')[0] + out[0] and 'gave up' not in out[0] else None
        pos = None if g is None else (g['D0'] & 255, g['D1'] & 255, g['D2'] & 255, g['D4'] & 255)
        a = h.obj(o1); h.close()
        return hh, pos
    ctl, _ = live(o_plain, 2, inject=False)
    print('   control (no injection) hits:', {hex(k): v for k, v in ctl.items()})
    hh, pos = live(o_plain, 2)
    chk('live[v44] branch B (#448, slot 2): drain ran, search $008e38 entered %d (control %d), $c24e entered with (x,y,z,room) %s = o1 %s moved by the search' % (hh.get(PSEARCH, 0), ctl.get(PSEARCH, 0), pos, pos1),
        hh.get(PSEARCH, 0) - ctl.get(PSEARCH, 0) == 1 and pos is not None and pos[3] == 0)
    hh, pos = live(o_plain, 12)
    chk('live[v44] branch B slot 12 (D6 field $ff, bit 7): search entered %d (control %d), $c24e entered with %s: the exact o1 position %s, no search' % (hh.get(PSEARCH, 0), ctl.get(PSEARCH, 0), pos, pos1),
        hh.get(PSEARCH, 0) == ctl.get(PSEARCH, 0) and pos is not None and pos[:3] == pos1)
    hh, pos = live(o_cls, 8)
    chk('live[v44] branch A (#463, direction 8): search entered %d (control %d), launch routine $008870 entered %d (control %d), $c24e entered %d times with (x,y,z,room) %s (entry position predicted %s)' % (
        hh.get(PSEARCH, 0), ctl.get(PSEARCH, 0), hh.get(0x8870, 0), ctl.get(0x8870, 0), hh.get(0xc24e, 0), pos, predict_launch(box1, 8, w16, w18)),
        hh.get(PSEARCH, 0) == ctl.get(PSEARCH, 0) and hh.get(0x8870, 0) > ctl.get(0x8870, 0) and hh.get(0xc24e, 0) == 1)
    hh, pos = live(o_cls, 3)
    chk('live[v44] branch A with the invalid direction 3 (launch routine returns D0 = -1): $c24e entered %d times (no clone is created)' % hh.get(0xc24e, 0), hh.get(0xc24e, 0) == 0)
    hh, pos = live(o_plain, 2, room=0x21)
    chk('live[v44] branch B with room operand $21: $c24e entered with room byte %s (the clone goes to room $21, not searched in this room: search entered %d, control %d)' % (None if pos is None else hex(pos[3]), hh.get(PSEARCH, 0), ctl.get(PSEARCH, 0)),
        pos is not None and pos[3] == 0x21 and hh.get(PSEARCH, 0) == ctl.get(PSEARCH, 0))

if __name__ == '__main__':
    run(); print('ok %d bad %d' % (lib2.OK, lib2.BAD))
    print('per-verb evidence (ok/bad):', ', '.join('%d: %d/%d' % (v, c[0], c[1]) for v, c in sorted(lib2.TALLY.items())))
