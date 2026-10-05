#!/usr/bin/env python3
"""gates.py [gate ...] : agent B (pass 5) gates over the outputs of gates.sh (out/). Prints one line per gate: counts and PASS/FAIL. Run with M68000/.venv/bin/python."""
import os, re, sys, hashlib, collections
here = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(here, '..', '..', '..', '..')); base = os.environ.get('FFB_BASE') or os.path.join(root, 'scratchpad', 'finalfight', 'engine')
OUT = os.path.join(base, 'out')
RUNS = os.path.join(base, 'runs')
results = []
def rd(p):
    try: return open(os.path.join(OUT, p)).read()
    except OSError: return None
def rep(name, ok, text):
    results.append(ok)
    print('%-5s %-18s %s' % ('PASS' if ok else 'FAIL', name, text))
def gate(fn):
    GATES[fn.__name__[2:]] = fn   # not .replace('g_', ''): it also rewrites the 'g_' inside 'ring_static'
    return fn
GATES = {}

@gate
def g_region():
    t = rd('g_region.txt')
    if not t: return rep('region', False, 'no g_region.txt (run gates.sh static)')
    ok1 = 'region word $726e0 = 0002' in t
    pl = re.search(r'placement trigger lists.*?(\d+) shifted pointers, (\d+) other differing bytes', t)
    sc = re.search(r'stage scripts.*?(\d+) shifted pointers, (\d+) other differing bytes', t)
    ok = ok1 and pl and sc and pl.group(2) == '4' and sc.group(2) == '0'
    rep('region', bool(ok), 'word=2; placement sets differ in %s bytes (2 entries), script sets in %s bytes (%s shifted pointers)' % (pl.group(2) if pl else '?', sc.group(2) if sc else '?', sc.group(1) if sc else '?'))

@gate
def g_ring_static():
    t = rd('ringtable.txt')
    if not t: return rep('ring_static', False, 'no ringtable.txt')
    rows = [l.split(None, 3) for l in t.splitlines() if l.strip()]
    types = collections.Counter()
    for r in rows:
        m = re.match(r'([0-9a-f]{2}):([0-9a-f]{2})', r[2]) if len(r) > 2 else None
        types[int(m.group(1), 16) if m else -1] += 1
    ok = len(rows) == 120 and types.get(9, 0) == 0 and types.get(12, 0) == 0
    rep('ring_static', ok, '%d call sites of $2874; by type %s (types 9 and 12: none)' % (len(rows), dict(sorted(types.items()))))

@gate
def g_ring_live():
    t = rd('g_ring_tap.txt'); h = rd('g_ring_hits.txt')
    if not t or not h: return rep('ring_live', False, 'missing g_ring_tap.txt / g_ring_hits.txt')
    prod = [l for l in t.splitlines() if 'pc=00287c' in l]
    cons = [l for l in t.splitlines() if 'pc=004b80' in l]
    cmds = [re.search(r'd=([0-9a-f]{4})', l).group(1) for l in prod]
    hits = dict(l.split() for l in h.splitlines() if l.strip())
    sndq = [l for l in t.splitlines() if 'pc=000a00' in l]; sndl = [l for l in t.splitlines() if 'pc=0009b2' in l]
    ok = len(prod) == 15 and len(cons) == 15 and hits.get('4b94') == '15' and hits.get('4be4') == '1' and hits.get('4c08') == '2' and hits.get('13ba') == '1' and hits.get('2738') == '2' \
        and '0039' in cmds and '0040' in cmds and len(sndq) == len(sndl) and len(sndq) > 0
    rep('ring_live', ok, 'cold boot to frame 2300: %d writes (pc $287c), %d consumed (pc $4b80), %d dispatches ($4b94), task creates $13ba %s $2738 %s; commands %s; sound ring %d queued / %d latch writes' % (len(prod), len(cons), int(hits.get('4b94', 0)), hits.get('13ba'), hits.get('2738'), ' '.join(cmds), len(sndq), len(sndl)))

def shake_check(name):
    import numpy as np
    from PIL import Image
    log = open(os.path.join(OUT, name, 'shake.log')).read().splitlines()
    cam = {}; reg = {}
    flagl = []
    for l in log:
        m = re.match(r'r=(\d+) f=\d+ st=\S+ cam=([0-9a-f]+),([0-9a-f]+) c2y=([0-9a-f]+).* flag=(\d)', l)
        if m:
            r = int(m.group(1)); y = int(m.group(3), 16); y = y - 65536 if y > 32767 else y
            cam[r] = y
            if m.group(5) == '1': flagl.append(r)
            m2 = re.search(r'800112=([0-9a-f]+)', l); m3 = re.search(r'800116=([0-9a-f]+)', l)
            reg[r] = (int(m2.group(1), 16) - 0x300 if m2 else 0, int(m3.group(1), 16) - 0x620 if m3 else 0)
    snap = os.path.join(RUNS, 'run_' + name, 'snap')
    ld = lambda r: np.asarray(Image.open(os.path.join(snap, 'sh_%03d.png' % r)).convert('RGB')).astype(np.int16)
    ref = ld(5)
    def shift(img):
        best = None
        for dy in range(-6, 7):
            y0, y1 = max(32, 32 + dy), min(224, 224 + dy)
            d = np.abs(ref[y0 - dy:y1 - dy] - img[y0:y1]).sum() / (y1 - y0)
            if best is None or d < best[0]: best = (d, dy)
        return best[1]
    ok = n = nz = 0
    for r in range(6, 41):
        if r - 2 in cam:
            n += 1; dy = shift(ld(r)); ok += (dy == cam[r - 2]); nz += (cam[r - 2] != 0)
    amps = [abs(cam[r]) for r in sorted(cam) if cam[r] != 0]
    return ok, n, nz, amps, (min(flagl), max(flagl)) if flagl else None, sum(1 for r in reg if reg[r][0]), sum(1 for r in reg if reg[r][1])

@gate
def g_shaker():
    try:
        out = {}
        for ch in (0, 2, 4): out[ch] = shake_check('g_shc%d' % ch)
    except Exception as e:
        return rep('shaker', False, 'cannot evaluate: %r' % e)
    seq = [4, 3, 3] + [2] * 6 + [1] * 4
    ok = all(v[0] == v[1] == 35 and v[3] == seq and v[5] == 13 for v in out.values()) and out[0][6] == 0 and out[2][6] == 13 and out[4][6] == 0
    rep('shaker', ok, 'rendered playfield shift = camera y two frames earlier: ch0 %d/%d, ch2 %d/%d, ch4 %d/%d; amplitude sequence %s (13 frames); scroll-2 Y reg frames changed %d/%d/%d, scroll-3 Y reg frames changed %d/%d/%d; record live frames r=%s' %
        (out[0][0], out[0][1], out[2][0], out[2][1], out[4][0], out[4][1], out[0][3], out[0][5], out[2][5], out[4][5], out[0][6], out[2][6], out[4][6], out[0][4]))

@gate
def g_haggar():
    exp = {'pd_0300': 0x02ce, 'pd_0065': 0x0033, 'pd_0064': 0x0032, 'pd_0019': 0x000c, 'pd_0018': 0xffff, 'sl_0300': 0x02ba, 'sl_008d': 0x0047, 'sl_008c': 0x0046, 'sl_001f': 0x000f, 'sl_001e': 0xffff}
    ok = 0; bad = []
    for k, v in exp.items():
        t = rd('g_%s/taps.txt' % k)
        if not t: bad.append(k + ':missing'); continue
        hp = [(re.search(r'pc=([0-9a-f]+)', l).group(1), int(re.search(r'd=([0-9a-f]{4})', l).group(1), 16)) for l in t.splitlines() if ' hp a=' in l and re.search(r'pc=0*d9[b-f]|pc=0*da0', l)]
        shk = sum(1 for l in t.splitlines() if 'pc=01b434' in l or 'pc=1b434' in l)
        if hp and hp[0][1] == v and shk >= 1: ok += 1
        else: bad.append('%s:%s' % (k, hp[:1]))
    rep('haggar', ok == len(exp), 'pile driver ($d9b6) and jump slam ($d9e2) victim health matches the pseudocode in %d of %d runs, shaker created in each %s' % (ok, len(exp), bad if bad else ''))

@gate
def g_terrain():
    try:
        import numpy as np
        from PIL import Image
        ld = lambda n, r: np.asarray(Image.open(os.path.join(RUNS, 'run_' + n, 'snap', 'tr_%04d.png' % r)).convert('RGB')).astype(int)
        eq = sum(int(np.abs(ld('g_trS' + c, r) - ld('g_trS0', r)).sum() == 0) for c in '35' for r in (1, 2))
    except Exception as e:
        return rep('terrain', False, 'cannot evaluate: %r' % e)
    def px(n, r):
        t = rd('%s/terr.log' % n) or ''
        m = re.search(r'^r=%d f=\d+ px=([0-9a-f]+)' % r, t, re.M)
        return int(m.group(1), 16) if m else None
    p0, p3, p5 = px('g_trR0', 200), px('g_trR3', 200), px('g_trR5', 200)
    held = all(px('g_trR3', r) == 0x1df for r in (40, 80, 120, 160, 200))
    ok = eq == 4 and held and p0 == 0x3a5 and p5 is not None and p5 > 0x240
    rep('terrain', ok, 'render identical with terrain code 3 or 5 written over 80 tiles: %d of 4 frames; Right held 195 frames: no block x=$%x, code 3 block x=$%x (held from frame 40: %s), code 5 block x=$%x' % (eq, p0 or 0, p3 or 0, held, p5 or 0))

@gate
def g_drums():
    h = rd('g_intro_hits.txt')
    if not h: return rep('drums', False, 'missing g_intro_hits.txt')
    d = dict(l.split() for l in h.splitlines() if l.strip())
    rep('drums', d.get('711a') == '6' and d.get('7156') == '0' and d.get('7aa8') == '0', 'cold-boot intro, frames 1..1900: $711a (DRUMCAN variant >= 2) %s hits, default $7156 %s, award $7aa8 %s' % (d.get('711a'), d.get('7156'), d.get('7aa8')))

def counts(name):
    t = rd('%s/pd.log' % name)
    if not t: return None, None
    return dict((m.group(1), int(m.group(2))) for m in re.finditer(r'^COUNT (\w+) (\d+)', t, re.M)), t

@gate
def g_glass():
    c, t = counts('g_glass')
    if not c: return rep('glass', False, 'missing g_glass')
    hp = [v for v in (int(m.group(1), 16) for m in re.finditer(r'\[\d+ k12 st\d/\d/\d hp([0-9a-f]+)', t)) if v > 0]
    mono = all(a >= b for a, b in zip(hp, hp[1:])) and hp and hp[-1] < hp[0]
    rep('glass', c['7222'] == c['7232'] and c['7222'] >= 10 and c['7220'] == 0 and c['722a'] == 0 and mono, 'bonus stage 1, Cody facing right at the kind-12 pane: $7222 %d, $7232 %d, kinds 11/13 handlers %d/%d; pane health %x -> %x' % (c['7222'], c['7232'], c['7220'], c['722a'], hp[0] if hp else 0, hp[-1] if hp else 0))

@gate
def g_car():
    c, t = counts('g_car')
    if not c: return rep('car', False, 'missing g_car')
    sc = re.findall(r'sc=([0-9a-f]{8})', t)
    rep('car', c['71a2'] == 2 and c['71ba'] == 2 and c['71e2'] == 0 and c['53182'] == 2 and c['531b4'] == 2, 'bonus stage 2 car pane (kind 9): $71a2 %d, accepted $71ba %d, attacker-hurt path $71e2 %d, $53182 %d, hit registered $531b4 %d; score %s -> %s' % (c['71a2'], c['71ba'], c['71e2'], c['53182'], c['531b4'], sc[0] if sc else '?', sc[-1] if sc else '?'))

@gate
def g_shake_sites():
    def cn(n):
        t = rd('k3/%s_hits.txt' % n)
        return dict((a, int(v)) for a, v in (l.split() for l in t.splitlines())) if t else None
    chk = [('g_k3e8', '2d0c2', 1), ('g_k3e10', '2d178', 1), ('g_k3e12', '2d352', 1), ('g_k4e8', '315e0', 1)]
    ok = 0; txt = []
    for n, a, mn in chk:
        c = cn(n)
        if c and c.get(a, 0) >= mn and c['1b428'] >= c[a]: ok += 1
        txt.append('%s:%s=%s' % (n[2:], a, c.get(a) if c else None))
    c = cn('g_k3n1')
    leap = c.get('2de58', 0) if c else 0; carry = c.get('2ed96', 0) if c else 0
    sites = ['1b428', '2d0c2', '2d178', '2d352', '2de58', '2ed96', '315e0', '3ed0e', '426d8', '477bc', '4d550']
    cons = c and c['1b428'] == sum(c[a] for a in sites[1:])
    rep('shake_sites', ok == 4 and leap >= 10 and carry >= 5 and cons, 'entrance landings ' + ' '.join(txt) + '; ANDORE (kind 3 sub 1, 16000 frames, no input): leap landing $2de58 %d, carry slam $2ed96 %d; calls of $1b428 = sum of the site hits: %s' % (leap, carry, bool(cons)))

@gate
def g_edi():
    t = rd('bk/g_edi.log')
    if not t: return rep('edi', False, 'missing bk/g_edi.log')
    c = dict((m.group(1), int(m.group(2))) for m in re.finditer(r'^COUNT (\w+) (\d+)', t, re.M))
    rep('edi', c.get('477bc') == 1 and c.get('1b428') == 1 and 'EXC' not in t, 'EDI.E hand-spawned (allocator contract: +78 kept) and killed by the hp poke: $477bc %s, $1b428 %s, exceptions: %s' % (c.get('477bc'), c.get('1b428'), 'EXC' in t))

@gate
def g_k7():
    t = rd('g_k7/pd.log')
    if not t: return rep('k7', False, 'missing g_k7')
    sts = []
    for l in t.splitlines():
        m = re.search(r'^P4 r=(\d+).*\[7 k7 c0 st(\d\d)/(\d\d)/', l)
        if m: sts.append((int(m.group(1)), m.group(3)))
    first = sts[0][0] if sts else None
    seq = []
    for r, s in sts:
        if not seq or seq[-1] != s: seq.append(s)
    after = re.search(r'^P4 r=9\d\d .* st=2/1 ', t, re.M)
    rep('k7', first is not None and 725 <= first <= 760 and seq[:1] == ['00'] and seq[-1:] == ['06'] and '02' in seq and bool(after), 'stage 2 area 0, 297 poked at r=600: pool-4 kind 7 in slot 7 from r=%s, +3 sequence %s, then stage 2 area 1 starts (record gone)' % (first, seq))

@gate
def g_elevator():
    t = rd('g_elev/pd.log')
    if not t: return rep('elevator', False, 'missing g_elev')
    n = ok = 0
    for l in t.splitlines():
        if not l.startswith('ACT'): continue
        m = re.search(r'P1 x=\w+ y=(\w+) .*\| b0=01 k=01 st=02/02/04/02 x=\w+ y=(\w+)', l)
        if m:
            n += 1; ok += (int(m.group(1), 16) - int(m.group(2), 16) == 3)
    rep('elevator', n >= 700 and ok == n, 'stage 5 area 0 actor (type 12 kind 1) at its carry step: player y = actor y + 3 in %d of %d frames' % (ok, n))

@gate
def g_elevator0():
    t = rd('g_elev0/pd.log')
    if not t: return rep('elevator0', False, 'missing g_elev0')
    y = {}; flag = None; spd = None
    for l in t.splitlines():
        m = re.match(r'ACT r=(\d+) .*? st=3/1 .*?279=(\w+) 280=\w+ 284=(\w+) cam=\w+,\w+ 1116=(\w+)', l)
        if m:
            r = int(m.group(1)); y[r] = int(m.group(4), 16)
            if m.group(2) == '01' and flag is None: flag = r
            if m.group(3) == '00010000' and spd is None: spd = r
    if not y or flag is None or spd is None: return rep('elevator0', False, 'no stage 3 area 1 samples')
    rs = [r for r in sorted(y) if spd + 10 <= r <= spd + 350 and r + 1 in y]
    jit = [r for r in sorted(y) if r > spd + 350 and r + 1 in y and y[r + 1] - y[r] != 1]
    steps = collections.Counter(y[r + 1] - y[r] for r in rs)
    rep('elevator0', steps.get(1, 0) == len(rs) and len(rs) >= 300, 'stage 3 area 1 actor (type 12 kind 0): 279(A5) set at r=%d, 284(A5) = $10000 at r=%d, camera-y copy 1116(A5) +1 per frame in %d of %d frames (r=%d..%d); %d later frames deviate (a shaker, ch 4, in the same run)' % (flag, spd, steps.get(1, 0), len(rs), spd + 10, spd + 350, len(jit)))

@gate
def g_states():
    ok = 0; txt = []
    for k in ('bs7', 'k7s', 's5'):
        hs = []
        for rep_ in (1, 2):
            p = os.path.join(OUT, 'g_%s_%d' % (k, rep_), 'pd.log.p5b_%s.ram' % {'bs7': 'bs7', 'k7s': 'k7', 's5': 's5pre'}[k])
            hs.append(hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16] if os.path.exists(p) else None)
        ok += (hs[0] is not None and hs[0] == hs[1]); txt.append('%s %s' % (k, hs[0]))
    rep('states', ok == 3, 'work RAM hash over two runs: ' + ', '.join(txt))

@gate
def g_sound():
    p = os.path.join(OUT, 'z80sweep_full.txt')
    if not os.path.exists(p): return rep('sound', False, 'no z80sweep_full.txt (gates.sh sound)')
    lines = open(p).read().splitlines()
    marks = []; evs = []
    for l in lines:
        m = re.match(r'f=(\d+) S id=([0-9a-f]+)', l)
        if m: marks.append((int(m.group(1)), int(m.group(2), 16))); continue
        m = re.match(r'f=(\d+) Z w a=f002 d=([0-9a-f]+)', l)
        if m: evs.append((int(m.group(1)), int(m.group(2), 16)))
    good = 0; seen = 0
    for i, (f, d) in enumerate(marks):
        if d > 0x3f: continue
        end = min(f + 150, marks[i + 1][0] - 41) if i + 1 < len(marks) else f + 150
        bytes_ = [b for (ff, b) in evs if f <= ff < end]
        starts = [b & 0x7f for b in bytes_ if b & 0x80]
        seen += 1; good += (d + 1) in starts
    # folding: the other sweeps show ids $60..$ef behave as id mod $60
    fold = fseen = 0
    for n in 'ABC':
        q = os.path.join(OUT, 'z80sweep_%s.txt' % n)
        if not os.path.exists(q): continue
        mk = []; ev2 = []
        for l in open(q).read().splitlines():
            m = re.match(r'f=(\d+) S id=([0-9a-f]+)', l)
            if m: mk.append((int(m.group(1)), int(m.group(2), 16))); continue
            m = re.match(r'f=(\d+) Z w a=f002 d=([0-9a-f]+)', l)
            if m: ev2.append((int(m.group(1)), int(m.group(2), 16)))
        for i, (f, d) in enumerate(mk):
            if d < 0x60 or d >= 0xf0 or d % 0x60 >= 0x40: continue
            end = min(f + 150, mk[i + 1][0] - 41) if i + 1 < len(mk) else f + 150
            st = [b & 0x7f for (ff, b) in ev2 if f <= ff < end and b & 0x80]
            fseen += 1; fold += (d % 0x60 + 1) in st
    rep('sound', seen == 64 and good == 64 and fseen == 112 and fold == 112, 'Z80 response to ids $00..$3f: OKI phrase id+1 started in %d of %d; ids $60..$ef with id mod $60 < $40: phrase (id mod $60)+1 in %d of %d' % (good, seen, fold, fseen))

if __name__ == '__main__':
    names = sys.argv[1:] or list(GATES)
    for n in names: GATES[n]()
    print('%d of %d gates pass' % (sum(results), len(results)))
