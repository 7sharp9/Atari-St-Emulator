"""Section 2: HIDE (26) and SHOW (1)"""
from lib2 import *
import lib2

def run():
    h = H(SNAP0); r = h.r
    cur = r.w(A5 + 1166)
    def flg(o): return r.b(h.obj(o) + 3)
    def room(o): return r.b(h.obj(o) + 10)
    # ---- HIDE
    for oid in (412, 16):
        f0 = flg(oid)
        d = h.call(26, [oid >> 8, oid & 255])
        ch = [x for x in changed(h, d, 't6/')]
        chk('verb 26 HIDE #%d (room %d, flags $%02x): flags byte +3 -> $%02x (bit 7 set)' % (oid, room(oid), f0, afterb(h, d, h.obj(oid) + 3)), d['ret'] and not d['thrown'] and d['da1'] == 2 and afterb(h, d, h.obj(oid) + 3) == f0 | 0x80 and len(ch) == 1, ch)
    d = h.call(26, [0, 119])
    chk('verb 26 HIDE #119 (already hidden, flags $%02x): nothing changes (bset #7 finds it set)' % flg(119), d['ret'] and changed(h, d, 't6/') == [] and changed(h, d, '(A5)') == [])
    # ---- SHOW
    d = h.call(1, [0, 119])
    chk('verb 1  SHOW #119 (hidden $%02x, room $%02x != current %d): bit 7 cleared, bit 3 set -> $%02x' % (flg(119), room(119), cur, afterb(h, d, h.obj(119) + 3)), d['ret'] and afterb(h, d, h.obj(119) + 3) == (flg(119) & 0x7f) | 0x08 and len(d['delta']) == 1)
    d = h.call(1, [0, 16])
    chk('verb 1  SHOW #16 (not hidden): nothing changes (bclr #7 finds it clear)', d['ret'] and d['delta'] == {} and d['da1'] == 2)
    # ---- current-room object: real HIDE then SHOW through the consumer (object 2's scratch block)
    lib2.noise = noise_for(SNAP0)
    a = h.obj(412); pos0 = r.mem(a, 3).hex(); f0 = flg(412); ids0, _, _ = t5_list(h, 0)
    real(h, [26, 1, 156]); f1 = flg(412)
    chk('real[v26] HIDE #412 (in the current room): flags $%02x -> $%02x, position unchanged %s' % (f0, f1, pos0), f1 == f0 | 0x80 and r.mem(a, 3).hex() == pos0)
    real(h, [1, 1, 156]); f2 = flg(412)
    chk('real[v1,26] SHOW #412 right after: flags -> $%02x (bit 7 clear), position %s, still in room list' % (f2, r.mem(a, 3).hex()), f2 == f0 and r.mem(a, 3).hex() == pos0 and 412 in t5_list(h, 0)[0])
    h.close()
    # ---- natural: object 35's event-5 block = SHOW #119, #118, #122
    h = H(SNAP0); r = h.r
    fl0 = {o: r.b(h.obj(o) + 3) for o in (119, 118, 122)}
    df, hits = inject_run(h, 35, 5, 0)
    fl1 = {o: r.b(h.obj(o) + 3) for o in (119, 118, 122)}
    chk('natural[v1]  #35 event 5 (SHOW #119 #118 #122): consumer matched once', hits.get(0xfe24) == 1, hits)
    chk('natural[v1]  #35: flags %s -> %s (bit 7 cleared, bit 3 set on each, as the callcap on #119)' % ({k: '%02x' % v for k, v in fl0.items()}, {k: '%02x' % v for k, v in fl1.items()}),
        all(fl1[o] == (fl0[o] & 0x7f) | 0x08 and fl0[o] & 0x80 for o in fl0))
    h.close()

if __name__ == '__main__':
    run(); print('ok %d bad %d' % (lib2.OK, lib2.BAD))
