"""Section 6: verbs 9, 42, 60, 65, 66, 87, 88, 91"""
from lib2 import *
import lib2, re

def run():
    # ============ level 0 callcaps
    h = H(SNAP0); r = h.r
    # ---- 9: queue event $4013 for the current room record with word n
    q0 = r.l(A5 + 304); n0 = r.w(A5 + 1154); room_rec = r.l(A5 + 164)
    d = h.call(9, [5])
    e = after(h, d, q0, 8)
    chk('verb 9  [05]: consumes 1 byte; ring entry at 304(A5) = %s = [opcode $%04x][ptr $%06x = 164(A5) room record][word %d]; write ptr +8, count %d -> %d' % (e.hex(), int.from_bytes(e[:2], 'big'), int.from_bytes(e[2:6], 'big'), int.from_bytes(e[6:8], 'big'), n0, afterw(h, d, A5 + 1154)),
        d['ret'] and d['da1'] == 1 and e == bytes.fromhex('4013') + room_rec.to_bytes(4, 'big') + bytes([0, 5]) and afterl(h, d, A5 + 304) == q0 + 8 and afterw(h, d, A5 + 1154) == n0 + 1)
    # ---- 42: 2462(A5) = a, 2461(A5) = b
    d = h.call(42, [3, 4])
    chk('verb 42 [03 04]: 2462(A5) %02x -> %02x (= a), 2461(A5) %02x -> %02x (= b); consumes 2 bytes; nothing else' % (r.b(A5 + 2462), afterb(h, d, A5 + 2462), r.b(A5 + 2461), afterb(h, d, A5 + 2461)),
        d['ret'] and d['da1'] == 2 and afterb(h, d, A5 + 2462) == 3 and afterb(h, d, A5 + 2461) == 4 and len(d['delta']) == 2)
    # ---- 65: byte +1 of the object's first sub-block (rec + rec[12]) += signed n, clamped 0..255
    a60 = h.obj(60); sb = a60 + r.b(a60 + 12); v0 = r.b(sb + 1)
    for n, start, want in ((5, v0, v0 + 5), (0xfb, v0, max(v0 - 5, 0)), (100, 250, 255), (0x80, 100, 0), (0x7f, 0, 127)):
        h.poke(sb + 1, [start]); d = h.call(65, [0, 60, n])
        chk('verb 65 [#60, %02x]: sub-block byte +1 %d -> %d (want %d), consumes 3 bytes, only that byte changes' % (n, start, afterb(h, d, sb + 1), want), d['ret'] and d['da1'] == 3 and afterb(h, d, sb + 1) == want and len(d['delta']) <= 1)
    # ---- 66: queue [class][sub][object] into 1266(A5); object #483 (the fire) has class byte 0x0a at sub-block +1
    a483 = h.obj(483); cls = r.b(a483 + r.b(a483 + 12) + 1)
    l0 = r.l(A5 + 308); c0 = r.w(A5 + 1264)
    d = h.call(66, [483 >> 8, 483 & 255, 3])
    rec = after(h, d, l0, 6)
    chk('verb 66 [#483, 03]: consumes 3 bytes; record at 308(A5) = %s = [class byte %02x = sub-block byte +1 of #483][sub 03][ptr $%06x]; 308(A5) += 6, 1264(A5) %d -> %d' % (rec.hex(), cls, h.obj(483), c0, afterw(h, d, A5 + 1264)),
        d['ret'] and d['da1'] == 3 and cls == 0x0a and rec == bytes([cls, 3]) + h.obj(483).to_bytes(4, 'big') and afterl(h, d, A5 + 308) == l0 + 6 and afterw(h, d, A5 + 1264) == c0 + 1)
    # ---- 88 COND n == 2489(A5)
    h.poke(A5 + 2489, [3])
    for n, want in ((3, 1), (4, 0)):
        h.poke(A5 + 2270, [0 if want else 7]); d = h.call(88, [n])
        chk('verb 88 [%02x] with 2489(A5) = 3: 2270(A5) -> %d (%s), consumes 1 byte' % (n, afterb(h, d, A5 + 2270), 'true adds 1' if want else 'false clears'), d['ret'] and d['da1'] == 1 and afterb(h, d, A5 + 2270) == want)
    # ---- 91 COND current object's template index (low byte of word +6 of 348(A5)'s record) == n
    h.poke(A5 + 348, h.obj(27).to_bytes(4, 'big')); t27 = int.from_bytes(h.ram[h.obj(27) + 6:h.obj(27) + 8], 'big')
    for n, want in ((t27 & 255, 1), ((t27 + 1) & 255, 0)):
        h.poke(A5 + 2270, [0 if want else 7]); d = h.call(91, [n])
        chk('verb 91 [%02x] with 348(A5) -> #27 (template index %d): 2270(A5) -> %d' % (n, t27, afterb(h, d, A5 + 2270)), d['ret'] and d['da1'] == 1 and afterb(h, d, A5 + 2270) == want)
    # ---- 87: cancel a queued sound.  The table at $0162a2 = [count.w] then words [id<<8 | x]; $015ae0 clears the words whose high byte = n and decrements the count
    snd = 0x162a2
    b0 = r.mem(snd, 8).hex()
    h.poke(snd, [0, 2]); h.poke(snd + 2, [0x0c, 1]); h.poke(snd + 4, [0x30, 1])
    d = h.call(87, [0x0c])
    e = after(h, d, snd, 6)
    chk('verb 87 [0c] on a sound table {count 2: id $0c, id $30} (was %s): -> %s (count 1, the $0c word cleared; the $30 word stays); consumes 1 byte' % (b0, e.hex()), d['ret'] and d['da1'] == 1 and e == bytes.fromhex('000100003001'), e.hex())
    h.close()
    # ============ real runs on level 0: 66 handler, 70/87
    lib2.noise = None
    h = H(SNAP0); r = h.r
    hp0 = r.w(A5 + 1174); shield = r.b(A5 + 2436)
    set_body(h, [66, 483 >> 8, 483 & 255, 0]); inject5(h)
    out = r.cmd('bp e24e 400000'); a1 = re.search(r'A1:([0-9a-f]+)', ' '.join(out)); a0 = re.search(r'A0:([0-9a-f]+)', ' '.join(out))
    chk('natural[v66]  scratch [66 #483 0] under the consumer: the frame service $00e1fa reaches its class-handler call $00e24e with A0 = record $%s, A1 = handler $%s (the fire\'s "class 10 sub 0" handler $04c856)' % (a0.group(1) if a0 else '?', a1.group(1) if a1 else '?'), a0 and a1 and int(a0.group(1), 16) == h.obj(483) and int(a1.group(1), 16) == 0x4c856, out[0])
    r.hits(300000, 0xe24e)
    chk('natural[v66]  ... after the frame the list count 1264(A5) is back to 0, health %d -> %d (handler: hp -20 unless shield bit 3 of the byte 2436(A5) = $%02x)' % (hp0, r.w(A5 + 1174), shield), r.w(A5 + 1264) == 0 and (r.w(A5 + 1174) == hp0 - 20 or shield & 8))
    h.close()
    h = H(SNAP0); r = h.r
    set_body(h, [87, 0x0c]); inject5(h)
    out = r.cmd('bp 15ae0 400000'); d0 = re.search(r'D0:([0-9a-f]+)', ' '.join(out))
    chk('natural[v87]  scratch [87 0c] under the consumer: $015ae0 entered with D0 = $%s (the operand)' % (d0.group(1) if d0 else '?'), d0 and int(d0.group(1), 16) == 0x0c, out[0])
    h.close()
    # 70 then 87: the play queue gains and loses the sound
    for script, label in (([70, 0x0c], 'PLAY $0c'), ([70, 0x0c, 87, 0x0c], 'PLAY $0c then 87 $0c')):
        h = H(SNAP0); r = h.r
        set_body(h, script); inject5(h); r.hits(20000, 0xfe24)
        cnt = r.w(0x162a2); ids = [r.mem(0x162a4 + 2 * i, 1)[0] for i in range(max(cnt, 1))]
        chk('natural[v70,87]  scratch %s: sound table $0162a2 count %d, ids %s' % (label, cnt, [hex(i) for i in ids if cnt]), (cnt == 1 and ids[0] == 0x0c) if len(script) == 2 else cnt == 0)
        h.close()

    # ============ level 1: verb 9 through the room record's event-19 block, verb 60 (buy prompt)
    h = H(SNAP1); r = h.r
    room80 = h.res(3, 80); blk = h.ram[room80 + 0x20:room80 + 0x20 + 64]
    # find the event-19 block in the room's second list (count byte +31)
    p = room80 + 0x20; found = None
    for k in range(h.ram[room80 + 31]):
        if h.ram[p + 1] & 0x7f == 19: found = (k, p, h.ram[p]); break
        p += h.ram[p]
    var4 = A5 + 2282 + 4
    chk('level 1  room 80 record carries a second script list (+$20, count %d at +31) with an event-19 block %s' % (h.ram[room80 + 31], bytes(h.ram[found[1]:found[1] + found[2]]).hex() if found else None), found is not None)
    h.owner = 27
    r.cmd('w %x %08x' % (A5 + 164, room80))
    v0 = r.b(var4)
    set_body(h, [9, 0]); inject5(h)
    hh = r.hits(300000, 0xfe24, 0x10c66)
    v1 = r.b(var4)
    chk('natural[v9]  L1: scratch [09 00] with 164(A5) -> room 80 record: verb 9 pushed ($010c66 %d), the consumer found the room\'s event-19 block (matches %d), its first verb (39: VAR 4 += 1) ran: VAR4 %d -> %d' % (hh.get(0x10c66, 0), hh.get(0xfe24, 0), v0, v1),
        hh.get(0x10c66) == 1 and hh.get(0xfe24) == 2 and v1 == v0 + 1, hh)
    h.close()

if __name__ == '__main__':
    run(); print('ok %d bad %d' % (lib2.OK, lib2.BAD))
