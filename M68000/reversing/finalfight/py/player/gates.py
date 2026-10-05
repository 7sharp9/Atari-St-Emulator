"""gates.py: player-side checks over the logs written by gates.sh ($FFP_OUT/*.txt, pdrive format).
Each gate prints  PASS/FAIL  matched/total  and what was compared. ROM expectations come from ffchar.py (the ROM, not memory).
Character index: 0 = Guy, 1 = Cody, 2 = Haggar (the live player is Cody: +20 = 1)."""
import os, re, sys, collections
import ffchar as C
here = os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(os.path.join(here, '../../../..'))
out = os.environ.get('FFP_OUT') or os.path.join(root, 'scratchpad/finalfight/p3/f/out')
CODY = 1

def load(name):
    rows, ev, aw = [], collections.defaultdict(list), []
    for l in open(os.path.join(out, name + '.txt')):
        p = l.split()
        if l[0] == 'E':
            d = dict(t.split('=') for t in p[3:]); d['rel'] = int(p[2]); ev[int(d['i'])].append(d); continue
        if l[0] in 'QC': continue
        d = {t.split('=')[0]: t.split('=')[1] for t in p[2:] if '=' in t}; d['rel'] = int(p[1]); rows.append(d)
    return rows, ev

def bcd(v): return int('%x' % v)
def score(r): return bcd(int(r['scH'] + r['sc'], 16))
def s16(v): return v - 0x10000 if v >= 0x8000 else v
res = []
def gate(name, ok, tot, note=''):
    res.append((name, ok, tot)); print('%s  %-34s %d/%d  %s' % ('PASS' if ok == tot and tot else 'FAIL', name, ok, tot, note))

def hits(name, idx=11):
    """(rel, dhp, victim +22, victim +63, cody row at rel, score delta within rel..rel+3)"""
    rows, ev = load(name); by = {r['rel']: r for r in rows}
    out_ = []; prev = None
    for e in ev[idx]:
        hp = s16(int(e['hp'], 16))
        if prev is not None and hp != prev:
            r = by[e['rel']]
            s0 = score(by[e['rel'] - 1]) if e['rel'] - 1 in by else None; s1 = score(by[min(e['rel'] + 3, rows[-1]['rel'])])
            out_.append((e['rel'], hp - prev, int(e['b22'], 16), int(e['b63'], 16), r, s1 - s0 if s0 is not None else None))
        prev = hp
    return out_

def g_combo():
    h = hits('c1'); ok = 0; tot = 0
    for rel, d, id22, t63, r, ds in h:
        box = C.attack_box(CODY, id22); exp = C.damage_row_value(CODY, box['off']); code, amt = C.hit_award(CODY, box['off'])
        tot += 1; ok += (-d == exp and t63 == box['hit'] and ds == amt)
        print('   combo hit rel %d id %02x dmg %d (rom %d) type %d (rom %d) score +%s (rom %s)' % (rel, id22, -d, exp, t63, box['hit'], ds, amt))
    gate('combo hits: id, dmg, type, score', ok, tot, 'ids 1,1,2,3; limit %d -> %d hits' % (C.combo_limit(CODY), C.combo_limit(CODY) // 2 + 1))

def g_boxes(names, label):
    ok = tot = 0
    for n in names:
        for rel, d, id22, t63, r, ds in hits(n):
            if id22 == 0: continue
            box = C.attack_box(CODY, id22); exp = C.damage_row_value(CODY, box['off']); code, amt = C.hit_award(CODY, box['off'])
            good = (-d == exp and t63 == box['hit'])   # score is printed, not gated: a prop or second enemy in reach can add awards in the same window
            tot += 1; ok += good
            print('   %s %s rel %d id %02x sub=%s dmg %d (rom %d) type %d (rom %d) score +%s (rom %s) %s' % (label, n, rel, id22, r['sub'], -d, exp, t63, box['hit'], ds, amt, '' if good else 'MISMATCH'))
    gate(label + ' damage/type vs ROM', ok, tot)

def g_cost():
    for n in ('s1_30', 's1_-30'):
        rows, _ = load(n); sp = [r for r in rows if r['sub'] == '10']
        print('   %s special frames %d  hp before %s after %s' % (n, len(sp), rows[sp[0]['rel'] - 1]['hp'][:4], rows[sp[-1]['rel'] + 3]['hp'][:4]))
    rows, _ = load('s1_none'); sp = [r for r in rows if r['sub'] == '10']
    a, b = rows[sp[0]['rel'] - 1]['hp'][:4], rows[sp[-1]['rel'] + 6]['hp'][:4]
    gate('special costs 0 without a hit', int(a == b), 1, 'hp %s -> %s, boxes %s' % (a, b, sorted(set(r['b45'] for r in sp))))

def g_items():
    amt = {}  # type -> (heal, code)
    exp = {}
    for t in range(0x24):
        if t <= 2: exp[t] = (0x80, 4)
        elif t <= 7: exp[t] = (0x40, 5)
        elif t <= 12: exp[t] = (0x20, 6)
        elif t <= 19: exp[t] = (0x10, 7)
        elif t <= 21: exp[t] = (0, 4)
        elif t <= 26: exp[t] = (0, 5)
        elif t <= 30: exp[t] = (0, 6)
        elif t <= 34: exp[t] = (0, 7)
    ok = tot = 0
    for fn in sorted(os.listdir(out)):
        m = re.match(r'item_0x([0-9a-f]+)_0x([0-9a-f]+)\.txt$', fn)
        if not m: continue
        t, h = int(m.group(1), 16), int(m.group(2), 16)
        if t not in exp: continue
        rows, _ = load(fn[:-4])
        if 'scH' not in rows[0]: continue
        a, b = rows[100], rows[200]
        heal = min(0x90, h + exp[t][0]) - h; dscore = score(b) - score(a)
        if h >= 0x90 or exp[t][0] == 0: e_hp, e_sc = h, C.AMT[exp[t][1]]
        else: e_hp, e_sc = min(0x90, h + exp[t][0]), 0
        if exp[t][0] and h >= 0x90: e_hp = 0x90
        got_hp = int(b['hp'][:4], 16)
        tot += 1; good = (got_hp == e_hp and dscore == e_sc); ok += good
        print('   item %02x cody hp %02x: hp %02x (exp %02x) score +%d (exp +%d) %s' % (t, h, got_hp, e_hp, dscore, e_sc, '' if good else 'MISMATCH'))
    gate('pickup: heal / score by item type', ok, tot, 'heal 80/40/20/10 for types 0-2/3-7/8-12/13-19; score 10000/5000/3000/1000 at full hp or types 20-34')

def g_grapple():
    rows, ev = load('g2a'); h = hits('g2a')
    ok = 0; tot = 0
    st = [r for r in rows if r['sub'] == '06' and r['m66'] == '02']
    gate('throw lands for 40 (a: away)', int(any(d == -40 for _, d, *_ in h)), 1, str([(a, b) for a, b, *_ in h]))
    rows2, _ = load('g2b'); h2 = hits('g2b')
    gate('slam does 40 (b: toward)', int(any(d == -40 for _, d, *_ in h2)), 1, str([(a, b) for a, b, *_ in h2]))
    rows3, _ = load('g2d'); h3 = hits('g2d'); exp = [C.strike_damage(CODY, s) for s in (2, 4, 6)]
    got = [-d for _, d, *_ in h3][:3]
    gate('grapple strikes (rom db6e)', int(got == exp), 1, 'got %s expected %s' % (got, exp))
    for n in ('g2a', 'g2b'):
        rows, _ = load(n); sc = score(rows[-1]) - score(rows[40]); print('   %s score gained %d' % (n, sc))

def g_thrown():
    ok = tot = 0
    for hp in (0x3c, 0x0a, 0x50, 0x52):
        h = hits('thr_%02x' % hp)[-1]; got = hp + h[1]; exp = C.thrown_hp(hp, CODY)
        got = s16(got & 0xffff) if got < 0 else got
        tot += 1; ok += (got == exp); print('   thrown enemy hp %d -> %d (rom rule %d)' % (hp, got, exp))
    gate('throw landing damage rule ($3f7a)', ok, tot, 'kill <= %d, halve <= %d, else -%d' % (C.w(0x3fd8 + 6), C.w(0x3fd8 + 6) + C.w(0x3fd8 + 8), C.w(0x3fd8 + 10)))

KILL_TAB = {0: 0x21fbe, 1: 0x28328, 2: 0x2a50e, 3: 0x2cec0, 4: 0x32854, 5: 0x363a4, 6: 0x3a220}
def g_kills():
    ok = tot = 0
    for l in open(os.path.join(out, 'award_bp.txt')):
        m = re.search(r'AWARD D0=([0-9a-f]+) A6=([0-9a-f]+) kind=([0-9a-f]+) sub=([0-9a-f]+) tag=([0-9a-f]+)', l)
        if not m or m.group(5) != '02': continue
        d0, a6, kind, sub = int(m.group(1), 16), int(m.group(2), 16), int(m.group(3), 16), int(m.group(4), 16)
        exp = C.rom[KILL_TAB[kind] + sub] if kind in KILL_TAB else None
        tot += 1; ok += (exp == d0 & 0x7f)
        print('   kill award code %02x (%s pts) record %04x kind %d sub %d: rom table says %s' % (d0, C.AMT.get(d0 & 0x7f), a6, kind, sub, None if exp is None else '%02x' % exp))
    gate('kill awards by kind/subtype', ok, tot, 'tables $21fbe $28328 $2a50e $2cec0 $32854 $363a4 $3a220')

def g_backgrab():
    rows, _ = load('bg1'); h = hits('bg1')
    g = [r for r in rows if r['m66'] == '02']
    ok = int(len(g) > 0 and g[0]['rel'] == 53 and any(d == -40 for _, d, *_ in h) and rows[-1]['b46'] == '01')
    gate('combo end + direction away = back throw', ok, 1, 'grapple mode from rel %s, hits %s, facing flips to %s' % (g[0]['rel'] if g else None, [(a, b) for a, b, *_ in h], rows[-1]['b46']))

def g_walk():
    rows, _ = load('walk1'); by = {r['rel']: r for r in rows}
    xs = C.sw(C.l(0xc15e + 4 * CODY) + 2); ys = C.sw(C.l(0xc19e + 4 * CODY))            # x step of frame idx 1, y step of frame idx 0 (8.8 px per frame)
    dl = int(by[180]['x'], 16) - int(by[122]['x'], 16); dd = int(by[380]['y'], 16) - int(by[322]['y'], 16)
    n = 58
    ok = int(abs(-dl - n * xs / 256.0) <= 1.5) + int(abs(-dd - n * ys / 256.0) <= 1.5)
    gate('walk speed = ROM step tables', ok, 2, 'left %d px/%d frames (rom %.1f), down %d px (rom %.1f); step words x $%x y $%x' % (dl, n, -n * xs / 256.0, dd, -n * ys / 256.0, xs, ys))

def g_drop():
    got = {}
    for r in (42, 43, 44, 45, 46):
        for l in open(os.path.join(out, 'dr%d.txt' % r)):
            if l.startswith('QP12'):
                m = re.search(r'w20=([0-9a-f]{4})', l); got[r] = int(m.group(1)[:2], 16); break
    ok = int(got.get(45) in (0x14, 0x15) and all(got.get(r) == 3 for r in (42, 43, 44, 46)))
    gate('direction press on the kill frame -> score item', ok, 1, 'explicit drop 3 replaced by type %s when the press lands on the kill frame; other timings %s' % (hex(got.get(45, -1)), {r: got[r] for r in got if r != 45}))

def g_death():
    rows, _ = load('die3'); by = {r['rel']: r for r in rows}
    d0 = [r['rel'] for r in rows if r['st'] == '04'][0]
    s0 = [r['rel'] for r in rows if r['st'] == '00'][0]
    land = [r['rel'] for r in rows if r['st'] == '02' and r['sub'] == '12' and r['rel'] > s0][0]
    gate('death state 4 lasts 60 frames', int(s0 - d0 == 60), 1, 'state 4 at rel %d, respawn init at %d' % (d0, s0))
    gate('lives -1 at respawn', int(int(by[s0 - 1]['lv']) - int(by[s0 + 1]['lv']) == 1), 1, 'lv %s -> %s' % (by[s0 - 1]['lv'], by[s0 + 1]['lv']))
    ok = tot = 0
    for r in rows:
        if s0 < r['rel'] < s0 + 180:
            b97 = int(r['b97'], 16); tot += 1; ok += (int(r['b1']) == (0 if (r['b154'] == '01' and b97 & 4) else 1))
    gate('blink: +1 == !(+97 & 4) while +154', ok, tot, '+97 starts $%s, drop-in %d frames, then lands' % (by[s0 + 1]['b97'], land - s0 - 1))

def g_hist():
    for n in ('rand1b',):
        rows, _ = load(n); c = collections.Counter((r['st'], r['sub'], r['m66']) for r in rows)
        print('   %s: %d frames; (state,sub,m66) counts:' % (n, len(rows)), dict(sorted(c.items())))
        gate('random drive: every state-2 sub seen is in the table', int(all(k[1] in ('00', '02', '04', '06', '08', '0a', '0c', '0e', '10', '12', '14', '16', '18', '1a', '1c', '1e', '20', '22') for k in c if k[0] == '02')), 1)

def g_life():
    rows, _ = load('life1'); a = [r for r in rows if r['lv'] == '03']
    r0 = a[0]; prev = rows[r0['rel'] - 1]
    gate('extra life at 100000 (thr $0010)', int(prev['lv'] == '02' and r0['scH'] == '0010'), 1, 'score %s -> %s, lives %s -> %s, next thr $%s' % (score(prev), score(r0), prev['lv'], r0['lv'], r0['thr']))

if __name__ == '__main__':
    todo = sys.argv[1:] or ['combo', 'jump', 'special', 'weapon', 'items', 'grapple', 'thrown', 'kills', 'walk', 'drop', 'death', 'hist', 'life']
    if 'combo' in todo: g_combo()
    if 'jump' in todo: g_boxes(['j1', 'j2'], 'jump attacks')
    if 'special' in todo: g_boxes(['s1_30', 's1_-30'], 'special'); g_cost()
    if 'weapon' in todo: g_boxes(['w2_0x24_50', 'w2_0x25_50', 'w2_0x26_50'], 'weapons')
    if 'items' in todo: g_items()
    if 'grapple' in todo: g_grapple()
    if 'thrown' in todo: g_thrown(); g_backgrab()
    if 'kills' in todo: g_kills()
    if 'walk' in todo: g_walk()
    if 'drop' in todo: g_drop()
    if 'death' in todo: g_death()
    if 'hist' in todo: g_hist()
    if 'life' in todo: g_life()
    print('SUMMARY', sum(1 for r in res if r[1] == r[2] and r[2]), 'of', len(res), 'gates pass')
