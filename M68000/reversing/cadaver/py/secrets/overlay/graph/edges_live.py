"""edges_live.py: A1 (Cadaver 91st pass) live spot checks of edges of the script graph, in the real game from the lineage snapshot
(CAD_LINEAGE_SNAP, default scratchpad/cadaver/s90/run1/end_room90.snap: room 90, health 60).  Two techniques: (1) `callcap` of a verb handler on a scratch script
(h.call, the verbs2 harness) for operand layouts and branch polarity; (2) the real consumer: the event is INJECTED into the ring-304 queue
([opcode][record][word] at the write pointer, count +1) for the owning object or room, so the game's own gate and verb dispatch run the block
(nothing in the block is edited); the effect is read back from the live records.  A check is a (label, expected, observed) row; the last line
counts matches.  Not driven: the physical act that normally queues the event (icon, region overlap): those producers are the static part.
Run from M68000/:  M68000_ROOT=$PWD ATARI_NOTRACE=1 .venv/bin/python reversing/cadaver/py/secrets/overlay/graph/edges_live.py"""
import sys, os
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..', '..')))
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay/verbs2')
from h import H, A5, wb, ww
LIN = os.path.abspath(os.environ.get('CAD_LINEAGE_SNAP', ROOT + '/scratchpad/cadaver/s90/run1/end_room90.snap'))
ROWS = []

def chk(label, expected, observed):
    ok = expected == observed
    ROWS.append(ok)
    print('%-5s %-74s expected %-22s observed %s' % ('MATCH' if ok else 'DIFF', label, expected, observed), flush=True)

def live_obj(h, oid):
    """record address read through the LIVE type-6 index entry (a DELETE compacts the resource block, so H.obj(), which reads the snapshot file, goes stale:
    deleting the 16-byte GEM 716 moved the gem lock 719 down by 16 and made the second injected event land 16 bytes off)"""
    e = h.r.l(h.rows[6][0] + 4 * oid)
    return h.rows[6][1] + (e & 0x1ffff) if (e >> 17) else None

def flagw(h, n): return h.r.w(h.flag_rec(n) + 2)
def var(h, n): return h.r.b(A5 + 2282 + n)
def b3(h, oid): return h.r.b(live_obj(h, oid) + 3)
def room(h): return h.r.w(A5 + 1166)

def inject(h, target_ptr, opcode, word=0, extra=None):
    """append [opcode.w][ptr.l][word.w] (+ a 4th long when bit 15 of the opcode is set) to the ring at the write pointer 304(A5)"""
    r = h.r
    w = r.l(A5 + 304)
    r.cmd('w %x %08x' % (w, (opcode << 16) | (target_ptr >> 16)))
    r.cmd('w %x %08x' % (w + 4, ((target_ptr & 0xffff) << 16) | word))
    n = 8
    if opcode & 0x8000:
        r.cmd('w %x %08x' % (w + 8, extra or 0)); n = 12
    r.cmd('w %x %08x' % (A5 + 304, w + n))
    ww(r, A5 + 1154, r.w(A5 + 1154) + 1)

def run_event(h, oid_or_room, opcode, word=0, kind='obj', steps=200000, extra=None):
    ptr = live_obj(h, oid_or_room) if kind == 'obj' else h.res(3, oid_or_room)
    inject(h, ptr, opcode, word, extra)
    h.r.cmd('s %d' % steps)

def main():
    # ---- A: static state of the lineage snapshot (live records of the loaded game)
    h = H(LIN); r = h.r
    chk('lineage: door $79 word (type-4 record 121 +2)', 0xffff, flagw(h, 121))
    chk('lineage: door $74 word', 0xffff, flagw(h, 116))
    chk('lineage: door $67 word', 0xffff, flagw(h, 103))
    chk('lineage: door $7b (12-90) word', 0, flagw(h, 123))
    chk('lineage: object 731 hidden bit (record +3 bit 7)', 1, b3(h, 731) >> 7)
    chk('lineage: object 690 hidden bit', 1, b3(h, 690) >> 7)
    chk('lineage: rucksack count and first record (680, 93)', (1, 680, 93), (r.b(A5 + 2438), r.w(h.rows[8][1]), r.w(h.rows[8][1] + 2)))
    chk('lineage: VAR 6, 7, 13 = 1, 2, 1', (1, 2, 1), (var(h, 6), var(h, 7), var(h, 13)))
    h.close()

    # ---- B: verb handlers by callcap (operand order and branch polarity)
    h = H(LIN); r = h.r
    # verb 34 compares record word +0 (object id), not +2 (template idx): ruck holds (680, 93)
    d = h.call(34, [0x02, 0xa8]); a = d['delta']
    d34id = h.call(34, [0x02, 0xa8]); d34t = h.call(34, [0x00, 0x5d])
    def cnt2270(d):
        sp = d['sp']; v = [new for addr, (old, new) in d['delta'].items() if addr == A5 + 2270]
        return v[0] if v else 0
    d34id = h.call(34, [0x02, 0xa8]); d34t = h.call(34, [0x00, 0x5d])
    # (0x02a8 = object 680 is the record's word +0; 0x005d = 93 is the template word +2)
    chk('verb 34 operand = object id (680 in ruck record (680, 93)): counter 2270 after', 1, cnt2270(d34id))
    chk('verb 34 operand = template idx (93): counter 2270 after (not found)', 0, cnt2270(d34t))
    # verb 40 byte order is n, op, value: VAR 0 = 0, script [0, 2, 1]: ==1 is false under (n, op, v); under (n, v, op) it would be '< 2' = true
    h.poke_a5(2282, [0]); h.poke_a5(2270, [0])
    d = h.call(40, [0x00, 0x02, 0x01]); chk('verb 40 [n=0, op=2, v=1] with VAR 0 = 0: counter (order n,op,v: false = 0)', 0, cnt2270(d))
    h.poke_a5(2282, [1])
    d = h.call(40, [0x00, 0x02, 0x01]); chk('verb 40 [n=0, op=2, v=1] with VAR 0 = 1: counter (true = 1)', 1, cnt2270(d))
    # verb 48: then-part runs when the counter is ZERO; script [len=5][verb 38 (0x26) var 5 := 1][0x16]
    for c, want in ((0, 1), (1, 0)):
        h.poke_a5(2270, [c]); h.poke_a5(2287, [0])
        d = h.call(48, [0x05, 0x26, 0x05, 0x01, 0x16])
        got = [new for addr, (old, new) in d['delta'].items() if addr == A5 + 2287]
        chk('verb 48 with counter %d: then-part (VAR 5 := 1) runs' % c, want, got[0] if got else 0)
    # verb 14: then-part runs when the counter is non-zero
    for c, want in ((1, 1), (0, 0)):
        h.poke_a5(2270, [c]); h.poke_a5(2287, [0])
        d = h.call(14, [0x05, 0x26, 0x05, 0x01, 0x16])
        got = [new for addr, (old, new) in d['delta'].items() if addr == A5 + 2287]
        chk('verb 14 with counter %d: then-part (VAR 5 := 1) runs' % c, want, got[0] if got else 0)
    # verb 82 deletes by template idx (word +2 of the record): n = 93 removes (680, 93); count 1 -> 0
    d = h.call(82, [93]); cnt = [new for addr, (old, new) in d['delta'].items() if addr == A5 + 2438]
    chk('verb 82 n=93 (template idx): rucksack count after (was 1)', 0, cnt[0] if cnt else 1)
    h.close()

    # ---- C: the real consumer, events injected for the owning object / room (fresh game each)
    def fresh(): return H(LIN)
    h = fresh(); r = h.r
    run_event(h, 720, 0x12, 690)
    chk('720 ev18 word 690 (object id): door $79 word ffff -> 0', 0, flagw(h, 121))
    chk('720 ev18 word 690: door $7e word ffff -> 0', 0, flagw(h, 126))
    chk('720 ev18 word 690: object 731 hidden bit 1 -> 0', 0, b3(h, 731) >> 7)
    chk('720 ev18 word 690: object 690 deleted (type-6 entry size 0)', 0, r.w(h.rows[6][0] + 4 * 690))
    h.close()
    h = fresh(); r = h.r
    run_event(h, 720, 0x12, 45)                                   # 45 = template idx of object 690 (record word +2): must NOT match
    chk('720 ev18 word 45 (template idx, negative control): door $79 stays ffff', 0xffff, flagw(h, 121))
    h.close()
    h = fresh(); r = h.r
    run_event(h, 349, 5)
    chk('349 ev5: object 690 hidden bit 1 -> 0 (SHOW)', 0, b3(h, 690) >> 7)
    h.close()
    h = fresh(); r = h.r
    run_event(h, 710, 5); b0_710 = b3(h, 710) & 1
    chk('710 ev5 with 711 not pressed: own state bit 0 set (no teleport)', (1, 90), (b0_710, room(h)))
    run_event(h, 711, 5)
    chk('711 ev5 with 710 pressed: TELEPORT 82 (room 1166(A5))', 82, room(h))
    h.close()
    h = fresh(); r = h.r
    run_event(h, 275, 5);       chk('275 ev5 (room 48): door $73 word ffff -> 0', 0, flagw(h, 115))
    h.close()
    h = fresh(); r = h.r
    run_event(h, 539, 0x12, 538); chk('539 ev18 word 538: door $42 word ffff -> 0', 0, flagw(h, 66))
    h.close()
    h = fresh(); r = h.r
    run_event(h, 27, 5);        chk('27 ev5 (room 89): door $01 word ffff -> 0', 0, flagw(h, 1))
    h.close()
    h = fresh(); r = h.r
    run_event(h, 719, 0x12, 716); run_event(h, 719, 0x12, 717)
    chk('719 ev18 word 716 then 717: VAR 18 (0 -> 1 -> 2)', 2, var(h, 18))
    run_event(h, 719, 0x12, 718)
    chk('719 ev18 word 718 at VAR 18 = 2: door $2b word ffff -> 0', 0, flagw(h, 43))
    chk('719 ev18 word 718: VAR 18 reset to 0', 0, var(h, 18))
    h.close()
    h = fresh(); r = h.r
    run_event(h, 719, 0x12, 718)
    chk('719 ev18 word 718 at VAR 18 = 0 (negative control): door $2b stays ffff', 0xffff, flagw(h, 43))
    h.close()
    h = fresh(); r = h.r
    run_event(h, 27, 5)                                                              # opens $01
    run_event(h, 4, 0x4006, 0, kind='room')                                        # room 4's every-entry block: SET FLAG $01 := $ffff
    chk('room 4 ev6 (every entry): door $01 word 0 -> ffff again (one-way)', 0xffff, flagw(h, 1))
    h.close()
    # room 17's region event 15 with 731 in the rucksack: poke the type-8 record (731, 127) and the count
    h = fresh(); r = h.r
    dat = h.rows[8][1]
    r.cmd('w %x %08x' % (dat + 4, (731 << 16) | 127))                               # second record slot
    r.cmd('w %x %08x' % (h.rows[8][0] + 4, 0x00040004))                             # its index entry: [size 4][offset 4] ($00c628 walks the index, not the count)
    w4 = r.mem(A5 + 2436, 4); r.cmd('w %x %02x%02x%02x%02x' % (A5 + 2436, w4[0], w4[1], 2, w4[3]))
    run_event(h, 17, 0xc00f, 1, kind='room', extra=0)
    chk('17 region 1 (event 15) with item 731 in the rucksack (poked): door $74 word ffff -> 0', 0, flagw(h, 116))
    h.close()
    h = fresh(); r = h.r
    run_event(h, 17, 0xc00f, 1, kind='room', extra=0)
    chk('17 region 1 (event 15) WITHOUT 730/731 (control): door $74 stays ffff', 0xffff, flagw(h, 116))
    h.close()
    print('%d of %d checks match' % (sum(ROWS), len(ROWS)))

if __name__ == '__main__':
    main()
