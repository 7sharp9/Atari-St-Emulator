"""Section 8: the other read-not-run verbs whose handler is a one-field write: 7 8 16-21 24 25 30-33 43 47 49 50 53 54 55 57 67 68 69 74 75 76 77 78 80 82 89 92 93"""
from lib2 import *
import lib2

def run():
    h = H(SNAP0); r = h.r
    def tracked(d):
        """all record/table bytes (type 4/6/8/9 data) plus A5 bytes the call changed, as {addr: new}"""
        st = {}
        for a, (o, n) in d['delta'].items():
            w = h.where(a)
            if w.startswith(('t6/', 't4/', 't8/', 't9/', '(A5)')): st[a] = n
        return st
    def case(v, script, exp, label, pre=(), extra_ok=True, want_ret=True):
        for addr, data in pre: h.poke(addr, data)
        d = h.call(v, script)
        got = tracked(d)
        okv = d['ret'] == want_ret and (d['da1'] == len(script) if want_ret else True)
        okv = okv and all(afterb(h, d, a) == x for a, x in exp.items())
        extra = {a: x for a, x in got.items() if a not in exp}
        chk('verb %2d %s' % (v, label), okv and (extra_ok or not extra), (d['thrown'][:1], {hex(a): x for a, x in extra.items()}) if not okv else '')
        return d
    rec = h.obj; sb = lambda o: rec(o) + r.b(rec(o) + 12)      # first sub-block (ext12)
    # ---- state bits +3 of the record
    o = 16; a = rec(o); f = r.b(a + 3)
    case(17, [0, o], {a + 3: f | 1}, '#16 state bit 0 = 1 (flags $%02x -> $%02x)' % (f, f | 1), extra_ok=False)
    case(18, [0, o], {a + 3: f & ~1}, '#16 state bit 0 = 0', pre=[(a + 3, [f | 1])], extra_ok=False)
    case(24, [0, o], {a + 3: f ^ 1}, '#16 state bit 0 ^= 1', pre=[(a + 3, [f])], extra_ok=False)
    case(20, [0, o], {a + 3: f | 2}, '#16 state bit 1 = 1', pre=[(a + 3, [f])], extra_ok=False)
    case(21, [0, o], {a + 3: f & ~2}, '#16 state bit 1 = 0', pre=[(a + 3, [f | 2])], extra_ok=False)
    case(25, [0, o], {a + 3: f ^ 2}, '#16 state bit 1 ^= 1', pre=[(a + 3, [f])], extra_ok=False)
    h.poke(a + 3, [f])
    for v, bit, name in ((16, 1, 'bit 0'), (19, 2, 'bit 1')):
        for val, want in ((f | bit, 1), (f & ~bit, 0)):
            h.poke(a + 3, [val]); h.poke(A5 + 2270, [0 if want else 7]); d = h.call(v, [0, o])
            chk('verb %2d COND #16 state %s %s: 2270(A5) -> %d' % (v, name, 'set' if want else 'clear', afterb(h, d, A5 + 2270)), d['ret'] and afterb(h, d, A5 + 2270) == want and d['da1'] == 2)
    h.poke(a + 3, [f])
    # ---- current-object versions (348(A5) -> #16)
    h.poke(A5 + 348, a.to_bytes(4, 'big'))
    case(32, [], {a + 3: f | 1}, 'current object (348(A5) -> #16) bit 0 = 1', extra_ok=False)
    case(31, [], {a + 3: f & ~1}, 'current object bit 0 = 0', pre=[(a + 3, [f | 1])], extra_ok=False)
    case(33, [], {a + 3: f ^ 1}, 'current object bit 0 ^= 1', pre=[(a + 3, [f])], extra_ok=False)
    for val, want in ((f | 1, 1), (f & ~1, 0)):
        h.poke(a + 3, [val]); h.poke(A5 + 2270, [0 if want else 7]); d = h.call(30, [])
        chk('verb 30 COND current object bit 0 %s: 2270(A5) -> %d' % ('set' if want else 'clear', afterb(h, d, A5 + 2270)), d['ret'] and afterb(h, d, A5 + 2270) == want and d['da1'] == 0)
    h.poke(a + 3, [f])
    # ---- +15 bits: LOCK/UNLOCK (bit 2), GOACTI/STOPACTI (bit 6)
    g = r.b(a + 15)
    case(54, [0, o], {a + 15: g | 4}, '#16 LOCK: record +15 bit 2 set ($%02x -> $%02x)' % (g, g | 4), pre=[(a + 15, [g])], extra_ok=False)
    case(55, [0, o], {a + 15: g & ~4}, '#16 UNLOCK: record +15 bit 2 clear', pre=[(a + 15, [g | 4])], extra_ok=False)
    case(68, [0, o], {a + 15: g | 0x40}, '#16 STOPACTI: record +15 bit 6 set', pre=[(a + 15, [g])], extra_ok=False)
    case(67, [0, o], {a + 15: g & ~0x40}, '#16 GOACTI: record +15 bit 6 clear', pre=[(a + 15, [g | 0x40])], extra_ok=False)
    h.poke(a + 15, [g])
    # ---- chest / creature sub-block fields, on #60 (sub-block at rec + rec[12])
    s60 = sb(60); base = r.mem(s60, 8)
    case(77, [0, 60], {s60 + 2: 0, s60 + 3: 0}, 'UNLOCK CHEST #60: sub-block word +2 cleared', pre=[(s60 + 2, [0x12, 0x34])], extra_ok=False)
    case(78, [0, 60], {s60 + 5: 0}, 'UNTRAP CHEST #60: sub-block byte +5 cleared', pre=[(s60 + 5, [0x77])], extra_ok=False)
    case(92, [0, 60], {s60: 0, s60 + 1: 0}, 'CLEAR CHEST #60: sub-block word +0 cleared', pre=[(s60, [0x56, 0x78])], extra_ok=False)
    h.poke(s60 + 3, [0x01]); case(93, [0, 60], {s60 + 3: 0x05}, 'DIRTY POTION #60: sub-block byte +3 bit 2 set ($01 -> $05)', extra_ok=False)
    h.poke(s60 + 6, [0x03]); case(89, [0, 60], {s60 + 6: 0x02}, 'UNINV #60: sub-block byte +6 bit 0 cleared ($03 -> $02)', extra_ok=False)
    h.poke(s60 + 3, [0x81]); case(53, [0, 60], {s60 + 3: 0x00}, 'REVEAL NAME #60: sub-block +3 bits 0 and 7 cleared ($81 -> $00)', extra_ok=True)
    m60 = rec(60) + r.b(rec(60) + 13)
    case(69, [0, 60, 9, 8, 7], {m60 + 3: 9, m60 + 4: 8, m60 + 5: 7}, 'MOVE #60: mover block (rec+rec[13]) bytes +3,+4,+5 := 9,8,7', extra_ok=False)
    # wake/sleep: sub-block byte +5 bit 7, and the awake-creature list 396(A5)
    h.poke(s60 + 5, [0x00]); d = h.call(75, [0, 60])
    chk('verb 75 SLEEP #60 (not in the list 396(A5)): assert (creature-list unregister $00e172 finds no entry)', bool(d['thrown']) and not d['ret'])
    r.cmd('w %x %08x' % (A5 + 396, 0x0001003c))    # list: count 1, id 60
    d = h.call(75, [0, 60])
    chk('verb 75 SLEEP #60 with 396(A5) = {count 1, id 60}: sub-block +5 bit 7 set; list count %d -> %d, id slot -> %d' % (r.w(A5 + 396), afterw(h, d, A5 + 396), afterw(h, d, A5 + 398)), d['ret'] and d['da1'] == 2 and afterb(h, d, s60 + 5) & 0x80 and afterw(h, d, A5 + 398) == 0)
    r.cmd('w %x %08x' % (A5 + 396, 0)); h.poke(s60 + 5, [0x80]); d = h.call(74, [0, 60])
    chk('verb 74 WAKE #60: sub-block +5 bit 7 cleared; list 396(A5) count %d -> %d, entry 0 -> %d' % (r.w(A5 + 396), afterw(h, d, A5 + 396), afterw(h, d, A5 + 398)), d['ret'] and d['da1'] == 2 and not afterb(h, d, s60 + 5) & 0x80 and afterw(h, d, A5 + 396) == 1 and afterw(h, d, A5 + 398) == 60)
    d = h.call(7, [0, 61])
    chk('verb 7  REGISTER id 61: 396(A5) count %d -> %d, entry 0 -> %d' % (r.w(A5 + 396), afterw(h, d, A5 + 396), afterw(h, d, A5 + 398)), d['ret'] and d['da1'] == 2 and afterw(h, d, A5 + 396) == 1 and afterw(h, d, A5 + 398) == 61)
    r.cmd('w %x %08x' % (A5 + 396, 0x0001003d)); d = h.call(8, [0, 61])
    chk('verb 8  UNREGISTER id 61 (listed): 396(A5) entry -> %d' % afterw(h, d, A5 + 398), d['ret'] and afterw(h, d, A5 + 398) == 0)
    r.cmd('w %x %08x' % (A5 + 396, 0)); d = h.call(8, [0, 61])
    chk('verb 8  UNREGISTER id 61 (not listed): assert', bool(d['thrown']) and not d['ret'])
    r.cmd('w %x %08x' % (A5 + 396, 0))
    # ---- KILL queues event 23
    q0 = r.l(A5 + 304); n0 = r.w(A5 + 1154); d = h.call(50, [0, 60]); e = after(h, d, q0, 6)
    chk('verb 50 KILL #60: ring entry %s = [opcode 23][ptr $%06x]; write ptr +8; count %d -> %d' % (e.hex(), rec(60), n0, afterw(h, d, A5 + 1154)), d['ret'] and d['da1'] == 2 and e == bytes([0, 0x17]) + rec(60).to_bytes(4, 'big') and afterl(h, d, A5 + 304) == q0 + 8 and afterw(h, d, A5 + 1154) == n0 + 1)
    # ---- conditions on objects
    for v, script, setup, want, lab in ((43, [0, 16, 0x21], (), 1, '#16 in room $21'), (43, [0, 16, 0x22], (), 0, '#16 in room $22'), (43, [0, 60, 0xfe], (), 1, '#60 in "this room" ($fe = 1166(A5) = 0)'),
                                        (47, [0, 16], (), 1, '#16 exists'), (47, [3, 0xde], (), 0, 'id 990 does not exist'),
                                        (57, [0, 5], ((A5 + 1262, [0, 5]),), 1, 'selected object 1262(A5) == 5'), (57, [0, 6], ((A5 + 1262, [0, 5]),), 0, 'selected 1262(A5) == 6 (it is 5)'),
                                        (76, [3], ((A5 + 2436, [8]),), 1, 'shield bit 3 of 2436(A5) set'), (76, [2], ((A5 + 2436, [8]),), 0, 'shield bit 2 clear'),
                                        (80, [9], ((A5 + 2520, [9]),), 1, '2520(A5) == 9'), (80, [8], ((A5 + 2520, [9]),), 0, '2520(A5) == 8 (it is 9)')):
        for addr, data in setup: h.poke(addr, data)
        h.poke(A5 + 2270, [0 if want else 7]); d = h.call(v, script)
        chk('verb %2d COND %s: 2270(A5) -> %d' % (v, lab, afterb(h, d, A5 + 2270)), d['ret'] and d['da1'] == len(script) and afterb(h, d, A5 + 2270) == want, d['thrown'][:1])
    # ---- 49 ARM TIMER n = v
    t0 = r.mem(A5 + 2307, 1)[0]
    d = h.call(49, [3, 0x28])
    chk('verb 49 ARM TIMER 3 = $28: 2311(A5) [2308+3] := $28 and its shadow 2363(A5) [2360+3] := $28; armed-count 2307(A5) %d -> %d; slot in list 2412(A5) := 3' % (t0, afterb(h, d, A5 + 2307)),
        d['ret'] and d['da1'] == 2 and afterb(h, d, A5 + 2311) == 0x28 and afterb(h, d, A5 + 2363) == 0x28 and afterb(h, d, A5 + 2307) == t0 + 1 and 3 in after(h, d, A5 + 2412, 8))
    h.poke(A5 + 2311, [0x10]); d = h.call(49, [3, 0x28])
    chk('verb 49 ARM TIMER 3 when already running ($10): re-arms to $28, armed-count unchanged', afterb(h, d, A5 + 2311) == 0x28 and afterb(h, d, A5 + 2307) == t0)
    h.close()
    # ---- 82: delete type-8 list entries whose template word == n: put #27 in the ruck then remove by template index
    lib2.noise = None
    h = H(SNAP0); r = h.r
    set_body(h, [35, 0, 27, 82, 63]); inject5(h); r.hits(300000, 0xfe24)
    chk('natural[v82,35]  scratch [35 #27, 82 63]: #27 (template 63) enters the ruck and 82 removes it again: 2438(A5) = %d' % r.b(A5 + 2438), r.b(A5 + 2438) == 0)
    h.close()
    h = H(SNAP0); r = h.r
    set_body(h, [35, 0, 27, 82, 64]); inject5(h); r.hits(300000, 0xfe24)
    chk('natural[v82]  scratch [35 #27, 82 64]: template 64 does not match, #27 stays: 2438(A5) = %d' % r.b(A5 + 2438), r.b(A5 + 2438) == 1)
    h.close()
    # ---------------- natural: the fire #485 (level 0).  event 9 (contact, gate 00 00): `76 1` shield bit test, IF msg ELSE `45 ffec` (hp -20), `50 actor` (KILL: queues event 23 for #485);
    # event 23 block: `2` DELETE current, `8 ffff` UNREGISTER actor (asserts unless #485 is in the creature list 396(A5)), `39 16 ff` (VAR 16 += $ff)
    noise = noise_for(SNAP0)
    h = H(SNAP0); r = h.r
    r.cmd('w %x %08x' % (A5 + 396, 0x000101e5))             # creature list {count 1, id 485}
    h.poke(A5 + 2436, [0])                                   # shield bit 1 clear: the ELSE part (damage) runs
    idx6 = h.rows[6][0]; e0 = r.l(idx6 + 4 * 485); hp0 = r.w(A5 + 1174); v16 = r.b(A5 + 2282 + 16)
    df, hits = inject_run(h, 485, 9, 0, steps=250000)
    e1 = r.l(idx6 + 4 * 485)
    chk('natural[v50,45,76]  #485 event 9: consumer matched twice (event 9 block, then the event-23 block queued by verb 50): %s' % hits, hits.get(0xfe24) == 2, hits)
    chk('natural[v45,76]  #485: shield bit clear -> `45 ffec`: health %d -> %d (-20)' % (hp0, r.w(A5 + 1174)), r.w(A5 + 1174) == hp0 - 20)
    chk('natural[v50,2,8,39]  #485 event 23: DELETE current (type-6 entry freed $%04x -> $%04x), UNREGISTER (396(A5) count %d, entry %d), VAR 16 %d -> %d (+$ff)' % (e0 >> 16, e1 >> 16, r.w(A5 + 396), r.w(A5 + 398), v16, r.b(A5 + 2282 + 16)),
        (e1 >> 16) == 0 and r.w(A5 + 396) == 0 and r.w(A5 + 398) == 0 and r.b(A5 + 2282 + 16) == (v16 + 0xff) & 0xff)
    h.close()

if __name__ == '__main__':
    run(); print('ok %d bad %d' % (lib2.OK, lib2.BAD))
