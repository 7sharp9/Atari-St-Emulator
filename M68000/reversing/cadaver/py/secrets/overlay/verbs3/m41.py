"""m41.py: verb 41 PLACE ($010aaa) and the free-space search $008e38 it uses (also verbs 36/44/73/84 through the frame service $00e38c and the teleport).
Evidence: callcap on scratch scripts (operand layout, the other-room branch, class-3 assert), live runs through the consumer $00fdbc on THROWAWAY forks (each
check starts a fresh REPL from the snapshot; nothing is saved), the placement array (56(A5), 70-byte entries) rewritten to a chosen crowd, the candidate
positions logged at $008f1c, and a Python transcription of the search (place_model.py) compared candidate by candidate.  `<label> ok|BAD` lines.
Run: cd M68000 && .venv/bin/python reversing/cadaver/py/secrets/overlay/verbs3/m41.py   (about 20 seconds)"""
from place_lib import *
from place_model import model
import lib2, random

SNAP7 = 'scratchpad/cadaver/secrets_out/action/room7_entry.snap'
OID = 60

def tmpl_ext(h, oid):
    a = h.obj(oid); ta = h.res(2, int.from_bytes(h.ram[a + 6:a + 8], 'big')); r = h.r
    return r.w(ta + 16), r.w(ta + 18), r.w(ta + 20), r.b(ta + 22)

def final_rec(snap, oid, script, blockers):
    """second phase: a fresh fork, same crowd and script, stopped at the return of $00c24e inside verb 41 ($010b4a): the record before the game moves it"""
    h = H(snap); r = h.r
    if blockers is not None: crowd(h, blockers, subject=oid)
    h.owner = 2; set_body(h, script); inject5(h)
    out = r.cmd('bp 10b4a 700000'); a = h.obj(oid)
    rec = r.mem(a, 12); h.close()
    return rec, out[0]

def run():
    # ============ A. strings of the asserts
    h = H(SNAP0); r = h.r
    for a, s in ((0x17822, b'EXCEEDED ADD LIST SPACE'), (0x1783a, b'CREATE SIZE ZERO'), (0x1784c, b'NO SPACE IN THIS ROOM'), (0x17862, b'INIT ROOM ERROR'), (0x17872, b'CANT PUT CREATURE IN ROOM'), (0x1788c, b'CANT FIND A SPACE PUT IN ROOM')):
        got = r.mem(a, 40).split(b'\0')[0]
        chk('verb 41 assert text at $%x = %r' % (a, got), got == s)
    h.close()
    # ============ B. callcap: layout, other-room branch, class 3
    h = H(SNAP0); r = h.r
    a60 = h.obj(60); t5_0 = t5_list(h, 0)[0]; t5_5 = t5_list(h, 5)[0]; rec0 = r.mem(a60, 12)
    d = h.call(41, [0, 60, 5, 70, 71, 9])
    rec1 = after(h, d, a60, 12); l0, _, _ = t5_list(h, 0, d); l5, _, _ = t5_list(h, 5, d)
    chk('verb 41 callcap [#60 room 5 x70 y71 z9]: consumes 6 bytes; record %s -> %s: x y z written exactly (70,71,9), +3 bit 3 set (%02x -> %02x), +10 = %d; id leaves room 0\'s type-5 list (%s -> %s) and joins room 5\'s (%s -> %s)' % (
        rec0.hex(), rec1.hex(), rec0[3], rec1[3], rec1[10], 60 in t5_0, 60 in l0, 60 in t5_5, 60 in l5),
        d['ret'] and d['da1'] == 6 and tuple(rec1[:3]) == (70, 71, 9) and rec1[3] == rec0[3] | 8 and rec1[10] == 5 and 60 in t5_0 and 60 not in l0 and 60 not in t5_5 and 60 in l5, (d['thrown'][:1]))
    chk('verb 41 other-room branch does not run the search: the delta holds no write of the search state 1230/1232(A5) = %s' % [hex(x) for x in d['delta'] if A5 + 1230 <= x < A5 + 1234], not any(A5 + 1230 <= x < A5 + 1234 for x in d['delta']))
    # same-room branch by callcap: record gets the exact target when free; class 3 asserts
    d = h.call(41, [0, 60, 0xfe, 40, 20, 0])
    rec1 = after(h, d, a60, 12)
    chk('verb 41 callcap [#60 room $fe x40 y20 z0] (this room): consumes 6 bytes; record x y z %s, +3 %02x, +10 %d (searched, this room)' % (list(rec1[:3]), rec1[3], rec1[10]), d['ret'] and d['da1'] == 6 and tuple(rec1[:3]) == (40, 20, 0) and rec1[10] == 0, d['thrown'][:1])
    o3 = [i for i in range(h.rows[6][2]) if h.obj(i) and tmpl_ext(h, i)[3] == 3][0]
    d = h.call(41, [o3 >> 8, o3 & 255, 0xfe, 40, 20, 0])
    chk('verb 41 callcap on #%d (template class byte 3): assert "CANT PUT CREATURE IN ROOM" (A0 = $17872 at $011788): thrown=%s, not returned' % (o3, d['thrown'][:1]), bool(d['thrown']) and not d['ret'])
    h.close()

    # ============ C. which room operands take the search (live, hits on $008e38), from room 0 (CAVERN) and room 7
    for snap, cur, subj, label in ((SNAP0, 0, 60, 'CAVERN (room 0)'), (SNAP7, 7, 62, 'room 7')):
        h = H(snap); r = h.r; crowd(h, [], subject=subj)
        ctl = r.hits(200000, PSEARCH).get(PSEARCH, 0); h.close()      # the game's own callers of the search in the same window
        for op, want, lab in ((0xfe, 1, '$fe'), (cur, 1, 'the current room number %d' % cur), (0, 1 if cur == 0 else 0, 'room 0'), (0x21, 0, 'room $21')):
            h = H(snap); r = h.r; h.owner = 2
            crowd(h, [], subject=subj)
            set_body(h, [41, 0, subj, op, 40, 20, 0]); inject5(h)
            hh = r.hits(200000, PVERB41, PSEARCH)
            a = h.obj(subj); rec = r.mem(a, 11); h.close()
            n = hh.get(PSEARCH, 0) - ctl
            chk('live[v41] in %s: PLACE #%d room operand %s: verb entered %d, search $008e38 entered %d times (control without the verb: %d), so %d from the verb (want %d), record +10 = %d' % (label, subj, lab, hh.get(PVERB41, 0), hh.get(PSEARCH, 0), ctl, n, want, rec[10]), hh.get(PVERB41) == 1 and n == want)

    # ============ D. search order: live trace vs the transcription, random crowds, two objects
    random.seed(91)
    def scen():
        x = random.choice([12, 30, 40, 60, 74]); y = random.choice([12, 20, 30, 40]); z = random.choice([0, 0, 3])
        bl = []
        for k in range(random.randint(1, 4)):
            cx = x + random.randint(-8, 8); cy = y + random.randint(-8, 8); w = random.randint(3, 16); hh_ = random.randint(3, 16)
            bl.append((cx - w // 2, cy - hh_ // 2, cx + w // 2, cy + hh_ // 2, random.choice([0, 0, 2]), random.choice([10, 30, 60])))
        return (x, y, z), bl
    nmatch = 0; ncand = 0; nscen = 0
    for oid in (60, 14, 60):
        for i in range(6):
            (x, y, z), bl = scen()
            h = H(SNAP0); r = h.r
            w16, w18, w20, cls = tmpl_ext(h, oid); world = (r.b(A5 + 2238), r.b(A5 + 2239), r.b(A5 + 2204), r.b(A5 + 2203))
            crowd(h, bl, subject=oid)
            res = drive41(h, [41, 0, oid, 0xfe, x, y, z], maxcand=400, owner=2); h.close()
            ents = [(xh, yh, xl, yl, zh, zl) for (xl, yl, xh, yh, zl, zh) in bl]
            mc, mf = model(x, y, z, w16, w18, w20, ents, world)
            live = [c[:4] for c in res['cands']]; mod = [c[:4] for c in mc]
            rec, _ = final_rec(SNAP0, oid, [41, 0, oid, 0xfe, x, y, z], bl)
            ok = (live == mod) and mf not in (None, 'runaway') and tuple(rec[:3]) == tuple(mf)
            nscen += 1; ncand += len(live)
            chk('live[v41] search #%d from (%d,%d,%d) with %d blockers: %d candidates (x,y,z,D6) identical to the transcription, found %s (record at the return of $c24e %s)' % (oid, x, y, z, len(bl), len(live), mf, tuple(rec[:3])), ok, (live[:20], mod[:20]))
    print('  search transcription: %d scenarios, %d candidate positions compared' % (nscen, ncand))

    # ============ E. a fixed illustrative crowd: the order and distances in words
    h = H(SNAP0); r = h.r; crowd(h, [(30, 8, 52, 40, 0, 40)], subject=60)
    res = drive41(h, [41, 0, 60, 0xfe, 40, 20, 0], maxcand=100); h.close()
    c = res['cands']
    seq = [(x - 40, y - 20, z) for (x, y, z, d6, *_r) in c]
    chk('live[v41] order for a blocker x30..52 y8..40 z0..40 around (40,20,0): as-is, then per round k (step 4k) -y, +x-y, +x, +x+y, +y, -x+y, -x, -x-y, then z-1 (65535 = -1: below 0, so bit $20 is cleared) and z+1 at the base xy, later rounds at the raised z; first 12 offsets %s' % seq[:12],
        seq[:12] == [(0, 0, 0), (0, -4, 0), (4, -4, 0), (4, 0, 0), (4, 4, 0), (0, 4, 0), (-4, 4, 0), (-4, 0, 0), (-4, -4, 0), (0, 0, 65535), (0, 0, 1), (0, -8, 1)])

    # ============ F. full room: nothing free -> D6 = 0 -> the assert, on a throwaway fork
    h = H(SNAP0); r = h.r; h.owner = 2
    crowd(h, [(0, 0, 127, 127, 0x80, 127)], subject=60)
    set_body(h, [41, 0, 60, 0xfe, 40, 20, 0]); inject5(h)
    out = r.cmd('bp 11788 900000')
    reg = regs(out)
    msg = r.mem(reg['A0'], 40).split(b'\0')[0] if 'A0' in reg else None
    chk('live[v41] a blocker covering the whole room (x 0..127, y 0..127, z -128..127: the byte compares are signed): the search fails (D6 = 0) and the engine assert $011788 is entered with A0 = $%x = %r' % (reg.get('A0', 0), msg), msg == b'CANT FIND A SPACE PUT IN ROOM', out[0])
    hh = r.hits(300000, 0x6ba2, 0x117c4)
    chk('live[v41] after the assert: the main loop $006ba2 is entered %d times and the spin loop $0117c4 %d times in 300,000 steps (the game is stopped for good: fatal screen and endless loop)' % (hh.get(0x6ba2, 0), hh.get(0x117c4, 0)), hh.get(0x6ba2, 0) == 0 and hh.get(0x117c4, 0) > 1000)
    h.close()
    h = H(SNAP0); r = h.r
    crowd(h, [(0, 0, 127, 127, 0x80, 127)], subject=60)
    res = drive41(h, [41, 0, 60, 0xfe, 40, 20, 0], maxcand=1000); h.close()
    w16, w18, w20, cls = (6, 7, 22, 2)
    mc, mf = model(40, 20, 0, w16, w18, w20, [(127, 127, 0, 0, 127, 0x80)], (80, 80, 6, 6))
    chk('live[v41] full room: %d candidates tried before D6 reaches 0 (transcription: %d, found %s); the last three (x,y,z,D6) %s' % (len(res['cands']), len(mc), mf, [c[:4] for c in res['cands'][-3:]]),
        [c[:4] for c in res['cands']] == [c[:4] for c in mc] and mf is None and len(mc) > 100)

    # a blocker of z 0..127 (an ordinary non-negative z range) does not make the room full: the search climbs z by one per round until the byte D5 = z + 21 passes 127 (negative as a signed byte, below z_lo)
    h = H(SNAP0); r = h.r
    crowd(h, [(0, 0, 127, 127, 0, 127)], subject=60)
    res = drive41(h, [41, 0, 60, 0xfe, 40, 20, 0], maxcand=1000); h.close()
    mc, mf = model(40, 20, 0, 6, 7, 22, [(127, 127, 0, 0, 127, 0)], (80, 80, 6, 6))
    chk('live[v41] a blocker x0..127 y0..127 z0..127: %d candidates, the object is placed at %s (z climbs 1 per round until D5 = z+21 wraps negative at z = 107); transcription %s' % (len(res['cands']), res['cands'][-1][:3] if res['cands'] else None, mf),
        [c[:4] for c in res['cands']] == [c[:4] for c in mc] and mf == (40, 20, 107))

if __name__ == '__main__':
    run(); print('ok %d bad %d' % (lib2.OK, lib2.BAD))
    print('per-verb evidence (ok/bad):', ', '.join('%d: %d/%d' % (v, c[0], c[1]) for v, c in sorted(lib2.TALLY.items())))
