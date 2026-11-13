#!/usr/bin/env python3
"""Infographic: Captive's creature pursuit (reversing/captive/ai.md "Summary", "Decision rule", "The trail";
mapgen.md "The flow field (plane 2)").

usage: gen_trail.py [--emu] [outdir]   (default scratchpad/captive/infographics; writes trail.svg, prints
every number it draws and asserts the key ones). Everything is read from the snapshots or recomputed with the repo's
models: py/ai/field.py (exec'd for the drain counts), py/ai/gate_decide.py (its model() and its trial generator,
exec'd with a stub server to recover the 3000 trial inputs). The emulator runs are cached in scratchpad/captive/infographics/data/trail_emu.json;
--emu re-runs them (about 20 s): gate_decide.py on p2.snap and base1/in.snap, the README's control (dy > 5,
rng < $31e0) on p2.snap, and track.py p2.snap 200 7 (its end snapshot goes to data/track_end.snap, TRACK_OUT).
Facts and sources: trail.facts.md."""
import io, json, os, re, struct, subprocess, sys, contextlib, collections

def root():
    d = os.environ.get('M68000_ROOT') or os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
        nd = os.path.dirname(d)
        if nd == d:
            sys.exit('repo root (tools/rdis.py) not found')
        d = nd
    return d

R = root()
sys.path.insert(0, os.path.join(R, 'tools'))
from gfxview import load_ram  # noqa: E402

args = [a for a in sys.argv[1:] if a != '--emu']
EMU = '--emu' in sys.argv[1:]
W = os.path.join(R, 'scratchpad', 'captive')
AI = os.path.join(W, 'agents', 'ai')
OUT = args[0] if args else os.path.join(W, 'infographics')
DATA = os.path.join(W, 'infographics', 'data')
os.makedirs(OUT, exist_ok=True)
os.makedirs(DATA, exist_ok=True)
PY = os.path.join(R, 'reversing', 'captive', 'py', 'ai')
CACHE = os.path.join(DATA, 'trail_emu.json')
A6 = 0x1b5ce
GRID, PL2, PX, PY_, FLOORS, ENT = A6 + 9242, A6 + 11322, A6 + 26, A6 + 28, A6 + 9206, A6 + 9238
DIRV = {0: (0, -1), 1: (-1, 0), 2: (0, 1), 3: (1, 0)}      # 0 N, 1 W, 2 S, 3 E (ai.md "Map planes")
SNAP = {n: os.path.join(AI, n + '.snap') for n in ('req4', 'p14', 'p2', 'g16_adj')}
SNAP['base1'] = os.path.join(W, 'base1', 'in.snap')

# ---- emulator runs (cached) ---------------------------------------------------------------------
def run(cmd, env=None):
    r = subprocess.run(cmd, cwd=R, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        sys.exit(f'{cmd} failed:\n{r.stderr[-2000:]}')
    return r.stdout

def parse_gate(txt):
    m = re.search(r'(\d+)/(\d+) match', txt)
    tally = eval(re.search(r'by label (\{.*\})', txt).group(1))
    return {'ok': int(m.group(1)), 'n': int(m.group(2)), 'tally': tally}

GATE = os.path.join(PY, 'gate_decide.py')
TRACK_FRAMES, TRACK_STEP = 200, 60000
if EMU or not os.path.exists(CACHE):
    py = [sys.executable, '-I']
    emu = {'p2': parse_gate(run(py + [GATE, SNAP['p2'], '3000', '2'])),
           'base1': parse_gate(run(py + [GATE, SNAP['base1'], '3000', '2']))}
    ctl = ("import sys; __file__ = %r; sys.argv = [__file__, %r, '3000', '2']; src = open(__file__).read(); "
           "assert src.count('dy > 6') == 1 and src.count('rng <= 0x31e0') == 1; "
           "src = src.replace('dy > 6', 'dy > 5').replace('rng <= 0x31e0', 'rng < 0x31e0'); "
           "exec(compile(src, __file__, 'exec'))" % (GATE, SNAP['p2']))
    emu['control'] = parse_gate(run(py + ['-c', ctl]))
    env = dict(os.environ, TRACK_OUT=os.path.join(DATA, 'track_end.snap'))
    emu['track'] = run(py + [os.path.join(PY, 'track.py'), SNAP['p2'], str(TRACK_FRAMES), '7'], env=env)
    json.dump(emu, open(CACHE, 'w'), indent=1)
emu = json.load(open(CACHE))

# ---- snapshots ------------------------------------------------------------------------------------
ram = {n: load_ram(p)[0] for n, p in SNAP.items()}
w16 = lambda m, a: struct.unpack('>H', m[a:a + 2])[0]
tile = lambda m, x, y: m[GRID + 64 * y + x] & 0x7f
lo = lambda m, x, y: m[PL2 + 64 * y + x] & 7
hi = lambda m, x, y: (m[PL2 + 64 * y + x] >> 3) & 7
req4, p14, p2 = ram['req4'], ram['p14'], ram['p2']
floor_of = lambda m, x, y: m[FLOORS + (y // 8) * 4 + x // 16]
ent = (w16(req4, ENT), 0)
party = {n: (w16(ram[n], PX), w16(ram[n], PY_)) for n in ram}
ROWS = max(y for y in range(32) for x in range(64) if tile(req4, x, y)) + 1
opn = lambda m, x, y: 0 <= x < 64 and 0 <= y < 32 and tile(m, x, y) != 0

# ---- field.py, exec'd, and a per-cell walk with the same rule ------------------------------------
def field_py(snap, trail):
    ns = {'__name__': '__main__', '__file__': os.path.join(PY, 'field.py')}
    old = sys.argv; sys.argv = ['field.py', snap] + (['trail'] if trail else [])
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(open(ns['__file__']).read(), 'field.py', 'exec'), ns)
    finally:
        sys.argv = old
    return ns['ends']

def walk(m, x, y, get):
    path = [(x, y)]
    for _ in range(300):
        d = get(m, x, y)
        if d > 3: return path, ('lift', x, y, d)
        nx, ny = x + DIRV[d][0], y + DIRV[d][1]
        if not opn(m, nx, ny): return path, ('wall', x, y)
        if (nx, ny) in path: return path, ('loop',)
        x, y = nx, ny; path.append((x, y))
    return path, ('loop',)

def drains(m, get):
    return {(x, y): walk(m, x, y, get) for y in range(32) for x in range(64) if opn(m, x, y)}

def tally(dr):
    c = collections.Counter()
    for _, e in dr.values():
        c[(e[1], e[2], e[3]) if e[0] == 'lift' else e if e[0] == 'loop' else e] += 1
    return c

dr_lo, dr_hi, dr_p2 = drains(req4, lo), drains(req4, hi), drains(p2, hi)
for dr, snap, tr in ((dr_lo, SNAP['req4'], False), (dr_hi, SNAP['req4'], True), (dr_p2, SNAP['p2'], True)):
    fp, mine = field_py(snap, tr), tally(dr)
    mine = collections.Counter({('loop' if k == ('loop',) else k): v for k, v in mine.items()})
    assert fp == mine, (snap, tr, fp.most_common(5), mine.most_common(5))
lifts = sorted((x, y, lo(req4, x, y)) for (x, y) in dr_lo if lo(req4, x, y) > 3)
cnt = lambda dr, key: sum(1 for _, e in dr.values() if e[:len(key)] == key)
n_open = len(dr_lo)
drain_lo = {('lift', x, y, v): cnt(dr_lo, ('lift', x, y, v)) for x, y, v in lifts}
drain_lo['entrance'] = cnt(dr_lo, ('wall',) + ent)
drain_lo['dead end'] = n_open - sum(drain_lo.values())
assert drain_lo[('lift', 24, 3, 5)] == 449 and drain_lo[('lift', 2, 4, 4)] == 11 and drain_lo['entrance'] == 74
ent_hi = cnt(dr_hi, ('wall',) + ent)
lift_hi = {k: cnt(dr_hi, ('lift',) + k) for k in [(x, y, v) for x, y, v in lifts]}
assert ent_hi == 75 and lift_hi[(24, 3, 5)] == 433 and lift_hi[(2, 4, 4)] == 10
# cells whose generated byte has bits 3-5 != bits 0-2 before the party moved
odd = [(x, y) for (x, y) in dr_lo if lo(req4, x, y) != hi(req4, x, y)]
odd_all = sum(1 for i in range(2048) if (req4[PL2 + i] & 7) != ((req4[PL2 + i] >> 3) & 7))
nz_odd = all(hi(req4, x, y) == 0 for x in range(64) for y in range(32) if lo(req4, x, y) != hi(req4, x, y))
mx_path = max(len(p) - 1 for p, e in dr_lo.values() if e[0] == 'lift' or (e[0] == 'wall' and e[1:] == ent))

# lift partners (inferred): the other end of a lift cell is the cell at the same place in its block on the
# neighbouring floor (mapgen.md "Lift offsets"). Floor 1 here is one block, so the offset is the block step.
floor_ids = sorted(set(floor_of(req4, x, y) for (x, y) in dr_lo))
fl1 = [b for b in range(16) if req4[FLOORS + b] == floor_ids[0]]
def partner(x, y):
    cands = [(x + 16 * dx, y + 8 * dy) for dx in range(-3, 4) for dy in range(-3, 4) if (dx, dy) != (0, 0)]
    return [c for c in cands if opn(req4, *c) and floor_of(req4, *c) != floor_of(req4, x, y) and tile(req4, *c) in (0x31, 0x34)]
part = {(x, y): partner(x, y) for x, y, _ in lifts}
assert all(len(v) == 1 for v in part.values()), part
def walk_lifts(x, y):                      # the dig path through the lifts (not creature behaviour)
    seen = set()
    while True:
        p, e = walk(req4, x, y, lo)
        if e[0] != 'lift' or (e[1], e[2]) in seen: return e
        seen.add((e[1], e[2])); x, y = part[(e[1], e[2])][0]
through = collections.Counter(walk_lifts(*c)[:3] for c in dr_lo)

# ---- the footprints -----------------------------------------------------------------------------
fp14 = [(x, y, hi(p14, x, y)) for y in range(32) for x in range(64) if hi(p14, x, y) != hi(req4, x, y)]
fp2 = [(x, y, hi(p2, x, y)) for y in range(32) for x in range(64) if hi(p2, x, y) != hi(req4, x, y)]
cur = party['req4']; order = []
fpd = {(x, y): d for x, y, d in fp2}
while cur in fpd:                          # chain the footprints from the start: each points to the next
    order.append(cur); d = fpd[cur]; cur = (cur[0] + DIRV[d][0], cur[1] + DIRV[d][1])
assert cur == party['p2'] and len(order) == len(fp2)
assert [d for *_, d in fp14] == [3, 3, 2] and party['p14'] == (14, 1)
assert all(fpd[c] == 2 for c in [(14, 1), (14, 2), (14, 3), (14, 4)])
reversed_ = [c for c in order[1:] if fpd[c] == (lo(req4, *c) + 2) & 3]
# every cell that drained to the entrance now drains into the party's cell
was_ent = {c for c, (_, e) in dr_hi.items() if e == ('wall',) + ent}
now_loop = {c for c, (_, e) in dr_p2.items() if e == ('loop',)}
loop_end = {c: p[-1] for c, (p, e) in dr_p2.items() if e == ('loop',)}
assert was_ent == now_loop and set(loop_end.values()) <= {party['p2'], (party['p2'][0], party['p2'][1] - 1)}
party_cell = hi(p2, *party['p2'])
# the same walk, stopping at the party's cell: the catchment that leads to the party, in each state
def walk_party(m, x, y, pc):
    seen = set()
    while (x, y) not in seen:
        if (x, y) == pc: return 'party'
        seen.add((x, y)); d = hi(m, x, y)
        if d > 3: return ('lift', x, y)
        nx, ny = x + DIRV[d][0], y + DIRV[d][1]
        if not opn(m, nx, ny): return 'wall'
        x, y = nx, ny
    return 'loop'
catch = {n: collections.Counter(walk_party(ram[n], x, y, party[n]) for y in range(32) for x in range(64)
                                if opn(ram[n], x, y)) for n in ('req4', 'p14', 'p2', 'base1')}
for n in ('req4', 'p14', 'p2'):
    assert catch[n]['party'] == 75 and catch[n]['loop'] == 0, (n, catch[n])
b1 = ram['base1']
b1_open = sum(1 for y in range(32) for x in range(64) if opn(b1, x, y))
b1_lifts = sum(1 for y in range(32) for x in range(64) if opn(b1, x, y) and lo(b1, x, y) > 3)
# the footprint is the direction travelled, not the facing: the party strafed E twice while facing S
pface = {n: w16(ram[n], A6 + 30) for n in ('req4', 'p14', 'p2')}
assert pface['req4'] == pface['p14'] == 2 and fpd[(12, 0)] == fpd[(13, 0)] == 3
# nothing ages a mark: plane-2 bits 3-5 after the 200-sample track
aged = {n: sum(1 for i in range(2048) if ((ram[n][PL2 + i] >> 3) & 7) != ((p2[PL2 + i] >> 3) & 7)) for n in ('g16_adj',)}
tend = os.path.join(DATA, 'track_end.snap')
if os.path.exists(tend):
    te = load_ram(tend)[0]
    aged['track_end'] = sum(1 for i in range(2048) if ((te[PL2 + i] >> 3) & 7) != ((p2[PL2 + i] >> 3) & 7))

# ---- the decision model and the gate's own trials -----------------------------------------------
gsrc = open(GATE).read()
gns = {'__name__': 'gate_model', '__file__': GATE}
exec(compile(gsrc.split("if __name__ == '__main__':")[0], 'gate_decide.py', 'exec'), gns)
model = gns['model']; TB2C = gns['TB2C']
class Stub:                                # replays main()'s draws; returns nothing the gate's counts rely on
    def __init__(self, m): self.m, self.pokes = m, []
    def __call__(self, meth, **kw):
        if meth == 'poke': self.pokes.append((kw['addr'], kw['value']))
        return {'id': 0}
    def read(self, a, n): return bytes(self.m[a:a + n])
    def call(self, *a, **k): return {'pc': '$010464'}
    def close(self): pass
def trials(m):
    st = Stub(m); gns['srv'] = lambda snap: st
    old = sys.argv; sys.argv = ['gate_decide.py', 'stub', '3000', '2']
    try:
        with contextlib.redirect_stdout(io.StringIO()): gns['main']()
    finally:
        sys.argv = old
    rec = A6 + 4532; out = []
    for k in range(0, len(st.pokes), 9):
        P = dict((a, v) for a, v in st.pokes[k:k + 9])
        out.append(dict(pv=st.pokes[k][1], cx=P[rec], cy=P[rec + 1], f5=P[rec + 5], typ=P[rec + 8],
                        px=P[A6 + 26], py=P[A6 + 28], rng=P[A6 + 15530]))
    return out
T = trials(p2)
tb = p2[TB2C:TB2C + 64]
lab = [model(t['cx'], t['cy'], t['f5'] & 3, t['f5'], t['typ'], t['px'], t['py'], t['rng'], t['pv'], tb[t['typ']]) for t in T]
assert len(T) == emu['p2']['n'] and collections.Counter(lab) == collections.Counter(emu['p2']['tally'])
assert emu['p2']['ok'] == emu['p2']['n'] and emu['base1']['ok'] == emu['base1']['n']
def branch(t):
    f5, dx, dy = t['f5'], abs(t['cx'] - t['px']), abs(t['cy'] - t['py'])
    if f5 & 0x20: return 'special'
    if not f5 & 8 or t['typ'] in (6, 8): return 'unaware'
    if (dx == 0 and 1 <= dy <= 6) or (dy == 0 and 1 <= dx <= 6): return 'sight'
    if dx == 0 and dy == 0: return 'same cell'
    return 'relentless' if f5 & 0x40 else 'trail'
br = collections.Counter((branch(t), l) for t, l in zip(T, lab))
def between(t):                            # cells strictly between group and party on the line
    cx, cy, px, py = t['cx'], t['cy'], t['px'], t['py']
    if cx == px: return [(cx, y) for y in range(min(cy, py) + 1, max(cy, py))]
    return [(x, cy) for x in range(min(cx, px) + 1, max(cx, px))]
sight = [t for t in T if branch(t) == 'sight']
thru_wall = [t for t in sight if any(not opn(p2, *c) for c in between(t))]
cross_floor = [t for t in sight if floor_of(p2, t['cx'], t['cy']) != floor_of(p2, t['px'], t['py'])]
byb = lambda b: {l: n for (bb, l), n in br.items() if bb == b}

# ---- group 16's natural chase (track.py) ---------------------------------------------------------
g16 = []
for line in emu['track'].splitlines():
    m = re.match(r'\s*(\d+) party\((\d+),(\d+)\)f(\d)', line)
    g = re.search(r'g16:t([0-9a-f]+)x(\d)@\((\d+),(\d+)\)f(\d)([A-])([H-])', line)
    if m and g:
        g16.append((int(m.group(1)), (int(m.group(2)), int(m.group(3))), int(g.group(1), 16),
                    (int(g.group(3)), int(g.group(4))), int(g.group(5)), g.group(6) == 'A', g.group(7) == 'H'))
assert len(g16) == TRACK_FRAMES
moves = [(f, pos, fc) for k, (f, _, _, pos, fc, _, _) in enumerate(g16) if k and (pos, fc) != (g16[k - 1][3], g16[k - 1][4])]
assert [f for f, *_ in moves] == [4, 22, 40, 58, 76], moves
assert all(pp == party['p2'] and a and h for _, pp, _, _, _, a, h in g16)
typ16 = g16[0][2]
chase = []
prev = (g16[0][3], g16[0][4])
for f, pos, fc in moves:
    (cx, cy), face = prev
    f5 = face | 0x18
    labs = sorted({model(cx, cy, face, f5, typ16, *party['p2'], rng, p2[PL2 + 64 * cy + cx], tb[typ16])
                   for rng in (0, 0x7d0, 0x7d1, 0x31e0, 0x31e1, 0xffff)})
    did = 'FORWARD' if pos != (cx, cy) else 'TURN'
    assert did in labs, (f, labs)
    dx, dy = abs(cx - party['p2'][0]), abs(cy - party['p2'][1])
    why = 'sight' if (dx == 0 and dy <= 6) or (dy == 0 and dx <= 6) else 'trail %s' % 'NWSE'[hi(p2, cx, cy)]
    src = 'footprint' if (cx, cy) in fpd else 'dig tree'
    chase.append((f, (cx, cy), face, pos, fc, did, labs, why, src))
    prev = (pos, fc)
last = g16[-1]
stay = sum(1 for r in g16 if r[3] == moves[-1][1])

# ---- print every number drawn -------------------------------------------------------------------
print('base: open cells', n_open, 'rows used', ROWS, 'floors (block table)', list(req4[FLOORS:FLOORS + 16]),
      'entrance', ent, 'party req4', party['req4'], 'p14', party['p14'], 'p2', party['p2'])
print('lift cells (value 4/5):', lifts, 'partners (inferred):', part)
print('dig tree (bits 0-2, req4) drains:', drain_lo, 'max path', mx_path)
print('through the lifts (dig path, not creatures):', dict(through))
print('bits 3-5 in req4: entrance', ent_hi, 'lifts', lift_hi, '; bytes with bits 3-5 != 0-2:', odd_all,
      'all with bits 3-5 = 0:', nz_odd, 'open ones:', len(odd))
print('footprints p14:', fp14, ' p2:', fp2, ' party path:', order, '->', party['p2'])
print('footprints that reverse the dig arrow:', len(reversed_), 'of', len(order) - 1, '(entrance excluded)')
print('cells draining to the entrance in req4 (bits 3-5):', len(was_ent), '-> in p2 into the party cycle:', len(now_loop),
      'ends', collections.Counter(loop_end.values()), 'party cell value', party_cell)
print('catchment of the party cell (bits 3-5, walk stops at the party):', {n: dict(c) for n, c in catch.items()})
print('base1: open', b1_open, 'cells with value 4/5:', b1_lifts, 'party', party['base1'], '; facing req4/p14/p2', pface)
print('bits 3-5 changed after track (12,000,000 steps):', aged)
print('gate p2 %d/%d, base1 %d/%d, control %d/%d' % (emu['p2']['ok'], emu['p2']['n'], emu['base1']['ok'],
      emu['base1']['n'], emu['control']['ok'], emu['control']['n']))
print('gate p2 tally', emu['p2']['tally'], '\nbase1 tally', emu['base1']['tally'])
print('branches (model, on the gate trials):', dict(br))
print('sight trials', len(sight), 'with a wall between', len(thru_wall), 'across floors', len(cross_floor))
print('group 16 type %x, chase:' % typ16)
for c in chase: print('  ', c)
print('stays at', moves[-1][1], 'for', stay, 'of', TRACK_FRAMES, 'samples; last', last)

# ---- svg ----------------------------------------------------------------------------------------
import html, textwrap
WD, HT = 900, 1236                         # HT is recomputed from the content at the end
s = []; a = s.append
INK, MUTE, ACC, BAD, GRIDC, WALL = '#1f2328', '#656d76', '#0969da', '#cf222e', '#d0d7de', '#57606a'
C_ENT, C_L1, C_L2, C_DEAD = '#f6c48f', '#a8cdf5', '#b5e3b5', '#e4e6e9'
a('')                                      # the <svg> header, written once the height is known
a('<title id="t">Follow the footprints</title>')
a('<desc id="d">Captive (1990): a creature group that is aware of the party sees it only along its row or column, '
  'up to 6 cells, through walls; out of sight it follows the direction stored in its own map cell, which starts as '
  'the level generator\'s dig tree and is overwritten by the party\'s footprints. Sources: reversing/captive/ai.md '
  '"Decision rule" and "The trail", mapgen.md "The flow field"; computed by gen_trail.py from the req4, p14 and p2 '
  'snapshots. Facts: trail.facts.md.</desc>')
a('<style>text{font-family:Helvetica,Arial,sans-serif;fill:%s;font-size:12px}.t{font-size:20px;font-weight:bold}'
  '.h{font-size:14px;font-weight:bold}.m{fill:%s}.c{font-family:Menlo,monospace;font-size:11px}'
  '.s{font-size:11px;fill:%s}.b{font-size:11px;font-weight:bold}.l{font-size:12.5px}.k{font-size:11px;fill:%s}</style>'
  % (INK, MUTE, MUTE, INK))
a('')                                      # the background rect, sized with the header

def para(x, y, w, txt, cls='s', lh=15, lead=None, cpx=5.3):
    """Wrap txt to w pixels (cpx pixels per character); an optional bold lead-in. Returns the next baseline."""
    full = (lead + ' ' if lead else '') + txt
    for k, line in enumerate(textwrap.wrap(full, int(w / cpx))):
        body = html.escape(line, quote=False)
        if k == 0 and lead:
            body = '<tspan style="font-weight:bold;fill:%s">%s</tspan>%s' % (INK, html.escape(lead, quote=False),
                                                                             html.escape(line[len(lead):], quote=False))
        a(f'<text x="{x}" y="{y}" class="{cls}">{body}</text>'); y += lh
    return y

a('<text x="24" y="38" class="t">Follow the footprints</text>')
LEAD = ('Captive (Antony Crowther, Mindscape, 1990) is a real-time dungeon crawler: the player steers four droids '
        'through procedurally generated bases on a series of planets. Inside a base the creatures move in groups of up '
        'to nine sharing one map cell. A group that has noticed the party has to reach it, yet it sees only along a '
        'straight line. The game does this without searching for a path. Beside the tile map it keeps a second map, '
        '"plane 2", holding one direction per cell. The level generator fills it with the route its digger took '
        '(panel A); the party overwrites it with footprints as it walks (B); a group that cannot see the party (C) '
        'steps the way its own cell points (D).')
ly_ = para(24, 62, 852, LEAD, 'l', 17, cpx=6.0)

def panel(x, y, w, h, title, label):
    """Draw a panel's title; its frame is sized later by close(), so the panel grows with its text."""
    idx = len(s); a('')
    PANELS[idx] = (x, y, w)
    a(f'<text x="{x+14}" y="{y+24}" class="h">{title}</text>')
    a(f'<text x="{x+w-14}" y="{y+24}" text-anchor="end" class="s" style="fill:{ACC}">{label}</text>')
    return idx

PANELS = {}
def close(idx, bottom):
    x, y, w = PANELS[idx]
    s[idx] = f'<rect x="{x}" y="{y}" width="{w}" height="{bottom - y}" rx="6" fill="none" stroke="{GRIDC}"/>'
    return bottom

def arrow(cx, cy, d, ln, col, wdt=1.0, hd=None):
    ux, uy = DIRV[d]; hd = hd or ln * 0.45
    x0, y0, x1, y1 = cx - ux * ln / 2, cy - uy * ln / 2, cx + ux * ln / 2, cy + uy * ln / 2
    px_, py2 = -uy, ux
    a(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{col}" stroke-width="{wdt}"/>')
    a(f'<polygon points="{x1+ux*hd*0.3:.1f},{y1+uy*hd*0.3:.1f} {x1-ux*hd+px_*hd*0.6:.1f},{y1-uy*hd+py2*hd*0.6:.1f} '
      f'{x1-ux*hd-px_*hd*0.6:.1f},{y1-uy*hd-py2*hd*0.6:.1f}" fill="{col}"/>')

def dest_col(e):
    if e[0] == 'lift': return C_L1 if (e[1], e[2]) == (lifts[1][0], lifts[1][1]) else C_L2
    if e == ('wall',) + ent: return C_ENT
    return C_DEAD

def floor_borders(x0, y0, cs, xs, ys):
    for y in ys:
        for x in xs:
            f = floor_of(req4, x, y)
            if x + 1 in xs and floor_of(req4, x + 1, y) != f:
                X = x0 + (x + 1 - xs[0]) * cs
                a(f'<line x1="{X}" y1="{y0+(y-ys[0])*cs}" x2="{X}" y2="{y0+(y-ys[0]+1)*cs}" stroke="{INK}" stroke-width="2"/>')
            if y + 1 in ys and floor_of(req4, x, y + 1) != f:
                Y = y0 + (y + 1 - ys[0]) * cs
                a(f'<line x1="{x0+(x-xs[0])*cs}" y1="{Y}" x2="{x0+(x-xs[0]+1)*cs}" y2="{Y}" stroke="{INK}" stroke-width="2"/>')

# A: the dig tree over the whole base -------------------------------------------------------------
AY = ly_ + 8
pA = panel(24, AY, 852, 318, 'A. The generator\'s dig tree, as the creatures inherit it (state req4, before the party moves)',
      'computed: field.py on req4')
cs, x0, y0 = 13, 34, AY + 40
xs, ys = list(range(64)), list(range(ROWS))
for y in ys:
    for x in xs:
        X, Y = x0 + x * cs, y0 + y * cs
        if not opn(req4, x, y):
            a(f'<rect x="{X}" y="{Y}" width="{cs}" height="{cs}" fill="{WALL}"/>'); continue
        a(f'<rect x="{X}" y="{Y}" width="{cs}" height="{cs}" fill="{dest_col(dr_lo[(x, y)][1])}"/>')
        d = lo(req4, x, y)
        if d <= 3: arrow(X + cs / 2, Y + cs / 2, d, 8, INK, 0.8, 3.2)
floor_borders(x0, y0, cs, xs, ys)
for (x, y, v) in lifts:
    X, Y = x0 + x * cs + cs / 2, y0 + y * cs + cs / 2
    a(f'<circle cx="{X}" cy="{Y}" r="6" fill="#ffffff" stroke="{INK}" stroke-width="1.6"/>')
    a(f'<text x="{X}" y="{Y+3.5}" text-anchor="middle" style="font-size:9px;font-weight:bold">{v}</text>')
    (qx, qy), = part[(x, y)]
    QX, QY = x0 + qx * cs + cs / 2, y0 + qy * cs + cs / 2
    a(f'<circle cx="{QX}" cy="{QY}" r="5.5" fill="none" stroke="{INK}" stroke-width="1.2" stroke-dasharray="2 1.5"/>')
EX, EY = x0 + ent[0] * cs + cs / 2, y0
a(f'<polygon points="{EX-5},{EY-9} {EX+5},{EY-9} {EX},{EY-1}" fill="{BAD}"/>')
a(f'<text x="{EX+8}" y="{EY-3}" class="s" style="fill:{BAD}">entrance {ent}: the root of the dig, where the party stands</text>')
a(f'<text x="{x0+8*cs}" y="{y0+11*cs}" text-anchor="middle" class="b" style="fill:#ffffff">floor {floor_ids[0]}: the block above</text>')
a(f'<text x="{x0+8*cs}" y="{y0+12.3*cs}" text-anchor="middle" class="s" style="fill:#ffffff">(this block: outside the base)</text>')
a(f'<text x="{x0+56*cs}" y="{y0+11.5*cs}" text-anchor="middle" class="b" style="fill:#ffffff">floor {floor_ids[1]}: the other five blocks</text>')
ly = y0 + ROWS * cs + 20
leg = [(C_L1, f'{drain_lo[("lift",) + lifts[1]]} cells end at lift ({lifts[1][0]},{lifts[1][1]}), value {lifts[1][2]}'),
       (C_L2, f'{drain_lo[("lift",) + lifts[0]]} end at lift ({lifts[0][0]},{lifts[0][1]}), value {lifts[0][2]}'),
       (C_ENT, f'{drain_lo["entrance"]} end at the entrance'),
       (C_DEAD, f'{drain_lo["dead end"]} end at a wall')]
lx = 34
for c, t in leg:
    a(f'<rect x="{lx}" y="{ly-10}" width="12" height="12" fill="{c}" stroke="{GRIDC}"/><text x="{lx+17}" y="{ly}" class="s">{t}</text>')
    lx += 17 + 6.1 * len(t) + 22
a(f'<text x="34" y="{ly+20}" class="s">Each open cell stores a direction (plane 2, bits 0-2) to its neighbour dug earlier, so following arrows retraces '
  f'the digger back to the entrance (longest walk {mx_path} steps).</text>')
a(f'<text x="34" y="{ly+35}" class="s">Where the dig changed floor the value is 4 or 5, "take the lift"; dashed ring: the other end '
  f'(inferred from the lift offset). Through the lifts all {n_open - drain_lo["dead end"]} reach the entrance.</text>')
a(f'<text x="34" y="{ly+50}" class="s">Floors are blocks of one 64 x 32 grid (thick lines). The creatures read a copy in bits 3-5, equal '
  f'to bits 0-2 except {odd_all} bytes where bits 3-5 are 0 ({len(odd)} of them open).</text>')
y = para(34, ly + 72, 830, f'One square per map cell of the game\'s 64 x 32 grid (only rows 0-{ROWS-1}, the ones this base uses, '
         'are drawn). North is up, and a coordinate is (column, row). Dark grey is rock. The arrow is the direction stored in '
         'the cell. The colour says where you arrive if you keep stepping the way the arrows point: at one of the two lifts '
         '(blue, green), at the entrance (orange), or stuck against rock (light grey). A circled number is a lift cell, which '
         'stores 4 or 5 instead of a direction. The digger is the level generator\'s carving routine: it moves cell by cell '
         'from the entrance and numbers each cell it carves, and each arrow points to the open neighbour that was dug '
         'earliest.', lead='How to read.')
y = para(34, y + 4, 830, 'Before the party moves, every open cell already holds a route back along the digger\'s path. The '
         'creatures reuse this map as it stands. Cells that lead to the entrance lead to the party, which arrives there; '
         'cells that lead to a lift lead to the place where a chasing group gives up (panel D).', lead='Takeaway.')
close(pA, y + 4)

# B: footprints and the chase ---------------------------------------------------------------------
BY = y + 18
pB = panel(24, BY, 852, 352, 'B. The party\'s footprints overwrite it, and group 16 follows (state p2, then 200 samples of play)',
      f'proven: walk.py; track.py {len(moves)}/{len(moves)} moves')
cs, x0, y0 = 28, 40, BY + 42
xs, ys = list(range(16)), list(range(8))
for y in ys:
    for x in xs:
        X, Y = x0 + x * cs, y0 + y * cs
        if not opn(p2, x, y):
            a(f'<rect x="{X}" y="{Y}" width="{cs}" height="{cs}" fill="{WALL}"/>'); continue
        e = dr_p2[(x, y)][1]
        col = '#fbe3c8' if e == ('loop',) else C_DEAD if e[0] == 'wall' else C_L2
        a(f'<rect x="{X}" y="{Y}" width="{cs}" height="{cs}" fill="{col}" stroke="#ffffff" stroke-width="0.6"/>')
        d = hi(p2, x, y)
        if (x, y) in fpd:
            a(f'<rect x="{X+1.5}" y="{Y+1.5}" width="{cs-3}" height="{cs-3}" fill="none" stroke="{BAD}" stroke-width="2"/>')
            od = lo(req4, x, y)
            if (x, y) != ent: arrow(X + cs / 2, Y + cs / 2, od, 14, '#9aa3ad', 1.0, 4)
            arrow(X + cs / 2, Y + cs / 2, d, 20, BAD, 2.2, 6)
        elif d <= 3: arrow(X + cs / 2, Y + cs / 2, d, 13, INK, 1, 4)
        else:
            a(f'<text x="{X+cs/2}" y="{Y+cs/2+4}" text-anchor="middle" class="b">{d}</text>')
X, Y = x0 + party['p2'][0] * cs, y0 + party['p2'][1] * cs
a(f'<rect x="{X+3}" y="{Y+3}" width="{cs-6}" height="{cs-6}" rx="4" fill="{ACC}"/>')
a(f'<text x="{X+cs/2}" y="{Y+cs/2+4}" text-anchor="middle" class="b" style="fill:#ffffff">P</text>')
EX = x0 + ent[0] * cs + cs / 2
a(f'<polygon points="{EX-5},{y0-9} {EX+5},{y0-9} {EX},{y0-1}" fill="{BAD}"/>')
# group 16: start and each move
pts = [chase[0][1]] + [c[3] for c in chase if c[5] == 'FORWARD']
pl = ' '.join(f'{x0+px_*cs+cs/2},{y0+py2*cs+cs/2}' for px_, py2 in pts)
a(f'<polyline points="{pl}" fill="none" stroke="#8250df" stroke-width="2.5" stroke-dasharray="5 3" opacity="0.8"/>')
for px_, py2 in pts[:-1]:
    a(f'<circle cx="{x0+px_*cs+cs/2}" cy="{y0+py2*cs+cs/2}" r="4" fill="#8250df"/>')
gx, gy = pts[-1]
a(f'<circle cx="{x0+gx*cs+cs/2}" cy="{y0+gy*cs+cs/2}" r="8" fill="#8250df"/>'
  f'<text x="{x0+gx*cs+cs/2}" y="{y0+gy*cs+cs/2+3.5}" text-anchor="middle" style="font-size:9px;font-weight:bold;fill:#ffffff">16</text>')
sx, sy = chase[0][1]
for k, txt in enumerate([f'Floor {floor_ids[0]} (cols 0-15, rows 0-7). Red: the cells the party left, with the',
                          'direction it went; grey: the dig arrow it replaced. P = party, facing S.',
                          f'Orange: the {len(now_loop)} cells whose arrows lead into the party\'s cell.',
                          'Purple: group 16, start, steps, and where it stopped.']):
    a(f'<text x="{x0}" y="{y0+8*cs+16+15*k}" class="s">{txt}</text>')
TX = 510
story = [
    (INK, 'b', f'Party walks {order[0]} {" ".join("NWSE"[fpd[c]] for c in order)} to {party["p2"]}'),
    (MUTE, 's', f'It walked down the dig tree\'s trunk, so {len(reversed_)} of its {len(order)-1} footprints'),
    (MUTE, 's', 'off the entrance are the dig arrow reversed. The cells whose'),
    (MUTE, 's', f'arrows led to the party at the entrance still lead to it:'),
    (MUTE, 's', f'{catch["req4"]["party"]} at {party["req4"]}, {catch["p14"]["party"]} at {party["p14"]}, {catch["p2"]["party"]} at {party["p2"]}.'),
    (MUTE, 's', f'A mark is the way it moved, not its facing (it strafed E facing S).'),
    (MUTE, 's', f'Marks never fade: 0 of 2048 bytes change in {TRACK_FRAMES * TRACK_STEP:,} steps.'),
    (None, None, ''),
    (INK, 'b', f'Group 16 (type ${typ16:x}, aware, hostile), no pokes:'),
    (MUTE, 'row', ('sample', 'from', 'what it did', 'why (rule in D)')),
]
for f, (cx, cy), face, pos, fc, did, labs, why, srcx in chase:
    act = f'step {"NWSE"[fc]} to {pos}' if did == 'FORWARD' else f'turn {"NWSE"[face]} to {"NWSE"[fc]}'
    rd = f'{why} ({srcx})' if why.startswith('trail') else f'sees P, {abs(cy - party["p2"][1]) + abs(cx - party["p2"][0])} away'
    story.append((INK, 'row', (f'{f}', f'({cx},{cy})', act, rd)))
story += [(MUTE, 's', f'Then adjacent to P for the last {stay} samples (the rule: attack).'),
          (MUTE, 's', 'Its trail steps read the dig tree; the one footprint it')
          , (MUTE, 's', 'stood on, (14,3), was already in sight of the party.')]
y = BY + 50
for c, cls, txt in story:
    if cls == 'row' and txt[0] == 'sample': cls = 'hdr'
    if cls == 'hdr':
        for dxc, t_ in zip((0, 38, 90, 204), txt):
            a(f'<text x="{TX+dxc}" y="{y}" class="s" style="font-style:italic">{t_}</text>')
        y += 16; continue
    if c is None: y += 6; continue
    if cls == 'row':
        for dxc, t in zip((0, 38, 90, 204), txt):
            a(f'<text x="{TX+dxc}" y="{y}" class="s" style="fill:{c}">{t}</text>')
    else:
        a(f'<text x="{TX}" y="{y}" class="{cls}" style="fill:{c}">{txt}</text>')
    y += 16
ry = para(TX, y + 4, 356, f'A sample is the game\'s state read every {TRACK_STEP:,} instructions, one creature update in this '
          'base. Group 16 acts on every 18th update (its period, 16, plus 2), hence samples 4, 22, 40, 58, 76.')
ly2 = y0 + 8 * cs + 16 + 15 * 4
y = para(40, max(ly2, ry) + 8, 820, 'Each footprint points to the cell the party entered next, so following footprints moves '
         'forward in time and ends at the party. The party arrived on the entrance, so as it walks it takes the entrance\'s '
         f'whole catchment (the {len(now_loop)} orange cells) with it: every cell that led to the entrance now leads to the party. '
         'Group 16 shows the effect in play. It follows the dig tree into that catchment, then sees the party and closes in. '
         'No observed chase has yet read a footprint itself.', lead='Takeaway.')
close(pB, y + 4)

# C: sight ---------------------------------------------------------------------------------------
CY = y + 18
pC = panel(24, CY, 400, 420, 'C. Sight: a row and a column, 6 cells', 'proven: gate')
cs = 18; xs = list(range(party['p2'][0] - 7, party['p2'][0] + 8)); ys = list(range(0, party['p2'][1] + 8))
x0, y0 = 224 - len(xs) * cs // 2, CY + 42
ppx, ppy = party['p2']
for y in ys:
    for x in xs:
        X, Y = x0 + (x - xs[0]) * cs, y0 + (y - ys[0]) * cs
        incross = (x == ppx and 1 <= abs(y - ppy) <= 6) or (y == ppy and 1 <= abs(x - ppx) <= 6)
        near = abs(x - ppx) <= 6 and abs(y - ppy) <= 6
        fill = WALL if not opn(p2, x, y) else '#ffffff'
        a(f'<rect x="{X}" y="{Y}" width="{cs}" height="{cs}" fill="{fill}" stroke="{GRIDC}" stroke-width="0.5"/>')
        if incross:
            a(f'<rect x="{X+2}" y="{Y+2}" width="{cs-4}" height="{cs-4}" fill="#2da44e" fill-opacity="{0.85 if not opn(p2, x, y) else 0.55}"/>')
        elif near:
            a(f'<rect x="{X}" y="{Y}" width="{cs}" height="{cs}" fill="{ACC}" fill-opacity="0.10"/>')
floor_borders(x0, y0, cs, xs, ys)
X, Y = x0 + (ppx - xs[0]) * cs, y0 + (ppy - ys[0]) * cs
a(f'<rect x="{X+2}" y="{Y+2}" width="{cs-4}" height="{cs-4}" rx="3" fill="{ACC}"/><text x="{X+cs/2}" y="{Y+cs/2+4}" text-anchor="middle" class="b" style="fill:#ffffff">P</text>')
g43 = [l for l in emu['track'].splitlines() if re.search(r'\*g43:[^ ]*@\(16,5\)', l)]
g43f = int(g43[0].split()[0]) if g43 else None
g43flags = re.search(r'g43:[^ ]*@\(16,5\)f\d([A-])', g43[0]).group(1) if g43 else None
if g43:
    X = x0 + (16 - xs[0]) * cs
    a(f'<circle cx="{X+cs/2}" cy="{Y+cs/2}" r="6.5" fill="#8250df"/>')
n_cross = sum(1 for x in xs for y in ys if (x == ppx and 1 <= abs(y - ppy) <= 6) or (y == ppy and 1 <= abs(x - ppx) <= 6))
wall_cross = sum(1 for x in xs for y in ys if ((x == ppx and 1 <= abs(y - ppy) <= 6) or (y == ppy and 1 <= abs(x - ppx) <= 6)) and not opn(p2, x, y))
other_floor = sum(1 for x in xs for y in ys if ((x == ppx and 1 <= abs(y - ppy) <= 6) or (y == ppy and 1 <= abs(x - ppx) <= 6))
                  and opn(p2, x, y) and floor_of(p2, x, y) != floor_of(p2, ppx, ppy))
ty = y0 + len(ys) * cs + 18
for txt in [f'Green: the {n_cross} cells (row -1 is off the map) from which an aware group',
            f'"sees" P. No wall test: {wall_cross} of them are wall, and {other_floor} open ones are on',
            f'floor {floor_ids[1]}, across the block wall. Purple: group 43 at (16,5), sample {g43f},',
            'in sight through the wall (15,5); not aware, so it wanders.',
            f'Gate trials decided by sight: {len(sight)}; {len(thru_wall)} with a wall between,',
            f'{len(cross_floor)} across floors; all match. Blue tint: the "near" box (a trail',
            'step that would turn the group around steps forward instead).']:
    a(f'<text x="38" y="{ty}" class="s">{txt}</text>'); ty += 15
cyb = para(38, ty + 4, 372, f'The party P stands at {party["p2"]} in state p2. Dark cells are rock; the thick line is the wall '
           'between two floor blocks of the grid.', lead='How to read.')
cyb = para(38, cyb + 4, 372, 'Sight compares coordinates only: rock does not block it. Floors are blocks of one grid, so the '
           'test also reaches into a neighbouring floor\'s block. Reading that as a creature seeing through the floor is '
           'inferred, because that the blocks are separate levels is itself inferred.', lead='Takeaway.')

# D: the decision rule ---------------------------------------------------------------------------
DX, DW = 436, 440
pD = panel(DX, CY, DW, 420, 'D. The decision ($10304), one per think', f'proven: {emu["p2"]["ok"]}/{emu["p2"]["n"]} labels')
tl = emu['p2']['tally']
def box(x, y, w, h, lines, fill='#f6f8fa', stroke=GRIDC):
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="{fill}" stroke="{stroke}"/>')
    for k, (t, cl) in enumerate(lines):
        a(f'<text x="{x+7}" y="{y+14+k*13}" class="{cl}">{t}</text>')
def ln(x1, y1, x2, y2, t=None, tx=None, ty=None):
    a(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{MUTE}" stroke-width="1"/>')
    if t: a(f'<text x="{tx}" y="{ty}" class="s">{t}</text>')
bx = DX + 14
box(bx, CY + 38, 190, 32, [('bit 5 (cell action)?', 'b'), (f'yes: SPECIAL {tl["SPECIAL"]}', 's')])
box(bx, CY + 80, 190, 32, [('not aware, or type 6 / 8?', 'b'), (f'yes: WANDER ({byb("unaware").get("WANDER",0)})', 's')])
box(bx, CY + 122, 190, 45, [('party on my row or column,', 'b'), ('1 to 6 cells away?', 'b'), ('no wall test', 's')], '#e6f4ea', '#2da44e')
ln(bx + 95, CY + 70, bx + 95, CY + 80); ln(bx + 95, CY + 112, bx + 95, CY + 122)
sb = byb('sight')
box(bx, CY + 182, 190, 110, [('yes: aim at it (S/N, E/W)', 'b'),
                             (f'facing, 2+ away: FORWARD {sb.get("FORWARD",0)}', 's'),
                             (f'  (ranged, RNG > $31e0: ATTACK)', 's'),
                             (f'adjacent: ATTACK {sb.get("ATTACK",0)}', 's'),
                             (f'90 deg off: TURN {sb.get("TURN",0)}', 's'),
                             (f'  (ranged, RNG &lt;= $7d0: + attack {sb.get("TURN_ATTACK",0)})', 's'),
                             (f'behind: turn at random {sb.get("BEHIND_TURN",0)}', 's')])
ln(bx + 95, CY + 167, bx + 95, CY + 182)
tb_ = byb('trail')
rx = DX + 222
ln(bx + 190, CY + 144, rx, CY + 144)
a(f'<text x="{bx+194}" y="{CY+139}" class="s">no</text>')
box(rx, CY + 122, 204, 45, [('relentless (bit 6)?', 'b'), (f'yes: WANDER ({byb("relentless").get("WANDER",0)})', 's'),
                            ('no: read bits 3-5 of my cell', 's')])
ln(rx + 102, CY + 167, rx + 102, CY + 182)
box(rx, CY + 182, 204, 32, [('4 to 7 (a lift cell)?', 'b'), (f'yes: FORGET, clear aware {tl["FORGET"]}', 's')], '#fff1e5', '#d1802d')
ln(rx + 102, CY + 214, rx + 102, CY + 224)
box(rx, CY + 224, 204, 72, [('0 to 3: aim that way, no attack', 'b'),
                            (f'facing: FORWARD {tb_.get("FORWARD",0)}', 's'),
                            (f'90 deg off: TURN {tb_.get("TURN",0)} (+ attack {tb_.get("TURN_ATTACK",0)})', 's'),
                            (f'behind: FORWARD if near, else', 's'),
                            (f'  turn at random {tb_.get("BEHIND_TURN",0)}', 's')])
ty = CY + 312
for txt in [f'Counts: the {emu["p2"]["n"]} gate trials on p2 (one group record, its cell byte,',
            f'the party and the RNG poked), split by the model\'s branch;',
            f'group on the party\'s cell: WANDER {byb("same cell").get("WANDER",0)}. Labels from the emulator:',
            ', '.join(f'{k} {v}' for k, v in sorted(tl.items(), key=lambda kv: -kv[1])[:4]) + ',',
            ', '.join(f'{k} {v}' for k, v in sorted(tl.items(), key=lambda kv: -kv[1])[4:]) + '.',
            f'Natural base: {emu["base1"]["ok"]}/{emu["base1"]["n"]}. Control (range 5, &lt; $31e0): {emu["control"]["ok"]}/{emu["control"]["n"]}.']:
    a(f'<text x="{DX+14}" y="{ty}" class="s">{txt}</text>'); ty += 15
dyb = para(DX + 14, ty + 4, DW - 28, 'Each box is a question; read from the top, and the first that applies decides. A think is one '
           'turn of a group, taken every period + 2 creature updates. CAPITALS are outcomes (the code label the gate stopped '
           'at); the number after one is how many trials ended there. Aware means the group has noticed the party; relentless '
           'groups never follow the trail; ranged types may attack from a distance. RNG is the game\'s random number for the '
           'update.', lead='How to read.')
dyb = para(DX + 14, dyb + 4, DW - 28, 'Four inputs decide: the group\'s flags, its facing, the party\'s position and one byte '
           'of the group\'s own cell. A value of 4 to 7 there (a lift cell) makes the group forget the party, so a lift is '
           'where a chase ends.', lead='Takeaway.')
bot = max(cyb, dyb) + 4
close(pC, bot); close(pD, bot)
y = bot + 26
a(f'<text x="24" y="{y}" class="h">How we know</text>')
y = para(24, y + 20, 852, 'proven: the game\'s own code was run in an Atari ST emulator and agreed with a Python model on every '
         'trial. computed: counted by this figure\'s script from memory snapshots of the running game. inferred: read from '
         'the 68000 machine code but not run.', 'k', lead='Labels.')
y = para(24, y + 3, 852, 'a gate calls one game routine thousands of times with chosen inputs written into memory ("pokes") '
         f'and compares each outcome with the model: {emu["p2"]["ok"]}/{emu["p2"]["n"]} means every trial agreed. The '
         'control runs the same gate against a deliberately wrong model (sight range 5 instead of 6, "<" instead of '
         f'"<="); it disagrees on {emu["control"]["n"] - emu["control"]["ok"]} trials, so the gate can tell the two apart. '
         'walk.py and track.py drive the party and record the creatures.', 'k', lead='Gates.')
y = para(24, y + 3, 852, 'req4 is mission 1\'s base just after entry, the party on the entrance (reached by setting the game\'s '
         'level-request word to 4); p14 and p2 are the same base after the party walked E, E, S and then four more S; base1 '
         'is a base reached by ordinary play. A step is one 68000 instruction. Hex numbers such as $10304 are addresses of '
         'the game\'s code and data, given for reference; "bits 3-5" are bits of the plane-2 byte.', 'k', lead='States.')
HT = y + 30
a(f'<text x="24" y="{HT-14}" class="s">Wander, hostility and what follows each label are inferred (ai.md "Wander and hostility"); '
  f'the base is mission 1, request word poked to 4 (ai.md "Getting into a base").</text>')
a('</svg>')
s[0] = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WD} {HT}" width="{WD}" height="{HT}" role="img" '
        'aria-labelledby="t d">')
s[4] = f'<rect width="{WD}" height="{HT}" fill="#ffffff"/>'
open(os.path.join(OUT, 'trail.svg'), 'w').write('\n'.join(s))
print('wrote', os.path.join(OUT, 'trail.svg'))
