"""gates.py [char ...] : per-character gates over the logs written by run_chars.sh (out/ch<c>_*.txt, wj_ch<c>_*, bg_ch<c>, a1_ch<c>, walk_ch<c>; pdrive format). Each gate prints PASS/FAIL matched/total and what
was compared; expectations come from the program ROM (charlib.py, the player's own +92 from the state dump), not from memory. Character index: 0 Guy, 1 Cody, 2 Haggar.
Gates: combo jump special strike throw wall walk rand slam flip"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import charlib as C
res = []
def gate(name, ok, tot, note=''):
    res.append((name, ok, tot)); print('%s  %-46s %d/%d  %s' % ('PASS' if ok == tot and tot else 'FAIL', name, ok, tot, note))
def events(log, ch, idx=12):
    p92 = C.state_p92(ch)
    out = []
    for rel, d, id22, t63, r, ds in C.hits(log, idx):
        if d > 0: continue
        box = C.attack_box(ch, id22)
        out.append(dict(rel=rel, d=-d, id=id22, type=t63, row=r, ds=ds, box=box, exp=C.damage_byte(p92, box['off']), award=C.hit_award(ch, box['off'])[1]))
    return out
CHAIN = {0: [0x01, 0x01, 0x02, 0x07, 0x0d], 1: [0x01, 0x01, 0x02, 0x03], 2: [0x01, 0x01, 0x02]}
def g_combo(ch):
    ev = [e for e in events('ch%d_c1' % ch, ch)]
    ok = sum(1 for e in ev if e['d'] == e['exp'] and e['type'] == e['box']['hit'] and e['ds'] == e['award'])
    ids = [e['id'] for e in ev]
    gate('%s combo chain: id, damage, type, award' % C.NAMES[ch], ok if ids == CHAIN[ch] else 0, len(ev), 'ids %s expected %s (limit %d -> %d hits)' % ([hex(i) for i in ids], [hex(i) for i in CHAIN[ch]], C.combo_limit(ch), C.combo_limit(ch) // 2 + 1))
def g_jump(ch):
    ok = tot = 0; ids = collections.Counter()
    for n in ('j1', 'j2', 'j3', 'j4'):
        for e in events('ch%d_%s' % (ch, n), ch):
            tot += 1; ids[e['id']] += 1
            ok += (e['d'] == e['exp'] and e['type'] == e['box']['hit'] and e['ds'] == e['award'])
    gate('%s jump attacks: id, damage, type, award' % C.NAMES[ch], ok, tot, 'ids %s' % dict((hex(k), v) for k, v in sorted(ids.items())))
def g_special(ch):
    ok = tot = 0; ids = set()
    for n in ('s1_30', 's1_-30'):
        for e in events('ch%d_%s' % (ch, n), ch):
            tot += 1; ids.add(e['id']); ok += (e['d'] == e['exp'] and e['type'] == e['box']['hit'] and e['ds'] == e['award'])
    gate('%s special: id, damage, type, award' % C.NAMES[ch], ok, tot, 'ids %s' % sorted(hex(i) for i in ids))
    rows, _ = C.load('a1_ch%d' % ch)
    sp = [r for r in rows if r['sub'] == '10']
    first = sp[0]['rel']; n = 0
    while any(r['rel'] == first + n and r['sub'] == '10' for r in rows): n += 1
    seg = [r for r in rows if first <= r['rel'] < first + n]
    apex = max(int(r['y'], 16) - int(r['gy'], 16) for r in seg)
    vys = [int(r['vy'].split('/')[0], 16) for r in seg if int(r['vy'].split('/')[0], 16) < 0x8000]
    vy = max(vys) if vys else 0
    print('        %s special: %d frames, apex +%d px, vy %04x' % (C.NAMES[ch], n, apex, vy))
def g_strike(ch):
    ok = tot = 0
    exp = [C.strike_damage(ch, s) for s in (2, 4, 6)]
    aw = [C.w(0xd86e + 8 * ch + s) for s in (2, 4, 6)]
    ty = [C.w(0xd8a6 + 8 * ch + s) for s in (2, 4, 6)]
    h = [x for x in C.hits('ch%d_g3d' % ch) if x[1] < 0]
    got = [(-d, t63, ds) for rel, d, id22, t63, r, ds in h][:3]
    want = [(exp[i], ty[i], C.AMT[aw[i]]) for i in range(3)]
    gate('%s grapple strikes: damage, type, award' % C.NAMES[ch], sum(1 for a, b in zip(got, want) if a == b) if len(got) == 3 else 0, 3, 'got %s rom %s' % (got, want))
def g_throw(ch):
    h = [x for x in C.hits('ch%d_g3a' % ch) if x[1] < 0]
    h2 = [x for x in C.hits('ch%d_g3b' % ch) if x[1] < 0]
    if ch == 2:
        got = [(-d, t63, ds) for rel, d, id22, t63, r, ds in h[:1] + h2[:1]]
        gate('Haggar throw (pile driver sub 8): -50, type 6, +1000', sum(1 for g in got if g == (50, 6, 1000)), 2, str(got))
    else:
        exp = 30 if ch == 0 else 40
        got = [-d for rel, d, id22, t63, r, ds in h[-1:] + h2[-1:]]
        gate('%s throw landing damage ($3f7a, $3fd8 flat %d)' % (C.NAMES[ch], exp), sum(1 for g in got if g == exp), 2, str(got))
def g_flip(ch):
    ok = 0; out = []
    for v, away in (('a', True), ('b', False)):
        rows, _ = C.load('ch%d_g3%s' % (ch, v))
        s8 = [r for r in rows if r['sub'] == '08' and r['m66'] == '02']
        if not s8: continue
        flipped = s8[0]['b46'] != s8[-1]['b46']
        exp = away if ch != 2 else (not away)     # Guy and Cody turn on the away press, Haggar on the toward press
        out.append((('away' if away else 'toward'), flipped)); ok += (flipped == exp)
    gate('%s turns on the %s press in the throw' % (C.NAMES[ch], 'toward' if ch == 2 else 'away'), ok, 2, str(out))
def g_wall(ch):
    got = []
    for n in ('a', 'b1grip', 'left', 'down'):
        rows, _ = C.load('wj_ch%d_%s' % (ch, n))
        got.append(sum(1 for r in rows if r['sub'] == '16'))
    if ch == 0:
        a = {r['rel']: r for r in C.load('wj_ch0_a')[0]}
        rows = C.load('wj_ch0_a')[0]
        s16 = [r for r in rows if r['sub'] == '16']
        bounce = [r for r in s16 if r['ss'] == '04']
        vx = bounce[0]['vx'] if bounce else None
        rows_l = [r for r in C.load('wj_ch0_left')[0] if r['sub'] == '16' and r['ss'] == '04']
        vxl = rows_l[0]['vx'] if rows_l else None
        rows_b = [r for r in C.load('wj_ch0_b1grip')[0] if r['sub'] == '16' and r['ss'] == '04']
        first_a = s16[0]['rel']
        gate('Guy wall jump: grip, bounce vx/vy per branch', int(got[0] > 0 and vx == 'fb80/0000' and vxl == 'f980/fff0' and got[3] > 0), 1,
             'sub $16 frames a/b1/left/down %s; bounce (no key) vx %s, (left held) vx %s; grip %d frames' % (got, vx, vxl, sum(1 for r in s16 if r['ss'] in ('00', '02')) ))
    else:
        gate('%s never enters sub $16 (wall jump is Guy-only)' % C.NAMES[ch], int(sum(got) == 0), 1, 'sub $16 frames %s' % got)
def g_walk(ch):
    rows, _ = C.load('walk_ch%d' % ch); by = {r['rel']: r for r in rows}
    X = lambda k: int(by[k]['x'], 16); G = lambda k: int(by[k]['gy'], 16)
    r = (X(80) - X(20)) / 60.0; l = (X(120) - X(180)) / 60.0; u = (G(280) - G(220)) / 60.0; d = (G(320) - G(380)) / 60.0
    print('        %s walk: right %.3f left %.3f px/frame, down %.3f px/frame, up %s (the +14 lane limit clamps when the start lane is high)' % (C.NAMES[ch], r, l, d, ('%.3f px/frame' % u) if abs(u) > 0.3 else 'clamped'))
    return r
def g_rand(ch):
    ok = tot = 0
    for seed in (1, 2):
        for e in events('ch%d_rand%d' % (ch, seed), ch):
            if e['id'] == 0: continue
            tot += 1; ok += (e['d'] == e['exp'] and e['type'] == e['box']['hit'])
    gate('%s random drive: every attack-box hit equals the ROM row' % C.NAMES[ch], ok, tot)
def g_slam():
    ok = 0; got = []
    for b in (68, 74, 80):
        h = [x for x in C.hits('ch2_g4_%d' % b) if x[1] < 0]
        g = [(-d, t63, ds) for rel, d, id22, t63, r, ds in h]
        got.append(g); ok += (g == [(70, 5, 1200)])
    gate('Haggar grapple jump slam: -70, type 5, +1200', ok, 3, str(got))
if __name__ == '__main__':
    chars = [int(a) for a in sys.argv[1:]] or [0, 1, 2]
    speeds = {}
    for ch in chars:
        for g in (g_combo, g_jump, g_special, g_strike, g_throw, g_flip, g_wall, g_rand):
            try: g(ch)
            except Exception as e: gate('%s %s' % (C.NAMES[ch], g.__name__), 0, 1, 'error %r' % (e,))
        speeds[ch] = g_walk(ch)
    if 2 in chars:
        try: g_slam()
        except Exception as e: gate('Haggar slam', 0, 1, 'error %r' % (e,))
    if len(speeds) == 3: gate('walk speed order Guy > Cody > Haggar', int(speeds[0] > speeds[1] > speeds[2]), 1, str({C.NAMES[k]: round(v, 3) for k, v in speeds.items()}))
    print('%d/%d gates PASS' % (sum(1 for n, o, t in res if o == t and t), len(res)))
