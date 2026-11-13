#!/usr/bin/env python3
"""Infographic: Captive's base digger $244b6 and the flow field $24f4c (reversing/captive/mapgen.md, "The digger and
rooms", "The flow field (plane 2)").

    uv run python -I reversing/captive/py/infographics/gen_digger.py [outdir]     (default scratchpad/captive/infographics)

Writes digger.svg and prints every number it draws. Sources, all computed here:
  - one seed (SEED, D2 = 1): the emulator's module block before and after $244b6 from the capture
    scratchpad/captive/mapgen_digger/d2_1_0.bin (digger/dig_capture.py). The port digger/dig.py is run on the pre
    block, instrumented by subclassing (dig.py is not edited); the script asserts its whole post block and D1-D7 equal
    the emulator's, byte for byte.
  - the flow field: the emulator's final G2 for the same seed from gen.py (seed<SEED>.json in scratchpad/captive/infographics/data;
    made with `gen.py <data>/seed5.json 5,0,1,0` when missing, which starts and closes one stserver), checked against
    flowfield.model on the port's post-digger grids.
  - the loop census: digger/tree.py's census over the 1000 captured D2 = 1 seeds, parsed from its own printout, and
    a corpus count of retried room words, both from the port on the emulator's captures (every run asserted equal).
Facts and sources: digger.facts.md.
"""
import contextlib
import io
import json
import math
import os
import re
import subprocess
import sys
import html
import textwrap
from collections import Counter


def root():
    d = os.environ.get('M68000_ROOT') or os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
        p = os.path.dirname(d)
        if p == d:
            sys.exit('repo root (tools/rdis.py) not found')
        d = p
    return d


R = root()
MG = os.path.join(R, 'reversing', 'captive', 'py', 'mapgen')
sys.path.insert(0, os.path.join(MG, 'digger'))
sys.path.insert(0, MG)
import dig  # noqa: E402
import flowfield  # noqa: E402
import tree  # noqa: E402
from dig_capture import records  # noqa: E402

CAP = os.path.join(R, 'scratchpad', 'captive', 'mapgen_digger')
CAPS = [os.path.join(CAP, f'd2_1_{b}.bin') for b in (0, 250, 500, 750)]
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(R, 'scratchpad', 'captive', 'infographics')
DATA = os.path.join(R, 'scratchpad', 'captive', 'infographics', 'data')
os.makedirs(OUT, exist_ok=True)
os.makedirs(DATA, exist_ok=True)
SEED = 5
G0, G1 = 56, 4168
BLOB_MAX, ROOM_MAX, LIFT_MIN = 0x7ad, 0x8f48, 0xccb0     # $24872: cmp.w against the step word 12426(A6)


class Traced(dig.Dig):
    """dig.Dig with observers only: every method calls the port's own and records what happened."""

    def __init__(self, block):
        super().__init__(block)
        self.carves = []        # (number, x, y, kind) in carve order
        self.steps = []         # one dict per call of $24872
        self.lifts = []         # ((x, y, floor) near, (x, y, floor) far, up)
        self.cur = None
        self.dec_pending = False
        self.restart_dec = 0    # decrements of the restart counter 12414(A6)
        self.restart_lift = 0   # restarts that were lift attempts from a carved cell ($2458a)
        self.tests = []         # the main loop's carve tests: position, uncarved count, G0 at that moment

    def SW(self, o, v):
        if o == 12414 and ((self.W(12414) - v) & 0xffff) == 1:
            self.restart_dec += 1
            self.dec_pending = True
        super().SW(o, v)

    def rng(self):
        self.dec_pending = False
        return super().rng()

    def carve(self, tag=('corr', None)):
        self.dec_pending = False
        self.carves.append((self.d4, self.d1, self.d2, tag[0]))
        if self.cur is not None:
            self.cur['made'].add(tag[0])
        super().carve(tag)

    def step(self):
        rec = {'word': self.W(12426), 'sel': self.d0 & 7, 'fresh': self.d7 == 9, 'call': 'move', 'made': set(),
               'restart': self.dec_pending}
        if rec['restart']:
            self.restart_lift += 1
        self.dec_pending = False
        self.steps.append(rec)
        self.cur = rec
        super().step()
        self.cur = None
        self.after_step = self.d5 != 0xffff     # the next count() is $244b6's carve test ($24514)

    def count(self):
        test = getattr(self, 'after_step', False)
        self.after_step = False
        super().count()
        if test:
            g = [self.W(G0 + 2 * i) for i in range(2048)]
            self.tests.append({'pos': (self.d1, self.d2), 'n': self.d6, 'g0': g,
                               'from': (self.W(48), self.W(50)), 'step': len(self.steps) - 1})

    def lift(self, up):
        self.cur['call'] = 'lift'
        near = (self.d1, self.d2, self.d3)
        super().lift(up)
        if self.d5 == 0xffff:
            self.lifts.append((near, (self.d1, self.d2, self.d3), up))

    def structure(self):
        self.cur['call'] = 'blob'
        super().structure()

    def room(self):
        self.cur['call'] = 'room'
        super().room()


def word_class(sel, word):
    """What $24872 does with a fresh word: low 3 bits 0/1 turn; 2/3 a lift when word > $ccb0; else by size."""
    if sel in (0, 1):
        return 'turn'
    if sel in (2, 3) and word > LIFT_MIN:
        return 'lift'
    if word <= BLOB_MAX:
        return 'blob'
    if word <= ROOM_MAX:
        return 'room'
    return 'forward'


def run_checked(pre, post, regs, cls=Traced):
    d = cls(pre)
    end = d.run()
    assert bytes(d.m) == post, 'port block != emulator block'
    assert [d.d1, d.d2, d.d3, d.d4, d.d5, d.d6, d.d7] == [r & 0xffff for r in regs[1:8]], 'D1-D7 differ'
    return d, end


# ---- the seed ----------------------------------------------------------------------------------------------------
rec = next(r for r in records(CAPS[0]) if r[0] == SEED)
seed, d2, emu_steps, regs, pre, post = rec
assert d2 == 1
d, end = run_checked(pre, post, regs)
W = lambda o: (d.m[o] << 8) | d.m[o + 1]
S = lambda o: W(o) - 0x10000 if W(o) & 0x8000 else W(o)
g0 = [W(G0 + 2 * i) for i in range(2048)]
feat = [d.m[G1 + 2 * i + 1] for i in range(2048)]
floor = [d.m[((i >> 6) >> 3) * 4 + ((i & 63) >> 4)] for i in range(2048)]
carved = [0 < v < 0xff00 for v in g0]
nfloors = S(46)
ex, ex_floor = W(32), W(34)
offs = [(S(16 + 2 * k), S(24 + 2 * k)) for k in range(nfloors - 1)]
kinds = Counter(k for *_, k in d.carves)
blocks = Counter(v for v in d.m[0:16] if v != 6)
maxn = max(v for v in g0 if 0 < v < 0xff00)
pre_cells = [i for i in range(2048) if carved[i] and i not in d.tag]
n_rooms = len({t[1] for t in d.tag.values() if t[0] == 'room'})
n_blobs = len({t[1] for t in d.tag.values() if t[0] == 'blob'})
lift_used = 900 - S(12416)
print(f'seed D0={seed} D2=1: port = emulator capture on the whole module block ({len(post)} bytes) and D1-D7; '
      f'ended on the {end} budget; capture step field {emu_steps:,} (not used: see facts, Flags)')
print(f'  floors {nfloors}, blocks {sum(blocks.values())} {dict(blocks)}, entrance column {ex} floor {ex_floor}, '
      f'lift offsets {offs}')
print(f'  carves {len(d.carves)} {dict(kinds)}; carved cells {sum(carved)}; pre-placed {len(pre_cells)}; '
      f'highest carve number {maxn}; final D4 {d.d4}')
print(f'  rooms {n_rooms}, blobs {n_blobs}, lifts {len(d.lifts)}; in-bounds lift attempts {lift_used}; '
      f'restart-counter decrements {d.restart_dec} (lift restarts {d.restart_lift})')
assert kinds['lift'] == len(d.lifts)

# ---- steps and words (panel C) -----------------------------------------------------------------------------------
fresh = [r for r in d.steps if r['fresh']]
retry = [r for r in d.steps if not r['fresh'] and not r['restart']]
fc = Counter(word_class(r['sel'], r['word']) for r in fresh)
p_turn = 2 / 8
w_blob = (BLOB_MAX + 1) / 65536
w_room = (ROOM_MAX - BLOB_MAX) / 65536
w_fwd = (LIFT_MIN - ROOM_MAX) / 65536
w_top = (65535 - LIFT_MIN) / 65536
prob = {'turn': p_turn, 'lift': 2 / 8 * w_top, 'blob': 6 / 8 * w_blob, 'room': 6 / 8 * w_room,
        'forward': 6 / 8 * w_fwd + 4 / 8 * w_top}
assert abs(sum(prob.values()) - 1) < 1e-9
made = {k: sum(1 for r in d.steps if k in r['made'] and r['call'] == k) for k in ('lift', 'blob', 'room')}
made_fresh = {k: sum(1 for r in fresh if k in r['made'] and r['call'] == k) for k in ('lift', 'blob', 'room')}
calls_retry = Counter(r['call'] for r in retry)
made_retry = {k: sum(1 for r in retry if k in r['made'] and r['call'] == k) for k in ('lift', 'blob', 'room')}
assert made['room'] == n_rooms and made['blob'] == n_blobs and made['lift'] == len(d.lifts)
print(f'  step calls {len(d.steps)}: fresh words {len(fresh)}, retries {len(retry)}, lift restarts '
      f'{sum(r["restart"] for r in d.steps)}')
print('  band widths: blob %.2f%% room %.2f%% forward %.2f%% top %.2f%%' % (100 * w_blob, 100 * w_room, 100 * w_fwd,
                                                                          100 * w_top))
for k in ('turn', 'lift', 'blob', 'room', 'forward'):
    print(f'    {k:8s} p={prob[k]:.4f} expected {prob[k] * len(fresh):6.1f} seen {fc[k]:4d}  made first try '
          f'{made_fresh.get(k, "-")}  retried calls {calls_retry.get(k, "-")} made on retry {made_retry.get(k, "-")}')

# ---- corpus: retried room and blob words; census -----------------------------------------------------------------
class Light(dig.Dig):
    def __init__(self, block):
        super().__init__(block)
        self.room_retry = self.room_retry_made = self.room_fresh = self.room_fresh_made = 0
        self.fresh_cls = Counter()

    def step(self):
        self.fr = self.d7 == 9
        if self.fr:
            self.fresh_cls[word_class(self.d0 & 7, self.W(12426))] += 1
        super().step()

    def carve(self, tag=('corr', None)):
        if tag[0] == 'room':
            self.rmade = True
        super().carve(tag)

    def room(self):
        self.rmade = False
        super().room()
        ok = self.rmade
        if self.fr:
            self.room_fresh += 1
            self.room_fresh_made += ok
        else:
            self.room_retry += 1
            self.room_retry_made += ok


CACHE = os.path.join(DATA, 'corpus_cache.json')   # only with DIGGER_CACHE=1 (layout iteration); the default recomputes
if os.environ.get('DIGGER_CACHE') == '1' and os.path.exists(CACHE):
    cc = json.load(open(CACHE))
    corp, fresh_all, nbase, ctext = Counter(cc['corp']), Counter(cc['fresh']), cc['nbase'], cc['ctext']
    print('(corpus numbers from the cache', CACHE, ')')
else:
    corp = Counter()
    fresh_all = Counter()
    nbase = 0
    recs = []
    for cap in CAPS:
        for r in records(cap):
            recs.append(r)
            dd, _ = run_checked(r[4], r[5], r[3], Light)
            nbase += 1
            corp['room_retry'] += dd.room_retry
            corp['room_retry_made'] += dd.room_retry_made
            corp['room_fresh'] += dd.room_fresh
            corp['room_fresh_made'] += dd.room_fresh_made
            fresh_all += dd.fresh_cls
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        tree.census(recs)
    ctext = buf.getvalue()
    json.dump({'corp': corp, 'fresh': fresh_all, 'nbase': nbase, 'ctext': ctext}, open(CACHE, 'w'))
print(f'corpus {nbase} seeds (each port block = emulator block): room words first try {corp["room_fresh"]} -> '
      f'{corp["room_fresh_made"]} rooms; retried {corp["room_retry"]} -> {corp["room_retry_made"]} rooms')
print('  fresh words by class over the corpus:', dict(fresh_all), 'total', sum(fresh_all.values()))
print('tree census (digger/tree.py):\n' + ctext)


def cview(name, lname):
    m = re.search(r'%s\s+%s\s+forest \(E - V \+ C = 0\) in (\d+)/(\d+) bases; cycles summed (\d+)' % (
        re.escape(name), re.escape(lname)), ctext)
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


raw = cview('raw', 'no lifts')
rb = cview('rooms+blobs', 'no lifts')
rbl = cview('rooms+blobs', 'lifts')
src = {k: int(v) for k, v in re.findall(r"\('no lifts', '([a-z]+', '[a-z]+)'\): (\d+)", ctext)}
src = {k.replace("', '", '-'): v for k, v in src.items()}
comp1 = re.search(r'components holding digger-carved cells \(rooms\+blobs, lifts\): \{1: (\d+)\}', ctext)
assert comp1 and int(comp1.group(1)) == nbase
assert sum(src.values()) == rb[2]
print('census used: raw', raw, 'rooms+blobs', rb, 'with lifts', rbl, 'sources', src)


# ---- this seed's own loops (same graph and contraction as tree.census) ---------------------------------------------
def seed_cycles(dd, pst):
    cells, ft, adj, lifts, bad = tree.graph(pst)
    out = {}
    for name, contr in (('raw', ()), ('rb', ('room', 'blob'))):
        node = {i: (dd.tag.get(i, ('pre', None)) if dd.tag.get(i, ('pre', None))[0] in contr else i) for i in cells}
        for lname, extra in (('nolift', []), ('lift', lifts)):
            par = {x: x for x in set(node.values())}

            def find(a):
                while par[a] != a:
                    par[a] = par[par[a]]
                    a = par[a]
                return a
            cyc = []
            for a, b in adj + extra:
                na, nb_ = node[a], node[b]
                if na == nb_:
                    continue
                ra, rb_ = find(na), find(nb_)
                if ra == rb_:
                    cyc.append((a, b))
                else:
                    par[ra] = rb_
            out[(name, lname)] = cyc
    return out


sc = seed_cycles(d, post)
print('seed cycles: raw %d, rooms+blobs %d, rooms+blobs with lifts %d; rooms+blobs closing edges %s' % (
    len(sc[('raw', 'nolift')]), len(sc[('rb', 'nolift')]), len(sc[('rb', 'lift')]),
    [((a & 63, a >> 6, d.tag.get(a, ('pre',))[0]), (b & 63, b >> 6, d.tag.get(b, ('pre',))[0]))
     for a, b in sc[('rb', 'nolift')]]))

# ---- flow field: emulator G2 for the seed, model, and walking the arrows -----------------------------------------
jpath = os.path.join(DATA, f'seed{SEED}.json')
if not os.path.exists(jpath):
    subprocess.run([sys.executable, '-I', os.path.join(MG, 'gen.py'), jpath, f'{SEED},0,1,0'], check=True)
o = json.load(open(jpath))[0]
assert o['args'] == [SEED, 0, 1, 0]
g2e = bytes.fromhex(o['g2'])
mdl = flowfield.model(g0, bytes(d.m[G1:G1 + 4096]), bytes(d.m[0:56]), bytes(d.m[13410:13460]))
open_cells = [i for i in range(2048) if mdl[i] is not None]
ff_match = sum(mdl[i] == g2e[2 * i] for i in open_cells)
assert ff_match == len(open_cells)
ff = [g2e[2 * i] for i in range(2048)]
ent = ex                      # row 0
assert ff[ent] == 0


def nxt(i):
    x, y, v = i & 63, i >> 6, ff[i]
    k = floor[i]
    if v == 0:
        x, y = x, y - 1
    elif v == 1:
        x -= 1
    elif v == 2:
        y += 1
    elif v == 3:
        x += 1
    elif v == 4:
        x, y = x + offs[k - 1][0], y + offs[k - 1][1]
    elif v == 5:
        x, y = x - offs[k - 2][0], y - offs[k - 2][1]
    else:
        return None
    return y * 64 + x if 0 <= x < 64 and 0 <= y < 32 else None


reach, longest, lift_rides, nondesc = 0, 0, 0, 0
for i in open_cells:
    j, n, seen = i, 0, set()
    while j != ent and j is not None and j not in seen and n < 5000:
        seen.add(j)
        k = nxt(j)
        if k is not None and ff[j] in (4, 5):
            lift_rides += 1
        if k is not None and g0[k] > g0[j]:
            nondesc += 1
        j, n = k, n + 1
    if j == ent:
        reach += 1
        longest = max(longest, n)
print(f'gen.py whole call for seed {SEED}: {o["steps"]:,} instructions')
print(f'flow field: emulator G2 = model on {ff_match}/{len(open_cells)} open cells; following arrows reaches the '
      f'entrance from {reach}/{len(open_cells)}; longest walk {longest} steps; uphill arrow steps {nondesc}')
assert reach == len(open_cells)


# ---- panel B: a real refusal followed by a carve, from the dig itself -------------------------------------------
best = None
for t0, t1 in zip(d.tests, d.tests[1:]):
    if t0['n'] != 2 or t1['n'] != 3 or t0['from'] != t1['from'] or t1['step'] != t0['step'] + 1:
        continue
    g = t0['g0']
    x, y = t0['pos']
    if not (0 <= x < 64 and 0 <= y < 32) or g[y * 64 + x] != 0:
        continue
    nb_ = [(x + u, y + v) for u, v in ((-1, 0), (1, 0), (0, -1), (0, 1))
           if 0 <= x + u < 64 and 0 <= y + v < 32 and 0 < g[(y + v) * 64 + x + u] < 0xff00]
    if len(nb_) != 2:
        continue
    fx, fy = t0['from']
    other = [q for q in nb_ if q != (fx, fy)]
    if len(other) != 1:
        continue
    gap = abs(g[fy * 64 + fx] - g[other[0][1] * 64 + other[0][0]])
    if best is None or gap > best[0]:
        best = (gap, t0, t1, other[0])
gap, tB0, tB1, cO = best
cX, cY, cF = tB0['pos'], tB1['pos'], tB0['from']
gB = tB0['g0']
nrefuse = sum(1 for t in d.tests if t['n'] != 3)
print(f'carve rule: at test {d.tests.index(tB0)} the turtle on {cF} #{gB[cF[1]*64+cF[0]]} tested {cX}: '
      f'{tB0["n"]} of 4 uncarved (touches {cO} #{gB[cO[1]*64+cO[0]]}, {gap} carves apart): refused; the retry '
      f'tested {cY}: {tB1["n"]} of 4: carved as #{g0[cY[1] * 64 + cY[0]]}')
assert tB1['n'] == 3
nxt_num = max(v for v in gB if 0 < v < 0xff00) + 1
print(f'  carve tests in the dig {len(d.tests)}: passed (3 of 4) {len(d.tests) - nrefuse}, refused {nrefuse}')

# ======================================== SVG ======================================================================
WD, HT = 960, 1554
INK, MUTE, GRID, BAD, GOOD, ROCK = '#1f2328', '#656d76', '#d0d7de', '#cf222e', '#1a7f37', '#eef1f4'
VIR = [(68, 1, 84), (59, 82, 139), (33, 145, 140), (94, 201, 98), (253, 231, 37)]   # viridis anchors


def ramp(v):
    f = min(1.0, max(0.0, (v - 1) / (maxn - 1)))
    k = min(len(VIR) - 2, int(f * (len(VIR) - 1)))
    t = f * (len(VIR) - 1) - k
    return '#%02x%02x%02x' % tuple(round(p + (q - p) * t) for p, q in zip(VIR[k], VIR[k + 1]))


def lum(hexc):
    r, g, b = (int(hexc[i:i + 2], 16) for i in (1, 3, 5))
    return 0.299 * r + 0.587 * g + 0.114 * b


s = []
a = s.append
a('')                                                  # the <svg> header, written once the height is known
a('<title id="t">A turtle that digs a perfect maze</title>')
a('<desc id="d">Captive (Antony Crowther, 1990) digs each base with a turtle that numbers every cell it carves and '
  'digs a cell only when 3 of its 4 neighbours are uncarved; the base generator then points every cell at its '
  'lowest-numbered neighbour, so the arrows lead back to the entrance. Sources: reversing/captive/mapgen.md, the '
  'port py/mapgen/digger/dig.py checked byte for byte against emulator captures, by gen_digger.py. Facts: '
  'digger.facts.md.</desc>')
a('<style>text{font-family:Helvetica,Arial,sans-serif;fill:%s;font-size:12px}.t{font-size:21px;font-weight:bold}'
  '.h{font-size:14px;font-weight:bold}.m{fill:%s}.c{font-family:Menlo,monospace;font-size:11px}'
  '.s{font-size:11px;fill:%s}.ev{font-size:10.5px;fill:%s;font-style:italic}.l{font-size:12.5px}.k{font-size:11px;fill:%s}</style>'
  % (INK, MUTE, MUTE, MUTE, INK))
a('')                                                  # the background, sized with the header
PANELS = {}


def para(x, y, w, txt, cls='s', lh=15, lead=None, cpx=5.3):
    """Wrap txt to w pixels (cpx pixels per character), with an optional bold lead-in. Returns the next baseline."""
    full = (lead + ' ' if lead else '') + txt
    for k, line in enumerate(textwrap.wrap(full, int(w / cpx))):
        body = html.escape(line, quote=False)
        if k == 0 and lead:
            body = '<tspan style="font-weight:bold;fill:%s">%s</tspan>%s' % (INK, html.escape(lead, quote=False),
                                                                             html.escape(line[len(lead):], quote=False))
        a(f'<text x="{x}" y="{y}" class="{cls}">{body}</text>')
        y += lh
    return y


def panel(x, y, w, h, title, ev):
    """Draw a panel's title; close() sizes its frame once its text is laid out."""
    idx = len(s)
    a('')
    PANELS[idx] = (x, y, w)
    a(f'<text x="{x + 14}" y="{y + 24}" class="h">{title}</text>')
    a(f'<text x="{x + 14}" y="{y + 40}" class="ev">evidence: {ev}</text>')
    return idx


def close(idx, bottom):
    x, y, w = PANELS[idx]
    s[idx] = f'<rect x="{x}" y="{y}" width="{w}" height="{bottom - y}" rx="6" fill="none" stroke="{GRID}"/>'
    return bottom


a('<text x="24" y="38" class="t">A turtle that digs a perfect maze</text>')
LEAD = ('Captive (Antony Crowther, Mindscape, 1990) is a real-time dungeon crawler in which four droids raid bases on a '
        'series of planets. Each base is computed by the game\'s generator module, fed_MapGen, from a 16-bit base number '
        'and a mode, and the same pair always gives the same base. Most of the work is one routine ($244b6), a "turtle": '
        'a digger with a position and a heading that draws one random number per step and, from it, turns, moves on, or '
        'drops a room, a looped cave (a "blob") or a lift to another floor (panels A and C). Its one rule, dig a cell only '
        'when 3 of its 4 neighbours are still uncarved (B), makes the corridors a perfect maze: no corridor ever breaks '
        'into another, so on each floor there is exactly one corridor route between two places. Every carved cell keeps '
        'its dig number, and those numbers become arrows that lead back to the entrance (D). The loops a player meets '
        'come from elsewhere (E).')
ly_ = para(24, 62, 912, LEAD, 'l', 17, cpx=6.0)


# ---- A: the map --------------------------------------------------------------------------------------------------
AY = ly_ + 8
C = 13
mx0, my0 = 64, AY + 108
pA = panel(24, AY, 912, 604, f'A. Base {SEED}: every cell coloured by the order it was dug',
      f'port = emulator, whole module block, seed {SEED}')
a(f'<text x="38" y="{AY + 60}" class="s">The turtle starts at the entrance heading east and numbers each cell it '
  f'carves. {nfloors} floors share one 64 x 32 grid, one floor per 16 x 8 block;</text>')
a(f'<text x="38" y="{AY + 74}" class="s">a lift jumps to another floor\'s block at a fixed offset, and the far end '
  f'takes the next number. Pale cells are rock, grey cells are walls between floors.</text>')
for i in range(2048):
    x, y = i & 63, i >> 6
    X, Y = mx0 + C * x, my0 + C * y
    if floor[i] == 6:
        col = '#ffffff'
    elif g0[i] == 0xffff:
        col = '#9aa4ae'
    elif carved[i]:
        col = ramp(g0[i])
    else:
        col = ROCK
    a(f'<rect x="{X}" y="{Y}" width="{C}" height="{C}" fill="{col}"/>')
a(f'<rect x="{mx0}" y="{my0}" width="{64 * C}" height="{32 * C}" fill="none" stroke="{MUTE}" stroke-width="1"/>')
for bi in range(16):
    bx, by = bi % 4, bi // 4
    fv = d.m[bi]
    X, Y = mx0 + 16 * C * bx, my0 + 8 * C * by
    if fv == 6:
        a(f'<text x="{X + 8 * C}" y="{Y + 4 * C + 4}" text-anchor="middle" class="s">outside the base</text>')
        continue
    a(f'<rect x="{X + 2}" y="{Y + 2}" width="22" height="13" rx="2" fill="#ffffff" fill-opacity="0.85"/>')
    a(f'<text x="{X + 13}" y="{Y + 12}" text-anchor="middle" style="font-size:10px;font-weight:bold">F{fv}</text>')
for i in pre_cells:
    x, y = i & 63, i >> 6
    a(f'<rect x="{mx0 + C * x + 1.5}" y="{my0 + C * y + 1.5}" width="{C - 3}" height="{C - 3}" fill="none" '
      f'stroke="{INK}" stroke-width="1.2" stroke-dasharray="2 1.5"/>')
# lifts
for n, ((x0, y0, f0), (x1, y1, f1), up) in enumerate(d.lifts, 1):
    X0, Y0 = mx0 + C * x0 + C / 2, my0 + C * y0 + C / 2
    X1, Y1 = mx0 + C * x1 + C / 2, my0 + C * y1 + C / 2
    mxp, myp = (X0 + X1) / 2, (Y0 + Y1) / 2
    dx, dy = X1 - X0, Y1 - Y0
    L = math.hypot(dx, dy)
    cx, cy = mxp - dy / L * 0.18 * L, myp + dx / L * 0.18 * L
    a(f'<path d="M{X0:.1f},{Y0:.1f} Q{cx:.1f},{cy:.1f} {X1:.1f},{Y1:.1f}" fill="none" stroke="#ffffff" '
      f'stroke-width="3" stroke-opacity="0.8"/>')
    a(f'<path d="M{X0:.1f},{Y0:.1f} Q{cx:.1f},{cy:.1f} {X1:.1f},{Y1:.1f}" fill="none" stroke="{BAD}" '
      f'stroke-width="1.3" stroke-dasharray="4 2.5"/>')
    for X, Y in ((X0, Y0), (X1, Y1)):
        a(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="5" fill="none" stroke="{BAD}" stroke-width="1.8"/>')
# entrance
a(f'<rect x="{mx0 + C * ex - 1}" y="{my0 - 1}" width="{C + 2}" height="{C + 2}" fill="none" stroke="{BAD}" '
  f'stroke-width="2.4"/>')
a(f'<line x1="{mx0 + C * ex + C / 2}" y1="{my0 - 2}" x2="{mx0 + C * ex + C / 2}" y2="{my0 - 10}" stroke="{BAD}" '
  f'stroke-width="1.4"/>')
a(f'<text x="{mx0 + C * ex + C / 2}" y="{my0 - 12}" text-anchor="middle" class="s" style="fill:{BAD}">entrance '
  f'(carved twice: #{g0[ent]})</text>')
# legend row
ly = my0 + 32 * C + 22
lx = mx0
for k in range(120):
    v = 1 + (maxn - 1) * k / 119
    a(f'<rect x="{lx + 2 * k}" y="{ly}" width="2.2" height="11" fill="{ramp(v)}"/>')
a(f'<text x="{lx}" y="{ly + 24}" class="s">1</text><text x="{lx + 240}" y="{ly + 24}" text-anchor="end" '
  f'class="s">{maxn}</text><text x="{lx + 120}" y="{ly + 24}" text-anchor="middle" class="s">carve number</text>')
a(f'<circle cx="{lx + 268}" cy="{ly + 5}" r="5" fill="none" stroke="{BAD}" stroke-width="1.8"/>'
  f'<line x1="{lx + 278}" y1="{ly + 5}" x2="{lx + 300}" y2="{ly + 5}" stroke="{BAD}" stroke-dasharray="4 2.5"/>'
  f'<text x="{lx + 306}" y="{ly + 9}" class="s">a lift: its two ends ({len(d.lifts)} here)</text>')
a(f'<rect x="{lx + 268}" y="{ly + 15}" width="10" height="10" fill="none" stroke="{INK}" stroke-dasharray="2 1.5"/>'
  f'<text x="{lx + 284}" y="{ly + 24}" class="s">shaft cells laid before the dig ({len(pre_cells)})</text>')
summ = [f'{len(d.carves)} carves: {kinds["corr"]} corridor, {kinds["room"]} room ({n_rooms} rooms),',
        f'{kinds["blob"]} blob ({n_blobs} blobs), {kinds["lift"]} lift ends, {kinds["trig"]} shaft,',
        f'entrance {kinds["entry"] + 1}x. The dig ends on its {end[:-1]} budget;',
        f'the whole generator call takes {o["steps"]:,} instructions.']
for k_, t in enumerate(summ):
    a(f'<text x="{lx + 540}" y="{ly + 9 + 14 * k_}" class="s">{t}</text>')
y = para(38, ly + 76, 884, 'Each small square is one cell of the 64 x 32 grid. The grid is cut into 16 blocks of 16 x 8 '
         'cells; each block belongs to one floor (labels F1 to F3) or lies outside the base (white). Colour is the carve '
         f'number: dark purple cells were dug first, yellow last ({maxn} is the highest number given out). Pale cells are '
         'rock that was never dug. A dashed red curve joins the two ends of a lift: the turtle jumps to the same place in '
         'a block of a neighbouring floor and digs on from there. A shaft is a chain of entries on consecutive floors laid out '
         'before the dig; the turtle opens its door when a corridor reaches it.', lead='How to read.')
y = para(38, y + 4, 884, 'This whole map follows from the base number. The generator, ported to Python and run from the '
         'base number and mode alone, reproduces the game\'s output in 400 of 400 bases.', lead='Takeaway.')
close(pA, y + 6)

# ---- B: the carve rule -------------------------------------------------------------------------------------------
BY0 = y + 20
pB = panel(24, BY0, 444, 400, 'B. The carve rule: exactly 3 of 4', 'proven: gate 1000/1000; 2-of-4 control 0/1000')
ww, wh = 7, 5
pts = (cX, cY, cF, cO)
wx0 = (min(q[0] for q in pts) + max(q[0] for q in pts)) // 2 - ww // 2
wy0 = (min(q[1] for q in pts) + max(q[1] for q in pts)) // 2 - wh // 2
wx0 = max(0, min(wx0, 64 - ww))
wy0 = max(0, min(wy0, 32 - wh))
CB = 40
bx0, by0 = 24 + (444 - ww * CB) // 2, BY0 + 54
nY = g0[cY[1] * 64 + cY[0]]
for yy in range(wy0, wy0 + wh):
    for xx in range(wx0, wx0 + ww):
        i = yy * 64 + xx
        X, Y = bx0 + CB * (xx - wx0), by0 + CB * (yy - wy0)
        v = gB[i]
        cv = 0 < v < 0xff00
        col = ramp(v) if cv else ('#9aa4ae' if v == 0xffff else ROCK)
        a(f'<rect x="{X}" y="{Y}" width="{CB}" height="{CB}" fill="{col}" stroke="#ffffff" stroke-width="1"/>')
        if cv:
            tc = '#ffffff' if lum(col) < 140 else INK
            a(f'<text x="{X + CB / 2}" y="{Y + CB / 2 + 4}" text-anchor="middle" class="c" style="fill:{tc}">'
              f'{v}</text>')
X, Y = bx0 + CB * (cF[0] - wx0), by0 + CB * (cF[1] - wy0)
a(f'<rect x="{X + 2}" y="{Y + 2}" width="{CB - 4}" height="{CB - 4}" fill="none" stroke="{INK}" stroke-width="2.4"/>')
for (px, py), colr, lab in ((cX, BAD, '2 of 4'), (cY, GOOD, '3 of 4')):
    X, Y = bx0 + CB * (px - wx0), by0 + CB * (py - wy0)
    a(f'<rect x="{X + 2}" y="{Y + 2}" width="{CB - 4}" height="{CB - 4}" fill="none" stroke="{colr}" '
      f'stroke-width="3"/>')
    a(f'<text x="{X + CB / 2}" y="{Y + CB / 2 + 4}" text-anchor="middle" class="s" style="fill:{colr};'
      f'font-weight:bold">{lab}</text>')
nF, nO = gB[cF[1] * 64 + cF[0]], gB[cO[1] * 64 + cO[0]]
ty = by0 + wh * CB + 22
btxt = [(INK, 'h', f'Base {SEED}, mid-dig: the turtle stands on #{nF} (black).'),
        (BAD, 'h', f'Red: tested first and refused.'),
        (MUTE, 's', f'Only 2 of its 4 neighbours are uncarved: it also touches #{nO},'),
        (MUTE, 's', f'numbered {gap} lower. Digging it would close a loop.'),
        (GOOD, 'h', f'Green: the retry. 3 of 4 uncarved, so it was dug, as #{nY}.'),
        (MUTE, 's', 'Rock, the grid edge, walls and reserved room space count as'),
        (MUTE, 's', 'uncarved ($24efc). Every corridor carve passes this test ($24514),'),
        (MUTE, 's', f'so corridors never merge. Base {SEED}: {len(d.tests) - nrefuse:,} of the '
                    f'{len(d.tests):,} tests after a step pass.')]
for c_, cls, t in btxt:
    st = 'font-size:12px;font-weight:bold' if cls == 'h' else ''
    a(f'<text x="40" y="{ty}" class="s" style="fill:{c_};{st}">{t}</text>')
    ty += 16 if cls == 'h' else 14
bend = para(40, ty + 6, 412, f'A {ww} x {wh} window of base {SEED} at one moment during the dig. Numbers are carve '
            'numbers; pale cells are uncarved; the black frame is where the turtle stands.', lead='How to read.')
bend = para(40, bend + 4, 412, 'Exactly 3 uncarved neighbours means the new cell touches only the cell it was dug from, so '
            'a corridor never breaks into another passage. On one floor the corridors therefore form a tree: one route '
            'between any two corridor cells, with no loops.', lead='Takeaway.')

# ---- C: the step word --------------------------------------------------------------------------------------------
CX0 = 480
pC = panel(CX0, BY0, 456, 400, 'C. One random word per step ($24872)', f'counted from the port, base {SEED}')
nx0, nw, ny = CX0 + 30, 396, BY0 + 104
X_ = lambda v: nx0 + nw * v / 65536
bands = [(0, BLOB_MAX + 1, '#8250df', 'blob'), (BLOB_MAX + 1, ROOM_MAX + 1, '#0969da', 'room'),
         (ROOM_MAX + 1, LIFT_MIN + 1, '#8c959f', 'forward'), (LIFT_MIN + 1, 65536, BAD, 'lift')]
a(f'<text x="{CX0 + 16}" y="{BY0 + 60}" class="s">Low 3 bits 0 or 1: turn left or right, then step (any value).'
  f'</text>')
a(f'<text x="{CX0 + 16}" y="{BY0 + 74}" class="s">Otherwise the word\'s size decides; the lift band needs low bits '
  f'2 or 3.</text>')
for lo, hi, col, lab in bands:
    a(f'<rect x="{X_(lo):.1f}" y="{ny}" width="{X_(hi) - X_(lo):.1f}" height="18" fill="{col}" fill-opacity="0.85"/>')
    if lab != 'blob':
        a(f'<text x="{(X_(lo) + X_(hi)) / 2:.1f}" y="{ny + 13}" text-anchor="middle" '
          f'style="font-size:11px;fill:#ffffff;font-weight:bold">{lab}</text>')
a(f'<text x="{X_(0) + 2:.1f}" y="{ny - 6}" class="s" style="fill:#8250df;font-weight:bold">blob: word &lt;= $7ad</text>')
for v, lab in ((0, '$0000'), (ROOM_MAX, '$8f48'), (LIFT_MIN, '$ccb0'), (65535, '$ffff')):
    a(f'<line x1="{X_(v):.1f}" y1="{ny + 18}" x2="{X_(v):.1f}" y2="{ny + 24}" stroke="{INK}"/>')
    anc = 'start' if v == 0 else ('end' if v == 65535 else 'middle')
    xo = X_(v) + (12 if v == BLOB_MAX else 0)
    a(f'<text x="{xo:.1f}" y="{ny + 36}" text-anchor="{anc}" class="c">{lab}</text>')
# table
ty = ny + 66
cols = [CX0 + 16, CX0 + 130, CX0 + 212, CX0 + 290, CX0 + 368]
for c_, h in zip(cols, ('class', 'chance', 'expected', 'seen', 'made')):
    a(f'<text x="{c_}" y="{ty}" class="s" style="fill:{INK};font-weight:bold">{h}</text>')
a(f'<line x1="{CX0 + 16}" y1="{ty + 5}" x2="{CX0 + 440}" y2="{ty + 5}" stroke="{GRID}"/>')
madecol = {'turn': '', 'forward': '', 'blob': f'{n_blobs} blobs', 'room': f'{n_rooms} rooms',
           'lift': f'{len(d.lifts)} lifts'}
for k in ('turn', 'room', 'forward', 'lift', 'blob'):
    ty += 17
    a(f'<text x="{cols[0]}" y="{ty}" class="s" style="fill:{INK}">{k}</text>'
      f'<text x="{cols[1]}" y="{ty}" class="c">{100 * prob[k]:5.1f}%</text>'
      f'<text x="{cols[2]}" y="{ty}" class="c">{prob[k] * len(fresh):5.1f}</text>'
      f'<text x="{cols[3]}" y="{ty}" class="c" style="font-weight:bold">{fc[k]:4d}</text>'
      f'<text x="{cols[4]}" y="{ty}" class="s">{madecol[k]}</text>')
ty += 24
ctxt = [f'{len(fresh)} fresh words in base {SEED}; "expected" is {len(fresh)} x the share of the',
        'word range. A carve that fails restores the turtle and retries up to 10',
        'times, re-drawing only the 2-bit selector and keeping the word:',
        f'{len(retry):,} retries here. Retried room words carved {made_retry["room"]} rooms in '
        f'{calls_retry["room"]}',
        f'(corpus: {corp["room_retry_made"]} in {corp["room_retry"]:,}); retried lift words made '
        f'{made_retry["lift"]} of the {len(d.lifts)} lifts.',
        f'After 10 failures it restarts from a random cell ({d.restart_dec} restarts here).']
for t in ctxt:
    a(f'<text x="{CX0 + 16}" y="{ty}" class="s">{t}</text>')
    ty += 14
cend = para(CX0 + 16, ty + 6, 424, 'The bar is the range of the 16-bit step word, $0000 to $ffff, cut where the code '
            'compares it; each band\'s width is its share of random words. "chance" combines the bands with the turn '
            'test on the low 3 bits (2 of 8 values); "seen" is what base 5\'s fresh words did.', lead='How to read.')
cend = para(CX0 + 16, cend + 4, 424, 'One random draw per step picks the action, so three thresholds and the selector bits '
            'set the mix of corridors, rooms, caves and lifts; base 5\'s counts sit close to the expected shares. A retry '
            'keeps its word and repeats the same check, so a room that fails once is never built.', lead='Takeaway.')
close(pB, max(bend, cend) + 6)
close(pC, max(bend, cend) + 6)

# ---- D: the flow field -------------------------------------------------------------------------------------------
DY0 = max(bend, cend) + 20
pD = panel(24, DY0, 520, 410, 'D. The flow field ($24f4c): point at the lowest number',
      f'proven: emulator G2 = model, {ff_match}/{len(open_cells)} cells')
fx0, fw, fh = ex - 6, 15, 7
fx0 = max(0, min(fx0, 64 - fw))
CF = 32
ox0, oy0 = 24 + (520 - fw * CF) // 2, DY0 + 66
ARW = {0: (0, -1), 1: (-1, 0), 2: (0, 1), 3: (1, 0)}
for yy in range(0, fh):
    for xx in range(fx0, fx0 + fw):
        i = yy * 64 + xx
        X, Y = ox0 + CF * (xx - fx0), oy0 + CF * yy
        col = ramp(g0[i]) if carved[i] else ('#9aa4ae' if g0[i] == 0xffff else ROCK)
        a(f'<rect x="{X}" y="{Y}" width="{CF}" height="{CF}" fill="{col}" fill-opacity="{0.55 if carved[i] else 1}" '
          f'stroke="#ffffff" stroke-width="1"/>')
        if not carved[i]:
            continue
        a(f'<text x="{X + 2}" y="{Y + 9}" style="font-size:8px;fill:{INK}">{g0[i]}</text>')
        v = ff[i]
        cxp, cyp = X + CF / 2, Y + CF / 2 + 4
        if v in ARW:
            ddx, ddy = ARW[v]
            x1, y1, x2, y2 = cxp - ddx * 7, cyp - ddy * 7, cxp + ddx * 9, cyp + ddy * 9
            a(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{INK}" stroke-width="1.6"/>')
            hx, hy = x2, y2
            px_, py_ = -ddy, ddx
            a(f'<polygon points="{hx + ddx * 3},{hy + ddy * 3} {hx - ddx * 3 + px_ * 3.5},{hy - ddy * 3 + py_ * 3.5} '
              f'{hx - ddx * 3 - px_ * 3.5},{hy - ddy * 3 - py_ * 3.5}" fill="{INK}"/>')
        else:
            a(f'<text x="{cxp}" y="{cyp + 4}" text-anchor="middle" style="font-size:10px;font-weight:bold;'
              f'fill:{BAD}">{"up" if v == 4 else "dn"}</text>')
X = ox0 + CF * (ex - fx0)
a(f'<rect x="{X + 1}" y="{oy0 + 1}" width="{CF - 2}" height="{CF - 2}" fill="none" stroke="{BAD}" '
  f'stroke-width="2.4"/>')
a(f'<text x="{X + CF / 2}" y="{oy0 - 5}" text-anchor="middle" class="s" style="fill:{BAD}">entrance</text>')
ty = oy0 + fh * CF + 22
dtxt = [f'After the dig, every open cell stores the direction of its open neighbour',
        f'(or lift partner) with the lowest carve number. From all {len(open_cells)} open cells of',
        f'base {SEED} the arrows lead to the entrance ({reach}/{len(open_cells)}, longest walk {longest} steps),',
        f'riding lifts and shafts where the dig did. Cells ({fx0}..{fx0 + fw - 1}, 0..{fh - 1}) of base {SEED};',
        f'small numbers are carve numbers. Creatures follow this field (inferred).']
for t in dtxt:
    a(f'<text x="40" y="{ty}" class="s">{t}</text>')
    ty += 14
dend = para(40, ty + 6, 490, f'A {fw} x {fh} window at the entrance (red box). The arrow is the direction stored in the cell; '
            'the small number is its carve number; "up" and "dn" send you to a lift.', lead='How to read.')
dend = para(40, dend + 4, 490, 'Pointing each cell at its lowest-numbered neighbour turns the dig order into a route map. '
            'Along the arrows the carve number falls at every step but 3 of all those walked (inferred to be lift or shaft '
            f'steps), down to the entrance, #{g0[ent]}.', lead='Takeaway.')

# ---- E: why there are loops anyway -------------------------------------------------------------------------------
EX0 = 556
pE = panel(EX0, DY0, 380, 410, 'E. Loops anyway', f'proven: tree.py census, {nbase} bases')
etxt = [(MUTE, f'A forest has no cycles: E - V + C = 0 over carved cells'),
        (MUTE, f'joined to their same-floor neighbours.')]
ty = DY0 + 62
for c_, t in etxt:
    a(f'<text x="{EX0 + 16}" y="{ty}" class="s">{t}</text>')
    ty += 14
bars = [('cells as they are', raw[0], 'rooms and blobs are open areas'),
        ('rooms, blobs as one node', rb[0], f'{rb[2]} loop edges, all at a shaft but 1'),
        ('+ lifts and shafts as edges', rbl[0], 'other routes between floors')]
ty += 12
bw_ = 220
for lab, v, note in bars:
    a(f'<text x="{EX0 + 16}" y="{ty}" class="s" style="fill:{INK};font-weight:bold">{lab}</text>')
    ty += 6
    a(f'<rect x="{EX0 + 16}" y="{ty}" width="{bw_}" height="14" fill="{ROCK}"/>')
    a(f'<rect x="{EX0 + 16}" y="{ty}" width="{bw_ * v / nbase:.1f}" height="14" fill="{GOOD}"/>')
    a(f'<text x="{EX0 + 24 + bw_}" y="{ty + 11}" class="c">{v}/{nbase} trees</text>')
    a(f'<text x="{EX0 + 16}" y="{ty + 28}" class="s">{note}</text>')
    ty += 50
lab_src = {'blob-trig': 'blob next to a shaft cell', 'corr-trig': 'corridor next to a shaft cell',
           'corr-corr': 'corridor next to corridor'}
a(f'<text x="{EX0 + 16}" y="{ty}" class="s" style="fill:{INK};font-weight:bold">The {rb[2]} loop edges with rooms '
  f'and blobs contracted:</text>')
ty += 15
for k, v in sorted(src.items(), key=lambda kv: -kv[1]):
    a(f'<text x="{EX0 + 30}" y="{ty}" class="c">{v:4d}</text><text x="{EX0 + 70}" y="{ty}" class="s">'
      f'{lab_src.get(k, k)}</text>')
    ty += 14
ty += 6
for t in ['Rooms and blobs join the maze at one cell, but are open',
          'inside. A shaft is carved when a passage reaches it,',
          'whatever lies beside it. Corridors are a perfect maze',
          f'per floor; base {SEED}: {len(sc[("rb", "nolift")])} loop edges contracted, '
          f'{len(sc[("rb", "lift")])} with lifts.']:
    a(f'<text x="{EX0 + 16}" y="{ty}" class="s">{t}</text>')
    ty += 14
eend = para(EX0 + 16, ty + 6, 350, f'Each bar counts the bases, of {nbase}, whose carved cells form a forest: a graph with no '
            'cycle. Cells are vertices (V), adjacent cells on one floor are joined by edges (E), and C is the number of '
            'separate pieces; E - V + C = 0 exactly when there is no cycle.', lead='How to read.')
eend = para(EX0 + 16, eend + 4, 350, 'The loops in a base come from the open insides of rooms and blobs and from shafts, '
            'which are opened whatever lies beside them; lifts and shafts add routes between floors.', lead='Takeaway.')
bot = max(dend, eend) + 6
close(pD, bot)
close(pE, bot)
y = bot + 26
a(f'<text x="24" y="{y}" class="h">How we know</text>')
y = para(24, y + 20, 912, 'dig.py is a register-level Python translation of the game\'s digging routine and every routine it '
         'calls. It starts from the emulator\'s state just before the routine and must leave the routine\'s whole '
         '13,756-byte variable block exactly as the game does.', 'k', lead='The port.')
y = para(24, y + 3, 912, 'a gate runs that comparison for many base numbers: 1000/1000 means all 1000 matched byte for byte. '
         'A control runs the same gate with one rule deliberately changed (2 of 4 uncarved instead of 3 of 4): it matches '
         '0/1000, so the gate can tell the rules apart.', 'k', lead='Gates.')
y = para(24, y + 3, 912, 'proven: checked against the game running in an Atari ST emulator. counted from the port: measured on '
         'the port, which the gate makes equal to the game. inferred: read from the code, not checked. Seed 5 is base '
         'number D0 = 5 in mode D2 = 1. Hex numbers such as $244b6 are addresses in the game\'s code, given for reference; '
         'an instruction count is how many 68000 instructions the emulator ran. G0 and G2 are two of the generator\'s working grids: G0 holds each cell\'s carve number, G2 its arrow.', 'k', lead='Labels.')
HT = y + 30
a(f'<text x="24" y="{HT - 14}" class="s">Port: reversing/captive/py/mapgen/digger/dig.py, byte-exact against the '
  f'emulator on 1000/1000 seeds (D2 = 1) and 100/100 (D2 = 0). Figure: gen_digger.py; facts: digger.facts.md.</text>')
a('</svg>')
s[0] = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WD} {HT}" width="{WD}" height="{HT}" role="img" '
        f'aria-labelledby="t d">')
s[4] = f'<rect width="{WD}" height="{HT}" fill="#ffffff"/>'
p = os.path.join(OUT, 'digger.svg')
open(p, 'w').write('\n'.join(s))
print('wrote', p)
