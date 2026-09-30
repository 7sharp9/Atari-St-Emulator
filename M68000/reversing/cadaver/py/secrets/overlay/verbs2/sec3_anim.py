"""Section 3: GOANI (3), STOPANI (4), GOMOVE (11), STOPMOVE (12)"""
from lib2 import *
import lib2

def anim_addr(h, oid): a = h.obj(oid); return a + h.r.b(a + 14)
def move_addr(h, oid): a = h.obj(oid); return a + h.r.b(a + 13)

def run():
    # ---------------- level 0: lever 144 (template +12 bit 2 = animated)
    h = H(SNAP0); r = h.r
    a144 = h.obj(144); ea = anim_addr(h, 144)
    tb = tmpl_bytes(h, 144)
    chk('verb 3/4 subject #144: template+12 = $%02x (bit 2 set), anim byte at rec+14 (+$%02x) = $%02x' % (tb[12], r.b(a144 + 14), r.b(ea)), tb[12] & 4 and r.b(a144 + 14) == 0x22)
    # GOANI acts only when the anim byte is $fe
    h.poke(ea, [0xfe]); b3 = r.b(ea + 3)
    d = h.call(3, [0, 144])
    chk('verb 3  GOANI #144 (anim byte $fe): byte -> $%02x (0), frame byte +3: %d -> %d, 380(A5) := record $%06x' % (afterb(h, d, ea), b3, afterb(h, d, ea + 3), a5l(h, 380, d)),
        d['ret'] and d['da1'] == 2 and afterb(h, d, ea) == 0 and afterb(h, d, ea + 3) == b3 + 1 and a5l(h, 380, d) == a144)
    chk('verb 3  ... 452(A5) := 56(A5) + word 8(rec) = $%06x, and the callee $b184 changed nothing else in the record' % a5l(h, 452, d), a5l(h, 452, d) == r.l(A5 + 56) + int.from_bytes(r.mem(a144 + 8, 2), 'big') and set(x[0] for x in changed(h, d, 't6/')) == {'t6/id144+34', 't6/id144+37'})
    for v in (0x00, 0xff):
        h.poke(ea, [v])
        d = h.call(3, [0, 144])
        chk('verb 3  GOANI #144 with anim byte $%02x: record untouched (only 380(A5) set)' % v, d['ret'] and changed(h, d, 't6/') == [] and a5l(h, 380, d) == a144)
    for v in (0xfe, 0x00):
        h.poke(ea, [v]); d = h.call(4, [0, 144])
        ch = sorted(x[0] for x in changed(h, d, 't6/'))
        chk('verb 4  STOPANI #144 with anim byte $%02x: byte -> $%02x, +15 bit 0 set by $b166 (%02x -> %02x)' % (v, afterb(h, d, ea), r.b(a144 + 15), afterb(h, d, a144 + 15)),
            d['ret'] and d['da1'] == 2 and afterb(h, d, ea) == 0xff and afterb(h, d, a144 + 15) == r.b(a144 + 15) | 1 and a5l(h, 380, d) == a144)
    d = h.call(3, [0, 60])
    chk('verb 3  GOANI on #60 (template+12 bit 2 clear): assert "GOANI A NONANI OBJECT"', bool(d['thrown']) and not d['ret'])
    d = h.call(4, [0, 60])
    chk('verb 4  STOPANI on #60 (not animated): assert "STOPANI A NONANI OBJECT"', bool(d['thrown']) and not d['ret'])
    d = h.call(3, [0x03, 0xde])
    chk('verb 3  GOANI on the absent id 990: assert "GOANI A NON-EXISTANT OBJECT"', bool(d['thrown']) and not d['ret'])
    d = h.call(11, [0x03, 0xde])
    chk('verb 11 GOMOVE on the absent id 990: assert', bool(d['thrown']) and not d['ret'])
    h.close()
    # ---------------- level 1: #341 (anim byte $fe, ext = fe 00 00 04), #126 (movable, state byte 01)
    h = H(SNAP1); r = h.r
    a341 = h.obj(341); e341 = anim_addr(h, 341)
    chk('level 1  #341: template+12 = $%02x, anim byte at rec+%d = $%02x, ext %s' % (tmpl_bytes(h, 341)[12], r.b(a341 + 14), r.b(e341), r.mem(e341, 4).hex()), r.b(e341) == 0xfe and tmpl_bytes(h, 341)[12] & 4)
    f3 = r.b(e341 + 3)
    d = h.call(3, [341 >> 8, 341 & 255])
    chk('verb 3  GOANI #341 (natural state $fe): -> $%02x, +3: %d -> %d' % (afterb(h, d, e341), f3, afterb(h, d, e341 + 3)), d['ret'] and afterb(h, d, e341) == 0 and afterb(h, d, e341 + 3) == f3 + 1)
    d = h.call(4, [341 >> 8, 341 & 255])
    chk('verb 4  STOPANI #341: anim byte $fe -> $%02x' % afterb(h, d, e341), d['ret'] and afterb(h, d, e341) == 0xff)
    a126 = h.obj(126); m126 = move_addr(h, 126)
    chk('level 1  #126: template+12 = $%02x (bit 0 movable), mover state byte at rec+%d = $%02x' % (tmpl_bytes(h, 126)[12], r.b(a126 + 13), r.b(m126)), tmpl_bytes(h, 126)[12] & 1 and r.b(m126) == 1)
    d = h.call(11, [0, 126])
    chk('verb 11 GOMOVE #126: mover state byte $%02x -> $%02x (0 = moving)' % (r.b(m126), afterb(h, d, m126)), d['ret'] and d['da1'] == 2 and afterb(h, d, m126) == 0 and len(changed(h, d, 't6/')) == 1)
    h.poke(m126, [4]); b1 = r.b(m126 + 1)
    d = h.call(11, [0, 126])
    chk('verb 11 GOMOVE #126 from state 4: -> 0 and the byte after it %d -> %d (+1: restart counter)' % (b1, afterb(h, d, m126 + 1)), afterb(h, d, m126) == 0 and afterb(h, d, m126 + 1) == b1 + 1)
    h.poke(m126, [0])
    d = h.call(12, [0, 126])
    chk('verb 12 STOPMOVE #126: mover state byte 0 -> $%02x (1 = stopped)' % afterb(h, d, m126), d['ret'] and d['da1'] == 2 and afterb(h, d, m126) == 1)
    d = h.call(12, [0xff, 0xff])   # actor: 348(A5) = the current object
    h.poke(A5 + 348, a126.to_bytes(4, 'big')); h.poke(m126, [0])
    d = h.call(12, [0xff, 0xff])
    chk('verb 12 STOPMOVE "actor" ($ffff) with 348(A5) -> #126: state byte -> $%02x' % afterb(h, d, m126), afterb(h, d, m126) == 1)
    d = h.call(11, [0, 60])   # object without the movable bit: assert
    t60 = tmpl_bytes(h, 60)[12] if h.obj(60) else None
    h.close()
    # ---------------- level 1 natural: object 27's event-5 block (GOANI actor, CLEAR FLAG 1) with the anim byte armed to $fe
    noise = noise_for(SNAP1)
    h = H(SNAP1); r = h.r
    e27 = anim_addr(h, 27); f27 = r.w(h.flag_rec(1) + 2)
    h.poke(e27, [0xfe]); f3 = r.b(e27 + 3)
    df, hits = inject_run(h, 27, 5, 0)
    chk('natural[v3,10]  L1 #27 event 5 (GOANI actor, CLEAR FLAG 1): consumer matched once', hits.get(0xfe24) == 1, hits)
    chk('natural[v3]  L1 #27: anim byte $fe -> $%02x, +3: %d -> %d (GOANI on the running object)' % (r.b(e27), f3, r.b(e27 + 3)), r.b(e27) == 0 and r.b(e27 + 3) == f3 + 1)
    chk('natural[v10]  L1 #27: flag 1 word %d -> %d' % (f27, r.w(h.flag_rec(1) + 2)), r.w(h.flag_rec(1) + 2) == 0)
    h.close()
    # ---------------- real scratch runs (the consumer executes the verbs): STOPANI #341, GOMOVE / STOPMOVE #126, level 1, owner #27 (6-byte body)
    for script, lab, addrf, oid, want, tag in (([4, 341 >> 8, 341 & 255], 'STOPANI #341', anim_addr, 341, 0xff, 4), ([11, 0, 126], 'GOMOVE #126', move_addr, 126, 0, 11), ([12, 0, 126], 'STOPMOVE #126', move_addr, 126, 1, 12)):
        h = H(SNAP1); r = h.r; h.owner = 27
        ad = addrf(h, oid)
        if tag == 12: h.poke(ad, [0])          # STOPMOVE needs a moving object to show anything
        b0 = r.b(ad)
        set_body(h, script); inject5(h); hh = r.hits(150000, 0xfe24)
        chk('real[v%d]  scratch %s under the consumer: byte $%02x -> $%02x (want $%02x)' % (tag, lab, b0, r.b(ad), want), hh.get(0xfe24) == 1 and r.b(ad) == want, hh)
        h.close()

if __name__ == '__main__':
    run(); print('ok %d bad %d' % (lib2.OK, lib2.BAD))
