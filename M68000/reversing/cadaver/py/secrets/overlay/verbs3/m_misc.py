"""m_misc.py: verbs 84 ($0108b6), 91 ($010f9e), 7 REGISTER ($01031e) and 8 UNREGISTER ($01032c), and the readers of the creature list 396(A5).
callcap on scratch scripts (operand layout by A1 advance, spawn entry / condition counter / list deltas), plus live runs through the consumer $00fdbc where the
mechanism is a frame service ($00e38c spawn drain, $00e25c creature loop).  `<label> ok|BAD` lines.
Run: cd M68000 && .venv/bin/python reversing/cadaver/py/secrets/overlay/verbs3/m_misc.py"""
from place_lib import *
import lib2

def run():
    h = H(SNAP0); r = h.r
    o1 = 60; a1 = h.obj(o1); pos1 = tuple(r.mem(a1, 3))
    def fields(e): return dict(size=int.from_bytes(e[0:2], 'big'), ptr=int.from_bytes(e[2:6], 'big'), pos=tuple(e[6:9]), room=e[9], d6=int.from_bytes(e[10:12], 'big'), tmpl=int.from_bytes(e[12:16], 'big'))
    def entry(d): return after(h, d, A5 + 1468, 16)
    def tmpl_of(oid): a = h.obj(oid); return h.res(2, int.from_bytes(h.ram[a + 6:a + 8], 'big'))
    # ============ verb 84
    o2 = 448; tp = tmpl_of(o2)
    for dx, dy, z, room, lab in ((3, 4, 5, 0xfe, 'small offsets'), (0, 0, 0, 0xfe, 'zero offsets'), (0xf0, 0xe0, 9, 0x21, 'offsets that wrap the byte (add.b)'), (1, 2, 0xff, 0, 'z $ff')):
        d = h.call(84, [0, o1, o2 >> 8, o2 & 255, dx, dy, z, room], regs='A1=%x A4=7f100 D6=9' % BUF); f = fields(entry(d))
        want = ((pos1[0] + dx) & 255, (pos1[1] + dy) & 255, z)
        chk('verb 84 [#60 #448 dx=%d dy=%d z=%d room=$%02x] (%s): consumes 8 bytes, count 1466(A5) -> %d, entry position %s = (o1.x+dx, o1.y+dy, z) %s, room byte $%02x, D6 field %d (the caller\'s D6: the handler never sets it), template ptr = o2\'s' % (dx, dy, z, room, lab, afterw(h, d, A5 + 1466), f['pos'], want, f['room'], f['d6']),
            d['ret'] and d['da1'] == 8 and afterw(h, d, A5 + 1466) == 1 and f['pos'] == want and f['room'] == room and f['d6'] == 9 and f['tmpl'] == tp)
    # o1 = ffff: the current object (348(A5))
    sv = r.mem(A5 + 348, 4); h.poke(A5 + 348, a1.to_bytes(4, 'big'))
    d = h.call(84, [0xff, 0xff, o2 >> 8, o2 & 255, 3, 4, 5, 0xfe]); f = fields(entry(d)); h.poke(A5 + 348, list(sv))
    chk('verb 84 with o1 = $ffff and 348(A5) -> #60: entry position %s = (%d, %d, 5)' % (f['pos'], pos1[0] + 3, pos1[1] + 4), f['pos'] == (pos1[0] + 3, pos1[1] + 4, 5))
    h.close()
    # live: the consumer's D6 at the verb, and the drain's position
    h = H(SNAP0); r = h.r; h.owner = 2
    set_body(h, [84, 0, o1, o2 >> 8, o2 & 255, 3, 4, 5, 0xfe]); inject5(h)
    out = r.cmd('bp 108b6 400000'); g = regs(out)
    chk('live[v84] under the consumer ($00fe2a: D0 = D6 = the event number): D6 at the entry of verb 84 = %d for an injected event 5' % g['D6'], g['D6'] == 5, out[0])
    h.close()
    for o2l, lab, want_pos in ((448, 'plain template (search)', None), (463, 'class-bit-7 template (launch routine, no direction offset)', None)):
        h = H(SNAP0); r = h.r; h.owner = 2
        crowd(h, [], subject=60)
        set_body(h, [84, 0, o1, o2l >> 8, o2l & 255, 3, 4, 5, 0xfe]); inject5(h)
        out = r.cmd('bp c24e 400000'); g = regs(out) if 'gave up' not in out[0] else None
        pos = None if g is None else (g['D0'] & 255, g['D1'] & 255, g['D2'] & 255, g['D4'] & 255)
        h.close()
        chk('live[v84] #%d %s: $c24e entered with (x,y,z,room) %s, expected (o1.x+3, o1.y+4, 5) = %s' % (o2l, lab, pos, (pos1[0] + 3, pos1[1] + 4, 5)), pos is not None and pos[:3] == (pos1[0] + 3, pos1[1] + 4, 5))

    # ============ verb 91
    h = H(SNAP0); r = h.r
    a27 = h.obj(27); t27 = int.from_bytes(h.ram[a27 + 6:a27 + 8], 'big')
    h.poke(A5 + 348, a27.to_bytes(4, 'big'))
    for tidx, op, want, lab in ((t27, t27 & 255, 1, 'equal'), (t27, (t27 + 1) & 255, 0, 'one off'), (0x013b, 0x3b, 1, 'record word +6 = $013b (high byte ignored): operand $3b'), (0x013b, 0x3a, 0, 'record word +6 = $013b: operand $3a'), (0x0100, 0x00, 1, 'record word +6 = $0100 vs 0')):
        h.poke(a27 + 6, [tidx >> 8, tidx & 255]); h.poke(A5 + 2270, [7 if not want else 0]); d = h.call(91, [op])
        chk('verb 91 [%02x] with current object (348(A5) -> #27) template word %04x (%s): consumes 1 byte, 2270(A5) -> %d (want %d)' % (op, tidx, lab, afterb(h, d, A5 + 2270), want), d['ret'] and d['da1'] == 1 and afterb(h, d, A5 + 2270) == want and len(d['delta']) <= 1)
    # 2270 counter semantics: true adds 1 (not sets 1)
    h.poke(a27 + 6, [t27 >> 8, t27 & 255]); h.poke(A5 + 2270, [3]); d = h.call(91, [t27 & 255])
    chk('verb 91 true with 2270(A5) = 3: -> %d (a true condition ADDS one: the IF-count semantics of $0106ca)' % afterb(h, d, A5 + 2270), afterb(h, d, A5 + 2270) == 4)
    h.poke(a27 + 6, [t27 >> 8, t27 & 255])
    # use in the scripts: none (the static decode counts), and template indices above 255 in the levels
    mx = max(int.from_bytes(h.ram[h.obj(i) + 6:h.obj(i) + 8], 'big') for i in range(h.rows[6][2]) if h.obj(i))
    chk('verb 91 reach: the largest template index of any level-0 object record is %d (<= 255, so the low byte is the whole index there; level 1: 142)' % mx, mx <= 255)
    h.close()

    # ============ verbs 7 and 8 and the creature list 396(A5)
    h = H(SNAP0); r = h.r
    r.cmd('w %x %08x' % (A5 + 396, 0)); r.cmd('w %x %08x' % (A5 + 400, 0)); r.cmd('w %x %08x' % (A5 + 404, 0))
    # fill the list with 6 ids via six REGISTER calls chained on the callcap's own state is not possible (state restored), so write the list directly
    r.cmd('w %x %08x' % (A5 + 396, 0x0006000a)); r.cmd('w %x %08x' % (A5 + 400, 0x000b000c)); r.cmd('w %x %08x' % (A5 + 404, 0x000d000e))
    d = h.call(7, [0, 61])
    chk('verb 7 REGISTER with a full list (count 6): assert $0174f0 (max 6): thrown=%s' % (d['thrown'][:1],), bool(d['thrown']) and not d['ret'])
    r.cmd('w %x %08x' % (A5 + 396, 0x0005000a)); r.cmd('w %x %08x' % (A5 + 400, 0x000b000c)); r.cmd('w %x %08x' % (A5 + 404, 0x000d0000))
    d = h.call(7, [0, 61]); lst = after(h, d, A5 + 396, 14)
    chk('verb 7 with count 5 ({a b c d e}, 6th slot free): list -> %s: count 6, the id goes into the first zero slot; consumes 2 bytes' % lst.hex(), d['ret'] and d['da1'] == 2 and lst == bytes.fromhex('0006000a000b000c000d003d'.ljust(28, '0')[:28]) or (d['ret'] and int.from_bytes(lst[:2], 'big') == 6 and int.from_bytes(lst[12:14], 'big') == 61))
    r.cmd('w %x %08x' % (A5 + 396, 0x0001003d)); r.cmd('w %x %08x' % (A5 + 400, 0)); r.cmd('w %x %08x' % (A5 + 404, 0))
    d = h.call(7, [0, 61]); lst = after(h, d, A5 + 396, 6)
    chk('verb 7 twice with the same id (list {61}): count 2, list %s (no duplicate check)' % lst.hex(), d['ret'] and int.from_bytes(lst[:2], 'big') == 2 and int.from_bytes(lst[2:4], 'big') == 61 and int.from_bytes(lst[4:6], 'big') == 61)
    # verb 8: removes the FIRST matching slot, count -= 1; on an empty list: ring event 8 with the text pointer $e1a6, then the assert
    r.cmd('w %x %08x' % (A5 + 396, 0x0002003d)); r.cmd('w %x %08x' % (A5 + 400, 0x003d0000))
    sleeper = h.obj(60); sbase = sleeper + r.b(sleeper + 12)
    h.poke(sbase + 5, [r.b(sbase + 5) & 0x7f])
    d = h.call(8, [0, 61], regs='A0=%x A1=%x A4=7f100' % (sleeper, BUF)); lst = after(h, d, A5 + 396, 6)
    chk('verb 8 UNREGISTER 61 on {61, 61} (A0 = an awake object): count 2 -> %d, slots %s: only the first match is cleared; consumes 2 bytes' % (int.from_bytes(lst[:2], 'big'), lst.hex()), d['ret'] and d['da1'] == 2 and lst == bytes.fromhex('00010000003d'))
    h.poke(sbase + 5, [r.b(sbase + 5) | 0x80])
    d = h.call(8, [0, 61], regs='A0=%x A1=%x A4=7f100' % (sleeper, BUF)); lst = after(h, d, A5 + 396, 6)
    chk('verb 8 UNREGISTER 61 when A0 (the running object) has bit 7 of its sub-block byte +5 set (asleep): nothing happens, list %s unchanged, consumes 2 bytes ($010346 tests the running object, not the operand)' % lst.hex(), d['ret'] and d['da1'] == 2 and lst == bytes.fromhex('0002003d003d'))
    h.poke(sbase + 5, [r.b(sbase + 5) & 0x7f])
    for k in (0, 4, 8, 12): r.cmd('w %x %08x' % (A5 + 396 + k, 0))
    q0 = r.l(A5 + 304); n0 = r.w(A5 + 1154)
    d = h.call(8, [0, 61], regs='A0=%x A1=%x A4=7f100' % (sleeper, BUF)); e = after(h, d, q0, 8)
    chk('verb 8 on an empty list: ring entry %s = [opcode 8][ptr $%06x -> %r] then the assert "KILLING A NON-EXISTANT CRE" (thrown=%s)' % (e.hex(), int.from_bytes(e[2:6], 'big'), r.mem(0xe1a6, 36).split(b'\0')[0], bool(d['thrown'])),
        e[:2] == bytes([0, 8]) and int.from_bytes(e[2:6], 'big') == 0xe1a6 and bool(d['thrown']))
    r.cmd('w %x %08x' % (A5 + 396, 0))
    h.close()
    # who reads the list: static scan of the whole image (main code $001000-$019100 and both overlays $04c65e-$051ffe), plus the per-frame loop live
    import re, os, subprocess, sys
    for n, snap in ((0, SNAP0), (1, SNAP1)):      # whole-overlay listings (regenerated when missing)
        pth = os.path.join(TMP, 'ov_l%d.asm' % n); os.makedirs(os.path.dirname(pth), exist_ok=True)
        if not os.path.exists(pth):
            with open(pth, 'w') as f: subprocess.run([sys.executable, 'tools/disassemble.py', '--snap', snap, '--all', '4c65e', '52000'], stdout=f, cwd=ROOT, check=True)
    rows = []
    for path in ('scratchpad/cadaver/secrets_out/cad_all.asm', os.path.join(TMP, 'ov_l0.asm'), os.path.join(TMP, 'ov_l1.asm')):
        last = 0
        for l in open(path):
            m = re.match(r'\s+\$([0-9a-f]+):', l)
            if m: last = int(m.group(1), 16)
            if re.search(r'\b39[68]\(A5\)', l): rows.append((os.path.basename(path), l.strip()))
        rows.append((os.path.basename(path), 'LAST ADDRESS $%x' % last))
    print('  static 396/398(A5) references:'); [print('   ', x) for x in rows]
    refs = [x for x in rows if '(A5)' in x[1]]
    chk('static: %d references to 396(A5)/398(A5) in main code (4: $e12c clear, $e142 register, $e176 unregister, $e25c frame loop) and both overlays (2 + 2: the two spells $4cdec/$4ce60 and $4cd6a/$4cdde)' % len(refs), len(refs) == 8)
    # live: the frame loop at $00e25c calls the class handler for a listed creature
    for lst, lab in ((0x0001ffff, 'empty list'), (0x000100ed, 'list {#237}')):
        pass
    res = {}
    for cnt, ids, lab in ((0, [], 'empty list'), (1, [237], 'list {#237}'), (2, [237, 285], 'list {#237, #285}')):
        h = H(SNAP0); r = h.r
        words = [cnt] + ids + [0] * (6 - len(ids))
        for k, w in enumerate(words): ww(r, A5 + 396 + 2 * k, w)
        hh = r.hits(120000, 0xe25c, 0xe298, 0xe26e); res[lab] = hh; h.close()
    chk('live: frame loop $00e25c entries / $00e26e resolves / $00e298 class-handler calls in 120,000 steps: %s' % {k: (v.get(0xe25c, 0), v.get(0xe26e, 0), v.get(0xe298, 0)) for k, v in res.items()},
        res['empty list'].get(0xe26e, 0) == 0 and res['list {#237}'].get(0xe26e, 0) > 0 and res['list {#237}'].get(0xe298, 0) > 0 and res['list {#237, #285}'].get(0xe26e, 0) >= 2 * res['list {#237}'].get(0xe26e, 0) - 2)

if __name__ == '__main__':
    run(); print('ok %d bad %d' % (lib2.OK, lib2.BAD))
    print('per-verb evidence (ok/bad):', ', '.join('%d: %d/%d' % (v, c[0], c[1]) for v, c in sorted(lib2.TALLY.items())))
