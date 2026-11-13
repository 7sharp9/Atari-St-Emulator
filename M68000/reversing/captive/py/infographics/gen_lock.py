#!/usr/bin/env python3
"""Infographic: Captive's coded-door combination lock and the DIE that gives it away
(reversing/captive/ai.md "Getting into a base"; mapgen.md "After the flow field", "Coded doors";
the DIE and RATT-note findings these docs hold).

usage: gen_lock.py [--emu] [outdir]   (default scratchpad/captive/infographics; writes lock.svg, prints every number
it draws and asserts the key ones).

What it computes from snapshots alone: the 24-byte corner-order table $e358 (read from req4.snap and
base1/outside.snap), its decoding, and Python models of the lock click $e270 and of the die's door hint $120ca-$1213c,
both written from the disassembly (tools/disassemble.py --snap req4.snap --all e270 e358 / 1207c 12168).

What the emulator gives (cached in scratchpad/captive/infographics/data/lock_emu.json and data/lock_runs/;
--emu re-runs it, about 1 minute):
  census (stserver, base1/outside.snap, door (22,21), list slot 0):
    lock: every 4-press sequence of the 4 corners (256) for every code 0..23 (labelled poke of the state word):
          6144 sequences, 24576 calls of $e270; state word after each press and whether $c420 (open) was reached.
    die:  labelled pokes: door tile $44 -> $42 (kind 2), party (22,20) facing S, 120,000 steps; then for each code and
          each pressed set (low nibble 0..14), $1207c called 3 times. Control: the same with the tile left at $44.
  the helper scripts in py/ai (HELPERS overrides the directory; only --emu needs them), re-run
  into lock_runs/: die_all.py (req4.snap), die_hint.py and DIE_TILE=42 die_hint.py
  (base1/outside.snap), ratt_msg.py (three snapshots), doorcodes.py compound.json, die_faces.py req4.snap.
Facts and sources: lock.facts.md."""
import base64, collections, html, io, itertools, json, os, re, struct, subprocess, sys, textwrap


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
CUR = os.environ.get('HELPERS') or os.path.join(R, 'reversing', 'captive', 'py', 'ai')   # --emu only
OUT = args[0] if args else os.path.join(W, 'infographics')
DATA = os.path.join(W, 'infographics', 'data')
RUNS = os.path.join(DATA, 'lock_runs')
os.makedirs(OUT, exist_ok=True)
os.makedirs(RUNS, exist_ok=True)
CACHE = os.path.join(DATA, 'lock_emu.json')
COMPOUND = os.path.join(DATA, 'compound.json')      # gen.py's 40 compound calls (curios doorcodes input)
REQ4 = os.path.join(W, 'agents', 'ai', 'req4.snap')
OUTSIDE = os.path.join(W, 'base1', 'outside.snap')
A6 = 0x1b5ce
DOORS = A6 + 2330                    # $1bee8, 8 x (cell word x*256+y, state word)
POSX, POSY, FACE, CELL68 = A6 + 26, A6 + 28, A6 + 30, A6 + 68
CLICKX, CLICKY, MAP = A6 + 15152, A6 + 15154, A6 + 9242
TAB = 0xe358
CN = ['TL', 'TR', 'BL', 'BR']        # corner c = 2*bottom + right
CLICK = {0: (0x46, 0x50), 1: (0x86, 0x50), 2: (0x46, 0x90), 3: (0x86, 0x90)}   # inside the zones tested at $e294-$e2dc

# ---- the table -------------------------------------------------------------------------------------------------
ram = {n: load_ram(p)[0] for n, p in (('req4', REQ4), ('outside', OUTSIDE))}
tab = bytes(ram['req4'][TAB:TAB + 24])
assert tab == bytes(ram['outside'][TAB:TAB + 24])
first3 = lambda b: [(b >> 2) & 3, (b >> 4) & 3, (b >> 6) & 3]    # 1st..3rd at bits 2-3/4-5/6-7 (the lock's slots)
orders = [first3(b) + [6 - sum(first3(b))] for b in tab]             # the order the lock opens on: 4th = the one left
assert all(len(set(first3(b))) == 3 for b in tab)
assert sorted(map(tuple, orders)) == sorted(itertools.permutations(range(4)))   # all 4! orders, each once
assert len({b & 0xfc for b in tab}) == 24                                       # the lock's compare is unambiguous
odd4 = [i for i, b in enumerate(tab) if b & 3 != orders[i][3]]                  # bits 0-1 (read only by the die) wrong
assert odd4 == [9] and tab[9] == 0x6e


# ---- models from the disassembly -------------------------------------------------------------------------------
def lock(st, c):
    """$e2e4-$e348 with D2 bit 4 clear (closed door): returns (new state, 'open'|'clear'|None)."""
    lo = st & 0xff
    if lo >> c & 1:                                  # $e2e4: corner already set -> clear ($e348)
        return st & 0x1f0, 'clear'
    lo |= 1 << c
    st = (st & 0xff00) | lo
    if lo & 0xf != 0xf:                              # $e2fc-$e30e: OR c << 2n into the high byte
        n = bin(lo & 0xf).count('1')
        return st | ((c << (2 * n)) & 0xff) << 8, None
    code = (st >> 4) & 0x1f                          # $e31a-$e346: compare high byte & $fc with the table
    for i, b in enumerate(tab):
        if (b & 0xfc) == ((st >> 8) & 0xfc) and i == code:
            return st, 'open'
    return st & 0x1f0, 'clear'


def die(st):
    """$1210e-$1213c: '0' + the next corner, counting pressed corners only (not whether they were right)."""
    n = bin(st & 0xf).count('1')
    d3 = (2 + 2 * n) & 7
    b = tab[(st >> 4) & 0x1f]
    return 0x30 + (((b >> d3) | (b << (8 - d3))) & 0xff & 3)


# ---- emulator ----------------------------------------------------------------------------------------------------
def run(cmd, out, env=None):
    r = subprocess.run(cmd, cwd=R, capture_output=True, text=True, env=env)
    open(os.path.join(RUNS, out), 'w').write(r.stdout + r.stderr)
    if r.returncode != 0:
        sys.exit(f'{cmd} failed:\n{r.stderr[-2000:]}')


def census():
    from stclient import StServer
    s = StServer(R)
    s('load', snapshot=OUTSIDE)
    door = s.read(DOORS, 4)
    dx, dy, st0 = door[0], door[1], int.from_bytes(door[2:4], 'big')
    sc = s.reg('a7') - 0x400                                          # scratch die record below the stack
    base = s('fork')['id']
    res = {'door': [dx, dy, st0], 'lock': {}, 'die': {}, 'ctrl': {}}
    for code in range(24):
        for seq in itertools.product(range(4), repeat=4):
            s('restore', id=base)
            s('poke', addr=DOORS + 2, width=2, value=code << 4)          # labelled poke: state = code, nothing pressed
            out = []
            for c in seq:
                s('poke', addr=CLICKX, width=2, value=CLICK[c][0])
                s('poke', addr=CLICKY, width=2, value=CLICK[c][1])
                s('poke', addr=CELL68, width=2, value=(dx << 8) | dy)
                r = s.call(0xe270, stops=[0xc420], d2=0x44)
                pc = int(str(r['pc']).lstrip('$'), 16) if 'pc' in r else s.reg('pc')
                out.append([int.from_bytes(s.read(DOORS + 2, 2), 'big'), pc == 0xc420])
                if pc == 0xc420:
                    break
            res['lock']['%d:%s' % (code, ''.join(map(str, seq)))] = out
    for tile, key in ((0x42, 'die'), (0x44, 'ctrl')):
        s('restore', id=base)
        s('poke', addr=POSX, width=2, value=dx)                          # labelled pokes: party N of the door,
        s('poke', addr=POSY, width=2, value=dy - 1)                      # facing S (2)
        s('poke', addr=FACE, width=2, value=2)
        s('poke', addr=MAP + dy * 64 + dx, width=1, value=tile)          # labelled poke: door tile ($42 = kind 2)
        s('step', n=120000)
        ahead = s.read(A6 + 15408, 1)[0]
        b2 = s('fork')['id']
        for code in range(24):
            for nib in range(15 if key == 'die' else 1):
                s('restore', id=b2)
                s('poke', addr=DOORS + 2, width=2, value=(code << 4) | nib)
                faces = []
                for _ in range(3):
                    s('poke', addr=sc, width=4, value=0)
                    s.call(0x1207c, a0=sc)
                    faces.append(s.read(sc + 3, 1)[0])
                res[key]['%d:%d' % (code, nib)] = faces
        res[key + '_ahead'] = ahead
    s.close()
    return res


if EMU or not os.path.exists(CACHE):
    py = [sys.executable, '-I']
    run(py + [os.path.join(CUR, 'die_all.py')], 'die_all_req4.txt')
    run(py + [os.path.join(CUR, 'die_hint.py')], 'die_hint.txt')
    run(py + [os.path.join(CUR, 'die_hint.py')], 'die_hint_42.txt', env=dict(os.environ, DIE_TILE='42'))
    run(py + [os.path.join(CUR, 'ratt_msg.py'), os.path.join(W, 'base1', 'in.snap'), REQ4,
              os.path.join(W, 'agents', 'curios', 'base30.snap')], 'ratt.txt')
    run(py + [os.path.join(CUR, 'doorcodes.py'), COMPOUND], 'doorcodes.txt')
    run(py + [os.path.join(CUR, 'die_faces.py'), REQ4, os.path.join(RUNS, 'die_faces.png')], 'die_faces.txt')
    json.dump(census(), open(CACHE, 'w'))
emu = json.load(open(CACHE))
txt = {n: open(os.path.join(RUNS, n)).read() for n in
       ('die_all_req4.txt', 'die_hint.txt', 'die_hint_42.txt', 'ratt.txt', 'doorcodes.txt')}

# ---- check the models against the census -------------------------------------------------------------------------
dx, dy, st0 = emu['door']
assert (dx, dy, st0) == (22, 21, 0x80)
n_seq = n_press = 0
opens = []
first_clear = collections.Counter()
for key, out in emu['lock'].items():
    code, seq = int(key.split(':')[0]), [int(ch) for ch in key.split(':')[1]]
    st = code << 4
    n_seq += 1
    for k, (c, (est, eopen)) in enumerate(zip(seq, out)):
        st, ev = lock(st, c)
        n_press += 1
        assert st == est and (ev == 'open') == eopen, (key, k, hex(st), hex(est), ev, eopen)
    if out[-1][1]:
        opens.append((code, seq))
assert len(opens) == 24 and all(seq == orders[code] for code, seq in opens)
# code 9: the die's 4th hint (bits 0-1 of $6e = BL) is a corner already lit; pressing it clears, the real 4th opens
bad_hint = die((9 << 4) | sum(1 << c for c in orders[9][:3])) - 0x30
assert bad_hint == 2 and emu['lock']['9:' + ''.join(map(str, orders[9][:3] + [bad_hint]))][-1] == [0x90, False]
assert emu['lock']['9:' + ''.join(map(str, orders[9]))][-1][1] and emu['die']['9:%d' % sum(1 << c for c in orders[9][:3])] == [0x32] * 3
assert sorted(c for c, _ in opens) == list(range(24))


def trace(code, seq):                       # the emulator's states for a sequence (prefix of a census row)
    key = '%d:%s' % (code, ''.join(map(str, seq + [0] * (4 - len(seq)))))
    out = emu['lock'][key][:len(seq)]
    model, st = [], code << 4
    for c in seq:
        st, ev = lock(st, c)
        model.append((st, ev))
    assert [o[0] for o in out] == [m[0] for m in model]
    return [(c, st, ev) for c, (st, ev) in zip(seq, model)]


# where does a wrong 4-press attempt clear?  Over all 24 x 255 non-opening sequences, clears by press number
clear_at = collections.Counter()
for key, out in emu['lock'].items():
    if out[-1][1]:
        continue
    code, seq = int(key.split(':')[0]), [int(ch) for ch in key.split(':')[1]]
    st = code << 4
    for k, c in enumerate(seq):
        st, ev = lock(st, c)
        if ev == 'clear':
            clear_at[k + 1] += 1
            break
# a sequence of four distinct corners clears only on the 4th press: count
perm_wrong = [(int(k.split(':')[0]), k.split(':')[1]) for k, o in emu['lock'].items()
              if len(set(k.split(':')[1])) == 4 and not o[-1][1]]
perm_wrong_states = all(o[3][0] == (int(k.split(':')[0]) << 4) and all(s_ & 0xf for s_, _ in o[:3])
                        for k, o in emu['lock'].items() if len(set(k.split(':')[1])) == 4 and not o[-1][1])
assert len(perm_wrong) == 24 * 23 and perm_wrong_states

# die census
die_ok = sum(1 for k, f in emu['die'].items()
             for v in f if v == die((int(k.split(':')[0]) << 4) | int(k.split(':')[1])))
die_n = sum(len(f) for f in emu['die'].values())
assert die_ok == die_n == 24 * 15 * 3, (die_ok, die_n)
wrong_prefix = sum(1 for k in emu['die'] if (lambda c, nib: nib != sum(1 << x for x in orders[c][:bin(nib).count('1')]))
                   (int(k.split(':')[0]), int(k.split(':')[1])))
ctrl_vals = collections.Counter(v for f in emu['ctrl'].values() for v in f)
ctrl_ok = sum(n for v, n in ctrl_vals.items() if 0x20 <= v <= 0x2b)
ctrl_n = sum(ctrl_vals.values())
assert ctrl_ok == ctrl_n == 72 and emu['die_ahead'] == 0x42 and emu['ctrl_ahead'] == 0x44

# curios re-runs
m = re.search(r'hint: next corner shown (\d+)/(\d+); control: random face (\d+)/(\d+)', txt['die_all_req4.txt'])
da = tuple(map(int, m.groups()))
assert da == (2400, 2400, 6400, 6400)
da_codes = [int(c) for c in re.findall(r'code (\d+) order', txt['die_all_req4.txt'])]
da_rolls = sorted(set(re.findall(r'ahead \$..: ((?:\$2.x\d+ ?)+)$', txt['die_all_req4.txt'], re.M)))
# the hint run on the compound door (kind 4) and on the same door poked to kind 2
partA = lambda t: [l for l in t.splitlines() if 'facing 2 pressed' in l]
k4 = partA(txt['die_hint.txt'])
k4_hint = sum(int(n) for l in k4 for v, n in re.findall(r'\$(3.)x(\d+)', l))
k4_rand = sum(int(n) for l in k4 for v, n in re.findall(r'\$(2.)x(\d+)', l))
k2 = [re.findall(r'\$(..)x(\d+)', l) for l in partA(txt['die_hint_42.txt'])]
assert k4_hint == 0 and k4_rand == 1200 and [x[0] for x in k2] == [('30', '300'), ('32', '300'), ('31', '300'), ('33', '300')]
partB = re.findall(r'^\s+((?:[TB][LR]->\$[0-9a-f]{4}(?: OPEN\(\$c420\))? ?)+)$', txt['die_hint.txt'], re.M)
for line in partB:                         # die_hint part B = the model, press by press
    st = 0x80
    for c, est, op in re.findall(r'([TB][LR])->\$([0-9a-f]{4})( OPEN)?', line):
        st, ev = lock(st, CN.index(c))
        assert st == int(est, 16) and (ev == 'open') == bool(op), line
assert len(partB) == 5

# RATT text and the compound seeds
rt = re.findall(r"407\(A6\)=1: at \$bb4c A0=\$013906 b'([^']*)'", txt['ratt.txt'])
ratt = rt[0].replace('\\n', ' ')
assert len(rt) == 3 and len(set(rt)) == 1
ratt_order = [CN[['TOP-LEFT', 'TOP-RIGHT', 'BOTTOM-LEFT', 'BOTTOM-RIGHT'].index(w.strip(' .'))] for w in ratt.split(',')]
ratt_codes = [i for i, o in enumerate(orders) if [CN[c] for c in o] == ratt_order]
assert ratt_codes == [8] and tab[8] == 0x63
comp = []
for case in json.load(open(COMPOUND)):
    ft = bytes.fromhex(case['fedtab']); off = 0x1bee8 - 0x1bd3e
    ents = [(ft[off + 4 * i], ft[off + 4 * i + 1], int.from_bytes(ft[off + 4 * i + 2:off + 4 * i + 4], 'big'))
            for i in range(8) if any(ft[off + 4 * i:off + 4 * i + 4])]
    comp.append((case['args'], ents))
assert len(comp) == 40 and all(len(e) == 1 for _, e in comp)
code8 = [a for a, e in comp if (e[0][2] >> 4) & 0x1f == 8]
comp_codes = collections.Counter((e[0][2] >> 4) & 0x1f for _, e in comp)
assert len(code8) == 3 and code8[0] == [0, 0, 2, 0]
assert comp[0][1][0] == (dx, dy, st0)       # seed (0,0) = the natural mission 1 compound in outside.snap
req4_codes = [(int.from_bytes(ram['req4'][DOORS + 4 * i + 2:DOORS + 4 * i + 4], 'big') >> 4) & 0x1f
              for i in range(8) if any(ram['req4'][DOORS + 4 * i:DOORS + 4 * i + 4])]
assert req4_codes == da_codes == [12, 8, 1]

# cost
blind_worst, blind_mean = 24 * 4, 4 * (24 + 1) / 2
die_cost, die_min = 4 + 4, 3 + 4

# ---- die faces, cropped from the re-render of $12168 --------------------------------------------------------------
from PIL import Image  # noqa: E402
fimg = Image.open(os.path.join(RUNS, 'die_faces.png')).convert('RGB')
fimg = fimg.resize((fimg.width // 4, fimg.height // 4), Image.NEAREST)
CH = list(range(0x20, 0x2c)) + list(range(0x30, 0x34))
RED = (252, 0, 0)


def crop(ch):
    i = CH.index(ch)
    return fimg.crop((i * 52 + 17, 1, i * 52 + 31, 15))


for c in range(4):                          # hint face $30+c: its only red pixels are in corner c's quadrant
    im = crop(0x30 + c)
    reds = [(x, y) for x in range(14) for y in range(14) if im.getpixel((x, y)) == RED]
    assert reds and all((x >= 7) == (c & 1) and (y >= 7) == (c >> 1) for x, y in reds), c
red_faces = [ch for ch in range(0x20, 0x2c) if any(crop(ch).getpixel((x, y)) == RED for x in range(14) for y in range(14))]


def b64(ch, z=4):
    im = crop(ch).resize((14 * z, 14 * z), Image.NEAREST)
    bio = io.BytesIO(); im.save(bio, 'PNG')
    return base64.b64encode(bio.getvalue()).decode()


# ---- print every number drawn ---------------------------------------------------------------------------------
print('table $e358:', tab.hex(' '))
for i, o in enumerate(orders):
    print(f'  code {i:2d} ${tab[i]:02x} {" ".join(CN[c] for c in o)}')
print('bits 2-7 hold 24 distinct first-three triples (all 4! orders once); byte & $fc distinct: asserted; '
      f'bits 0-1 differ from the corner left over in entries {odd4} (${tab[9]:02x}: bits 0-1 = {CN[tab[9] & 3]}, left over '
      f'{CN[orders[9][3]]}); code 9 die hint after 3 lit: {CN[bad_hint]} (a lit corner); census 9:{"".join(map(str, orders[9][:3] + [bad_hint]))} clears, '
      f'9:{"".join(map(str, orders[9]))} opens')
print(f'lock census: {n_seq} sequences, {n_press} presses of $e270, model = emulator state word on every press; '
      f'opened {len(opens)}, each its own code\'s order')
print('non-opening sequences cleared at press:', dict(sorted(clear_at.items())),
      f'; the {len(perm_wrong)} wrong orders of 4 distinct corners all clear on press 4, nothing cleared before')
for name, code, seq in (('right', 8, [0, 2, 1, 3]), ('wrong', 8, [1, 2, 0, 3]), ('two right', 8, [0, 2, 3, 1]),
                        ('repeat', 8, [0, 0])):
    print(f'  {name}:', ' '.join(f'{CN[c]}->${s_:04x}{"/" + ev if ev else ""}' for c, s_, ev in trace(code, seq)))
print(f'die census: {die_ok}/{die_n} faces = model (24 codes x 15 pressed sets x 3 calls; {wrong_prefix} of the 360 '
      f'sets are not a prefix of the order); control (tile $44): {ctrl_ok}/{ctrl_n} random faces')
print(f'die_all.py re-run: hint {da[0]}/{da[1]}, control {da[2]}/{da[3]} on req4 doors codes {da_codes}; distinct '
      f'control tallies: {len(da_rolls)}')
print(f'die_hint.py: kind-4 compound door facing it: {k4_rand} random, {k4_hint} hint; DIE_TILE=42:', k2)
print('die_hint.py part B lines (= model):', partB)
print('red-pip random faces:', [hex(c) for c in red_faces])
print('RATT text 407(A6)=1:', repr(ratt), '-> order', ratt_order, '= code', ratt_codes)
print(f'compound seeds: code 8 in {len(code8)} of {len(comp)}:', code8, '; codes', dict(sorted(comp_codes.items())))
print(f'cost: blind worst {blind_worst} presses, mean {blind_mean}; die {die_cost} (4 rolls + 4 presses), '
      f'{die_min} if the forced 4th corner is not rolled for')

# ---- svg ---------------------------------------------------------------------------------------------------------
WD, HT = 900, 1494
s = []; a = s.append
INK, MUTE, ACC, BAD, OK, GRIDC = '#1f2328', '#656d76', '#0969da', '#cf222e', '#1a7f37', '#d0d7de'
CC = ['#0969da', '#8250df', '#bf8700', '#1a7f37']          # corner colours TL TR BL BR
a('')                                                        # the <svg> header, written once the height is known
a('<title id="t">The die that knows the code</title>')
a('<desc id="d">Captive (1990): coded doors are four-corner combination locks with 24 possible orders and no feedback '
  'until the fourth press; the DIE item, rolled in front of one, shows the next corner instead of a number. '
  'Computed by gen_lock.py from the game\'s table at $e358 and stserver runs of $e270 and $1207c. Facts: lock.facts.md.</desc>')
a('<style>text{font-family:Helvetica,Arial,sans-serif;fill:%s;font-size:12px}.t{font-size:20px;font-weight:bold}'
  '.h{font-size:14px;font-weight:bold}.m{fill:%s}.c{font-family:Menlo,monospace;font-size:11px}'
  '.s{font-size:11px;fill:%s}.b{font-size:11px;font-weight:bold}.k{font-size:9px;fill:%s}.l{font-size:12.5px}.q{font-size:11px;fill:%s}</style>'
  % (INK, MUTE, MUTE, MUTE, INK))
a('')                                                        # the background, sized with the header
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


def close(idx, bottom):
    x, y, w = PANELS[idx]
    s[idx] = f'<rect x="{x}" y="{y}" width="{w}" height="{bottom - y}" rx="6" fill="none" stroke="{GRIDC}"/>'
    return bottom


a('<text x="24" y="38" class="t">The die that knows the code</text>')
LEAD = ('Captive (Antony Crowther, Mindscape, 1990) is a real-time dungeon crawler: four droids raid procedurally generated '
        'bases on a series of planets. Some doors are combination locks. The player clicks the door\'s four corners in some '
        'order; only one of the 24 possible orders opens it, and the lock gives no sign of progress until the fourth click, '
        'so a wrong guess always costs four clicks (panels A and B). One item, the DIE, normally rolls a random face. Rolled '
        'while facing a coded door of the kind found inside a base, it shows instead a four with one red pip in the corner '
        'to press next (C). A fixed note, the MESSAGE FROM RATT, spells out one order, which is right for the first door of '
        'mission 1 (D).')
ly_ = para(24, 62, 852, LEAD, 'l', 17, cpx=6.0)


def panel(x, y, w, h, title, label):
    """Draw a panel's title; close() sizes its frame once its text is laid out."""
    idx = len(s)
    a('')
    PANELS[idx] = (x, y, w)
    a(f'<text x="{x+14}" y="{y+24}" class="h">{title}</text>')
    a(f'<text x="{x+w-14}" y="{y+24}" text-anchor="end" class="s" style="fill:{ACC}">{label}</text>')
    return idx


def door(x, y, sz, o, pressed=None, hl=None):
    """A door face: 2x2 corners; numbers = position in the order o (list of corners); pressed = set of corners."""
    a(f'<rect x="{x}" y="{y}" width="{sz}" height="{sz}" rx="2" fill="#f6f8fa" stroke="{MUTE}"/>')
    h = sz / 2
    for c in range(4):
        cx, cy = x + (c & 1) * h, y + (c >> 1) * h
        if pressed is not None and c in pressed:
            a(f'<rect x="{cx+1.5}" y="{cy+1.5}" width="{h-3}" height="{h-3}" rx="1.5" fill="{CC[c]}" fill-opacity="0.85"/>')
        if hl is not None and c == hl:
            a(f'<rect x="{cx+1}" y="{cy+1}" width="{h-2}" height="{h-2}" fill="none" stroke="{BAD}" stroke-width="2"/>')
        if o is not None:
            col = '#ffffff' if pressed is not None and c in pressed else CC[c]
            a(f'<text x="{cx+h/2}" y="{cy+h/2+4}" text-anchor="middle" class="b" style="fill:{col}">{o.index(c)+1}</text>')


# A: the state word and the table -----------------------------------------------------------------------------------
AY = ly_ + 8
pA = panel(24, AY, 852, 412, 'A. A door is a state word, and its code picks one of 24 corner orders',
      'read: $e358 in req4 and outside.snap; lock $e270 disassembled')
ex = trace(8, [0, 2, 1])[-1][1]               # $6087: code 8 after TL, BL, TR
bx, by, bw = 40, AY + 62, 30
groups = [(15, 14, '3rd corner', BAD), (13, 12, '2nd corner', BAD), (11, 10, '1st corner', BAD), (9, 9, '', MUTE),
          (8, 4, 'code 0..23', ACC), (3, 0, 'pressed: BR BL TR TL', OK)]
a(f'<text x="{bx}" y="{by-12}" class="b">door state word (list $1bee8, one per coded door), here ${ex:04x}: code 8 after TL, BL, TR</text>')
for b in range(16):
    X = bx + (15 - b) * bw
    bit = ex >> b & 1
    a(f'<rect x="{X}" y="{by}" width="{bw}" height="26" fill="{"#eaeef2" if bit else "#ffffff"}" stroke="{MUTE}"/>')
    a(f'<text x="{X+bw/2}" y="{by+17}" text-anchor="middle" class="c">{bit}</text>')
    a(f'<text x="{X+bw/2}" y="{by+38}" text-anchor="middle" class="k">{b}</text>')
for hi_, lo_, lab, col in groups:
    X0, X1 = bx + (15 - hi_) * bw + 2, bx + (16 - lo_) * bw - 2
    a(f'<line x1="{X0}" y1="{by+46}" x2="{X1}" y2="{by+46}" stroke="{col}" stroke-width="2"/>')
    val = (ex >> lo_) & ((1 << (hi_ - lo_ + 1)) - 1)
    dec = CN[val] if lab.endswith('corner') else str(val) if lab.startswith('code') else ''
    if lab.startswith('pressed'):
        dec = ' '.join(CN[c] for c in range(4) if val >> c & 1)
    if lab:
        a(f'<text x="{(X0+X1)/2}" y="{by+60}" text-anchor="middle" class="s" style="fill:{col}">{lab}</text>')
        a(f'<text x="{(X0+X1)/2}" y="{by+73}" text-anchor="middle" class="b" style="fill:{col}">{dec}</text>')
RX = bx + 16 * bw + 28
for k, t in enumerate(['Each press ($e270) sets the corner\'s bit in the low',
                       'nibble and writes the corner into the next 2-bit',
                       'slot of the high byte. On the 4th press the high',
                       'byte &amp; $fc is looked up in the table at $e358; the',
                       'door opens ($c420) only if the match is entry',
                       '"code". The 4th corner is never stored: it is',
                       'whichever is left. Corner c = 2 x bottom + right.']):
    a(f'<text x="{RX}" y="{by-12+15*k}" class="s">{t}</text>')
ty = AY + 168
a(f'<text x="40" y="{ty}" class="b">The table at $e358: 24 bytes, one per code. Bits 2-7 hold the first three corners, '
  f'bits 0-1 the fourth; together, every order of the 4 corners once</text>')
cw, chh, sz = 134, 46, 34
for i, b in enumerate(tab):
    col, row = i % 6, i // 6
    X, Y = 40 + col * cw, ty + 12 + row * chh
    if i == 8:
        a(f'<rect x="{X-4}" y="{Y-3}" width="{cw-6}" height="{chh-4}" rx="4" fill="#fff8c5" stroke="#d4a72c"/>')
    door(X, Y, sz, orders[i])
    a(f'<text x="{X+sz+8}" y="{Y+14}" class="b">code {i}</text>')
    a(f'<text x="{X+sz+8}" y="{Y+29}" class="c">${b:02x}</text>')
    if i in odd4:
        a(f'<rect x="{X-4}" y="{Y-3}" width="{cw-6}" height="{chh-4}" rx="4" fill="none" stroke="{BAD}" stroke-width="1.5"/>')
        a(f'<text x="{X+sz+38}" y="{Y+29}" class="k" style="fill:{BAD}">bits 0-1 = {CN[b & 3]}</text>')
    if i in req4_codes:
        a(f'<text x="{X+sz+44}" y="{Y+29}" class="k" style="fill:{ACC}">req4</text>')
for k, t_ in enumerate([
        f'Numbers: press order. Yellow: code 8, the mission 1 compound door (TL, BL, TR, BR). "req4": the codes of the three '
        f'coded doors ({", ".join(map(str, req4_codes))}) of the die runs\' base.',
        f'Red: code 9 is ${tab[9]:02x}. Its bits 0-1 say BL, but BL is already its 2nd corner; the lock ignores bits 0-1, '
        f'the die does not (panel C). ${tab[9] & 0xfc:02x} would be the clean entry.',
        f'The generator draws each door\'s code from the base RNG: high word of RNG x 24 (mapgen.md "Coded doors"; every code '
        f'0..23 occurs in its 80-base census).']):
    a(f'<text x="40" y="{ty+12+4*chh+8+15*k}" class="s">{t_}</text>')
y = para(40, ty + 12 + 4 * chh + 8 + 15 * 3 + 6, 820, 'Top: the 16 bits of one door\'s state word, bit 15 on the left; the '
         'coloured brackets group the bits into fields, decoded beneath. Below: the 24 entries of the game\'s order table. '
         'Each small square is a door seen from the front, its corners numbered 1 to 4 in the order that opens it (TL '
         'top-left, TR top-right, BL bottom-left, BR bottom-right); the hex byte is the table entry.', lead='How to read.')
y = para(40, y + 4, 820, 'A door remembers only its code and the corners pressed so far. The table turns a code, 0 to 23, '
         'into one of the 24 orders of four corners, each used once. Entry 9 holds an inconsistent fourth corner, which the '
         'lock ignores and the die does not.', lead='Takeaway.')
close(pA, y + 6)

# B: the lock over sequences ---------------------------------------------------------------------------------------
BY = y + 20
pB = panel(24, BY, 852, 330, 'B. The lock gives nothing away until the fourth press',
      f'proven: {n_seq} sequences, {n_press} presses, model = emulator')
rows = [('right order', [0, 2, 1, 3]), ('first two right', [0, 2, 3, 1]), ('wrong order', [1, 2, 0, 3]),
        ('a corner twice', [0, 0])]
a(f'<text x="40" y="{BY+46}" class="s">Door code 8 from state $0080. Each box: the corner clicked, the state word after it, '
  f'the corners lit (pressed bits).</text>')
for r, (name, seq) in enumerate(rows):
    Y = BY + 60 + r * 50
    a(f'<text x="40" y="{Y+24}" class="b">{name}</text>')
    tr = trace(8, seq)
    for k, (c, st_, ev) in enumerate(tr):
        X = 160 + k * 120
        pressed = {cc for cc in range(4) if st_ >> cc & 1}
        door(X, Y + 2, 34, None, pressed, c)
        a(f'<text x="{X+42}" y="{Y+16}" class="b" style="fill:{CC[c]}">{CN[c]}</text>')
        a(f'<text x="{X+42}" y="{Y+31}" class="c">${st_:04x}</text>')
        if k < len(tr) - 1:
            a(f'<text x="{X+96}" y="{Y+24}" class="m">&#8594;</text>')
    last = tr[-1][2]
    X = 160 + len(tr) * 120 - 10
    if last == 'open':
        a(f'<text x="{X}" y="{Y+24}" class="b" style="fill:{OK}">opens ($c420)</text>')
    else:
        a(f'<text x="{X}" y="{Y+24}" class="b" style="fill:{BAD}">cleared to $0080 on press {len(tr)}</text>')
ty = BY + 272
for k, t in enumerate([
        f'All 256 four-press sequences for each of the 24 codes, run through $e270 under stserver: the state word matched the',
        f'model on all {n_press} presses, and the door opened {len(opens)} times, once per code, on its own order. All {len(perm_wrong)} wrong orders',
        f'of four different corners clear only on press 4. An early clear is always a corner pressed twice (cleared at press 2:',
        f'{clear_at[2]}, press 3: {clear_at[3]}, press 4: {clear_at[4]}). Every in-zone press also calls $e370, right or wrong (inferred: a click sound).']):
    a(f'<text x="40" y="{ty+15*k}" class="s">{t}</text>')
y = para(40, ty + 15 * 4 + 6, 820, 'Each row is one sequence of clicks on a code-8 door, left to right. A square shows the '
         'corners lit after the click (filled) and the corner just clicked (red outline); beside it are that corner\'s name '
         'and the state word in hex.', lead='How to read.')
y = para(40, y + 4, 820, 'Nothing tells a right corner from a wrong one. Three right clicks and three wrong ones look the '
         'same until the fourth, which either opens the door or resets it, so a player without help can only try whole '
         'orders.', lead='Takeaway.')
close(pB, y + 6)

# C: the die -------------------------------------------------------------------------------------------------------
CY = y + 20
pC = panel(24, CY, 852, 380, 'C. The DIE ($1207c): rolled facing a coded door, it shows the next corner',
      f'proven: {da[0]}/{da[1]} and {die_ok}/{die_n} hints; controls {da[2]}/{da[3]}, {ctrl_ok}/{ctrl_n}')
z = 3
fx, fy = 40, CY + 58
a(f'<text x="{fx}" y="{fy-10}" class="b">A normal roll: one of 12 faces ($20-$2b), drawn by the game\'s $12168</text>')
for i, ch in enumerate(range(0x20, 0x2c)):
    X = fx + (i % 6) * 54 + (i // 6) * 0
    Y = fy + (i // 6) * 62
    a(f'<image x="{X}" y="{Y}" width="{14*z}" height="{14*z}" xlink:href="data:image/png;base64,{b64(ch, z)}" '
      f'style="image-rendering:pixelated"/>')
    a(f'<text x="{X+21}" y="{Y+54}" text-anchor="middle" class="k">${ch:02x}</text>')
hx = fx + 6 * 54 + 140
a(f'<text x="{hx}" y="{fy-10}" class="b">Facing a closed kind-2 coded door: $30+c</text>')
for c in range(4):
    X = hx + c * 66
    a(f'<image x="{X}" y="{fy}" width="{14*z}" height="{14*z}" xlink:href="data:image/png;base64,{b64(0x30 + c, z)}" '
      f'style="image-rendering:pixelated"/>')
    a(f'<text x="{X+21}" y="{fy+54}" text-anchor="middle" class="k">${0x30+c:02x}</text>')
    a(f'<text x="{X+21}" y="{fy+68}" text-anchor="middle" class="b" style="fill:{CC[c]}">{CN[c]}</text>')
a(f'<text x="{hx}" y="{fy+90}" class="s">A four with one red pip: the corner to press next.</text>')
rx, ry = hx, fy + 112
a(f'<text x="{rx}" y="{ry}" class="b">The rule ($1210e-$1213c)</text>')
for k, t in enumerate(['n = corners already lit (counted, not checked)',
                       'face = $30 + ((table[code] ror 2(n+1)) &amp; 3)']):
    a(f'<text x="{rx}" y="{ry+16+14*k}" class="{"c" if k == 1 else "s"}">{t}</text>')
b8 = tab[8]
a(f'<text x="{rx}" y="{ry+52}" class="s">code 8, ${b8:02x} = {b8 >> 6 & 3:02b} {b8 >> 4 & 3:02b} {b8 >> 2 & 3:02b} {b8 & 3:02b}:</text>')
for n in range(4):
    f_ = die((8 << 4) | sum(1 << c for c in orders[8][:n]))
    a(f'<text x="{rx + n*84}" y="{ry+68}" class="c">n={n}: <tspan style="fill:{CC[f_-0x30]};font-weight:bold">{CN[f_-0x30]}</tspan></text>')
ty = fy + 146
for k, t in enumerate([
        f'Values 1 to 6, each in two orientations;',
        f'odd values have red pips (read from the crops).',
        f'The roll is an LCG at 15218(A6), retried above 11.']):
    a(f'<text x="40" y="{ty+15*k}" class="s">{t}</text>')
ty = fy + 206
for k, t in enumerate([
        f'Proven: die_all.py on the req4 base (three kind-2 doors, codes {", ".join(map(str, da_codes))}), party poked beside each door from both open sides,',
        f'0-3 corners lit: next corner {da[0]}/{da[1]}; facing away {da[2]}/{da[3]} random. This census: every code, all 15 lit sets (including {wrong_prefix}',
        f'that are not a prefix of the order), 3 rolls each: {die_ok}/{die_n} = the rule. The compound door (tile $44, kind 4): {k4_rand}/{k4_rand} random;',
        f'the same door with its tile poked to $42 (kind 2): hints {", ".join("$" + v for v, _ in (x[0] for x in k2))} for 0-3 lit, its order TL BL TR BR.']):
    a(f'<text x="40" y="{ty+15*k}" class="s">{t}</text>')
ty += 70
a(f'<text x="40" y="{ty}" class="b" style="fill:{BAD}">A slip in the table: for code 9 (${tab[9]:02x}) the 4th hint is {CN[bad_hint]}, a corner already lit. '
  f'Pressing it clears the lock;</text>')
a(f'<text x="40" y="{ty+15}" class="s" style="fill:{BAD}">the corner left over, {CN[orders[9][3]]}, opens it (census: '
  f'{" ".join(CN[c] for c in orders[9][:3] + [bad_hint])} clears, {" ".join(CN[c] for c in orders[9])} opens; the die shows '
  f'${0x30 + bad_hint:02x} 3/3 after three lit).</text>')
y = para(40, ty + 15 + 22, 820, 'Left: the 12 ordinary faces as the game draws them, pixels enlarged. Right: the four hint '
         'faces, one per corner, and the rule that picks one; n is how many corners are already lit, and the table is the '
         'one in panel A. "Kind 2" and "kind 4" are door types set by the low bits of the door\'s tile: the doors inside '
         'the req4 base are kind 2, the door outside mission 1\'s base is kind 4.', lead='How to read.')
y = para(40, y + 4, 820, 'The die reads the door\'s order straight from the table, so a door it works on takes at most 4 '
         'rolls and 4 clicks. It counts lit corners without checking them: after a wrong click it still shows the true '
         'order\'s next corner. On a code-9 door its fourth hint is wrong.', lead='Takeaway.')
close(pC, y + 6)

# D: cost and the RATT note ---------------------------------------------------------------------------------------
DY = y + 20
pD = panel(24, DY, 852, 206, 'D. What the die is worth', 'computed; RATT text proven, its delivery inferred')
bars = [(f'blind, worst case: 24 orders x 4 presses', blind_worst, BAD),
        (f'blind, on average (12.5 orders)', blind_mean, '#d1802d'),
        (f'with the die: 4 rolls + 4 presses', die_cost, OK)]
NX = 540
scale = 2.3
for k, (lab, v, col) in enumerate(bars):
    Y = DY + 44 + k * 30
    a(f'<rect x="40" y="{Y}" width="{v*scale:.1f}" height="20" fill="{col}" fill-opacity="0.8"/>')
    a(f'<text x="{40+v*scale+8:.1f}" y="{Y+15}" class="b">{v:g}</text>')
    a(f'<text x="{40+v*scale+34:.1f}" y="{Y+15}" class="s">{lab}</text>')
for k, t in enumerate([f'Three rolls are enough ({die_min} actions): the 4th corner is the one left',
                       '(and for code 9, the 4th roll is wrong). A failed order always costs',
                       '4 presses: the lock clears after the 4th, so attempts share none.']):
    a(f'<text x="40" y="{DY+148+15*k}" class="s">{t}</text>')
a(f'<rect x="{NX}" y="{DY+40}" width="322" height="150" rx="4" fill="#fffbea" stroke="#d4a72c"/>')
a(f'<text x="{NX+12}" y="{DY+60}" class="b">MESSAGE FROM RATT (item $66), text 1 of 3:</text>')
a(f'<text x="{NX+12}" y="{DY+78}" class="c">{ratt.split(",")[0]},{ratt.split(",")[1]},</text>')
a(f'<text x="{NX+12}" y="{DY+92}" class="c">{",".join(ratt.split(",")[2:]).strip()}</text>')
door(NX + 266, DY + 66, 40, orders[8])
for k, t in enumerate(['Fixed text at $13906, the same in three bases. It is',
                       'code 8: the compound door of mission 1 target 1,',
                       f'and of {len(code8)} of the {len(comp)} compound seeds tried. Compound',
                       'doors are kind 4, so the die gives them no hint; this',
                       'note is the only clue, right for the first door only.']):
    a(f'<text x="{NX+12}" y="{DY+112+13*k}" class="s">{t}</text>')
y = para(40, DY + 206, 820, 'The bars count clicks (and rolls) needed to open one door. Blind means trying orders one '
         'after another; the average assumes every code is equally likely and no order is tried twice.', lead='How to read.')
y = para(40, y + 4, 820, f'The die cuts a door from {blind_mean:g} actions on average to at most {die_cost}; for the '
         'compound door it gives no hint, and the RATT note is the only clue.', lead='Takeaway.')
close(pD, y + 6)
y += 32
a(f'<text x="24" y="{y}" class="h">How we know</text>')
y = para(24, y + 20, 852, 'proven: the game\'s own routines were run in an Atari ST emulator and agreed with a Python model '
         'every time. computed: worked out by this figure\'s script. inferred: read from the 68000 code but not run.',
         'q', lead='Labels.')
y = para(24, y + 3, 852, 'stserver runs the emulator as a server that a script drives, calling one game routine at a time '
         'with inputs written into memory ("labelled pokes", each one recorded). A census runs every case: all 256 '
         'four-click sequences for each of the 24 codes, or every code with every set of lit corners. A control repeats a '
         'test where the effect should be absent (the door left as kind 4): the die then gives random faces, so the test can '
         'tell. die_all.py, die_hint.py and ratt_msg.py are the earlier scripts this figure re-runs.', 'q', lead='Checks.')
y = para(24, y + 3, 852, 'req4 is mission 1\'s base just after entry (reached by setting the level-request word to 4). '
         'outside.snap is the compound, the surface level where the party lands, in front of mission 1\'s base door. Hex '
         'numbers such as $e270 are addresses of the game\'s code; item $66 is an item type.', 'q', lead='States.')
HT = y + 44
a(f'<text x="24" y="{HT-30}" class="s">Inferred: that the die runs when the player uses it, and how the RATT note reaches the party '
  f'(item code read, not played).</text>')
a(f'<text x="24" y="{HT-15}" class="s">Every face and state word above comes from stserver calls of the game\'s own routines, with labelled pokes.</text>')
a('</svg>')
s[0] = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {WD} {HT}" '
        f'width="{WD}" height="{HT}" role="img" aria-labelledby="t d">')
s[4] = f'<rect width="{WD}" height="{HT}" fill="#ffffff"/>'
open(os.path.join(OUT, 'lock.svg'), 'w').write('\n'.join(s))
print('wrote', os.path.join(OUT, 'lock.svg'))
