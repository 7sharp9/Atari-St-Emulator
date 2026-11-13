#!/usr/bin/env python3
"""Infographic: how Captive (1990) generates its whole star map from the mission number (world.md section 1).

usage (from M68000/): uv run python -I reversing/captive/py/infographics/gen_universe.py [outdir]
       (default scratchpad/captive/infographics; inputs and the rendered screens in its data/)
Writes universe.svg and prints every number it draws. Facts and sources: universe.facts.md.

Inputs, all computed or read here, never typed in:
  - scratchpad/captive/mission1.snap (mission index 0, "CAPTIVE MISSION 0001"): the generated tables in RAM,
    the coordinate table $3047c, the orbit table $303d6, the syllable tables $30706..$30785;
  - callcap deltas cc_m0.json, cc_m1.json, cc_m7.json in scratchpad/captive/infographics/data: the generator re-run from $302c6 on
    mission1.snap, after `w 1ef86 000N0001` for N = 1, 7 (the poke is not in the delta; index 0 has no poke).
    Recreate them with
      printf 'w 1ef86 00010001\\ncallcap 302c6 3000000 <data>/cc_m1.json\\nq\\n' | ATARI_NOTRACE=1 \\
        dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/captive/mission1.snap repl --disk-a scratchpad/captive/tmb097.st
  - the rendered screens of mission1.snap and star.snap (tools/snap_render.py, run here);
  - reversing/captive/py/world/universe.py (the proven model); the step-counting chain below is a second copy of
    the same routines, asserted equal to it and to RAM.
"""
import base64, html, io, json, os, struct, subprocess, sys, textwrap
from collections import Counter


def repo_root():
    d = os.environ.get('M68000_ROOT') or os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
        p = os.path.dirname(d)
        if p == d:
            raise SystemExit('repo root (tools/rdis.py) not found')
        d = p
    return d


R = repo_root()
sys.path.insert(0, os.path.join(R, 'reversing', 'captive', 'py', 'world'))
import universe as U            # noqa: E402  (puts tools/ on the path too)
from gfxview import load_ram    # noqa: E402
from PIL import Image           # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(R, 'scratchpad', 'captive', 'infographics')
DATA = os.path.join(R, 'scratchpad', 'captive', 'infographics', 'data')
os.makedirs(OUT, exist_ok=True)
os.makedirs(DATA, exist_ok=True)
SNAP = os.path.join(R, 'scratchpad', 'captive', 'mission1.snap')
STAR = os.path.join(R, 'scratchpad', 'captive', 'star.snap')
A6 = U.A6

ram, _ = load_ram(SNAP)
W16 = lambda m, a: struct.unpack('>H', m[a:a + 2])[0]
mission0 = W16(ram, A6 + 14776)
xytab = list(ram[0x3047c:0x3047c + 32])
orbtab = [struct.unpack('>hh', ram[0x303d6 + 4 * i:0x303da + 4 * i]) for i in range(8)]
A, C = 0x5e5, 0x29


# ---- the LCG ($3049c) and its period --------------------------------------------------------------
def lcg(x):
    return (x * A + C) & 0xffff


seen = bytearray(65536); x = 0; period = 0
while True:
    seen[x] = 1; x = lcg(x); period += 1
    if x == 0:
        break
visited = sum(seen)
# low-bit periods (why the dots use ror.w #2): period of bit k of D0
def bit_period(k):
    s = [(v >> k) & 1 for v in [0]]
    v = 0; seq = []
    for _ in range(4096):
        v = lcg(v); seq.append((v >> k) & 1)
    for p in range(1, 4097):
        if all(seq[i] == seq[i + p] for i in range(len(seq) - p)):
            return p
bitp = [bit_period(k) for k in range(5)]


# ---- the generator chain, step by step ($302ca..$302e4) ------------------------------------------
def chain(mission):
    st = {'state': mission & 0xffff, 'n': 0}
    def step():
        st['state'] = lcg(st['state']); st['n'] += 1
        d0 = st['state']; return d0, ((d0 >> 2) | (d0 << 14)) & 0xffff
    stages = []
    n0 = st['n']; step(); step()                                     # $30430, $30432: two discards
    stages.append(('discard', st['n'] - n0, {}))
    n0 = st['n']; dots = []; rz = rd = 0                            # $30444..$30476
    while len(dots) < 51:
        _, d1 = step()
        x, y = d1 & 31, (d1 >> 5) & 31
        if x == 0 or y == 0:
            rz += 1; continue
        v = (xytab[x], xytab[y])
        if v in dots:
            rd += 1; continue
        dots.append(v)
    stages.append(('dots', st['n'] - n0, {'zero': rz, 'dup': rd}))
    n0 = st['n']; moons = []; rd = 0                                # $303fa..$3042a
    while len(moons) < 100:
        _, d1 = step()
        v = (1 + ((d1 * 50) >> 16), d1 & 7)
        if v in moons:
            rd += 1; continue
        moons.append(v)
    stages.append(('moons', st['n'] - n0, {'dup': rd}))
    n0 = st['n']; objs = [[0, 0, 0, 0] for _ in range(150)]; rd = 0   # $302fa
    for k in range(10):
        if mission == 0 and k == 0:
            slot = 0
        else:
            while True:
                d0, _ = step(); slot = (d0 * 150) >> 16
                if objs[slot] == [0, 0, 0, 0]:
                    break
                rd += 1
        objs[slot][3] = k + 1
    stages.append(('targets', st['n'] - n0, {'taken': rd}))
    n0 = st['n']                                                    # $3032c
    for i in range(150):
        d0, _ = step()
        if i < 50:
            objs[i][0], objs[i][1] = d0 & 31, (d0 >> 5) & 31
        else:
            objs[i][0], objs[i][1] = (d0 & 15) + 7, ((d0 >> 5) & 15) + 7
    stages.append(('sites', st['n'] - n0, {}))
    return dots, moons, objs, stages, st['state'], st['n']


def conv(c):                                                         # $3037a
    return (((c * 2) << 8) - 0x2600) & 0xffff


def s16(v):
    return v - 65536 if v & 0x8000 else v


def check(m, mission):
    """model tables vs RAM image m: (dots ok, moons ok, objs ok)"""
    stars, sxy, planets, pxy, objs, d0 = U.generate(mission, xytab, orbtab)
    a = sum((W16(m, A6 + 13566 + 4 * i), W16(m, A6 + 13568 + 4 * i)) == xy for i, xy in enumerate(sxy))
    b = sum((W16(m, A6 + 13770 + 4 * i), W16(m, A6 + 13772 + 4 * i)) == xy for i, xy in enumerate(pxy))
    c = sum(list(m[A6 + 14170 + 4 * i:A6 + 14174 + 4 * i]) == o for i, o in enumerate(objs))
    return (a, b, c), (stars, sxy, planets, pxy, objs, d0)


MISSIONS = {}
for idx in (0, 1, 7):
    cc = json.load(open(os.path.join(DATA, f'cc_m{idx}.json')))
    assert cc['outcome'] == 'returned' and cc['target'] == '0302c6'
    m = bytearray(ram)
    for a_, old, new in cc['mem']:
        m[a_] = new
    ok, model = check(m, idx)
    dots, moons, objs, stages, fin, nsteps = chain(idx)
    # second copy == model
    assert [(v >> 16, v & 0xffff) for v in model[0]] == dots
    assert [(dots[p], o) for p, o in moons] == [((v >> 16, v & 0xff), (v >> 8) & 0xff) for v in model[2]]
    assert objs == model[4] and fin == model[5]
    MISSIONS[idx] = dict(ok=ok, dots=dots, moons=moons, objs=objs, stages=stages, fin=fin, n=nsteps,
                         sxy=model[1], pxy=model[3], cc_d0=cc['regN'][0] & 0xffff, cc_steps=cc['steps'],
                         cc_bytes=len(cc['mem']))
    assert ok == (51, 100, 150), (idx, ok)
    assert fin == MISSIONS[idx]['cc_d0'], (idx, hex(fin), hex(MISSIONS[idx]['cc_d0']))
okram, _ = check(ram, mission0)
assert mission0 == 0 and okram == (51, 100, 150)
M1 = MISSIONS[0]
# moon parents: chain gives (parent planet slot, orbit slot); check against the model's packed values
for (p, o), v, in zip(M1['moons'], U.generate(0, xytab, orbtab)[2]):
    assert (v >> 8) & 0xff == o and (v >> 16, v & 0xff) == M1['dots'][p]

# landing-site byte periodicity: byte 0 & 15 is D0 & 15 over 150 consecutive steps -> period 16
b0 = [(o[0] if i < 50 else o[0] - 7) & 15 for i, o in enumerate(M1['objs'])]
rep16 = sum(b0[i] == b0[i + 16] for i in range(150 - 16))
raw0 = [o[0] if i < 50 else o[0] - 7 for i, o in enumerate(M1['objs'])]   # D0 & 31 or D0 & 15 before the +7
par = sum((raw0[i] & 1) != (raw0[i + 1] & 1) for i in range(149))
rep32 = sum(M1['objs'][i][0] == M1['objs'][i + 32][0] for i in range(50 - 32))

# ---- the screen (panel B) and the grid (panel C) ----------------------------------------------------
def render(snap, png):
    if os.path.exists(png):
        os.remove(png)
    subprocess.run([sys.executable, '-I', os.path.join(R, 'tools', 'snap_render.py'), snap, png], check=True,
                   stdout=subprocess.DEVNULL)
    return Image.open(png).convert('RGB')


scr = render(SNAP, os.path.join(DATA, 'm1.png'))
WHITE, GRIDC = (252, 252, 252), (180, 144, 108)
box = [(x, y) for y in range(68, 160) for x in range(55, 150)]   # the grid box (starscreen.py); title text excluded
white = {p for p in box if scr.getpixel(p) == WHITE}
cells = M1['dots']
best = None
for s_ in (1, 2, 3):
    for ox in range(40, 110):
        for oy in range(50, 120):
            n = sum((ox + s_ * x, oy + s_ * y) in white for x, y in cells)
            if best is None or n > best[0]:
                best = (n, s_, ox, oy)
fit_n, FS, FX, FY = best
hit = {(FX + FS * x, FY + FS * y) for x, y in cells}
unexpl = len(white - hit)
miss = [i for i, (x, y) in enumerate(cells) if (FX + FS * x, FY + FS * y) not in white]
gcol = Counter(x for x, y in box if scr.getpixel((x, y)) == GRIDC)
grow = Counter(y for x, y in box if scr.getpixel((x, y)) == GRIDC)
vlines = sorted(x for x, n in gcol.items() if n > 40)
hlines = sorted(y for y, n in grow.items() if n > 40)
vcells = [(x - FX) / FS for x in vlines]
hcells = [(y - FY) / FS for y in hlines]
assert vcells == hcells and all(c % 5 == 4 for c in vcells)
assert fit_n == 50 and miss == [0] and unexpl == 0 and len(white) == 50
assert rep16 == 134 and par == 149 and rep32 == 18
skip = [v for v in range(0, 39) if v not in xytab]
assert all(v % 5 == 4 for v in skip) and all(v % 5 != 4 for v in xytab)
allc = [c for idx in MISSIONS for d in MISSIONS[idx]['dots'] for c in d]
on_line = sum(c % 5 == 4 for c in allc)

# ---- names (panel D) ------------------------------------------------------------------------------
SYL = []
for t in U.SYL:
    e = []
    for i in range(16):
        a_ = t + 2 * i
        e.append(chr(ram[a_]) + (chr(ram[a_ + 1]) if ram[a_ + 1] else ''))
    SYL.append(e)
OBJ = 13
d4 = [OBJ]
v = lcg(OBJ); d4.append(v)
v = ((v >> 8) | (v << 8)) & 0xffff; d4.append(v)
v = lcg(v); d4.append(v)
v = lcg(v); d4.append(v)
nib = [(v >> (4 * k)) & 15 for k in range(4)]
nm = ''.join(SYL[k][nib[k]] for k in range(4))
assert nm == U.name(ram, 0, OBJ)
names = [U.name(ram, 0, i) for i in range(150)]
dupn = sum(c - 1 for c in Counter(names).values() if c > 1)
star = load_ram(STAR)[0]
star_sel = W16(star, A6 + 14782); star_mis = W16(star, A6 + 14776)
assert star_sel == OBJ + 1 and star_mis == 0
sscr = render(STAR, os.path.join(DATA, 'star.png'))
assert U.name(star, 0, OBJ) == nm


def png_uri(img, z):
    img = img.resize((img.width * z, img.height * z), Image.NEAREST)
    b = io.BytesIO(); img.save(b, 'PNG')
    return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()


# ---- print every number drawn ---------------------------------------------------------------------
print(f'LCG x*${A:x}+${C:x} = x*{A}+{C}; {A} mod 4 = {A % 4}; {C} odd; period from 0 = {period}, values visited {visited}')
print(f'D0 bit periods (bits 0..4): {bitp}')
for idx in MISSIONS:
    M = MISSIONS[idx]
    print(f'mission index {idx} (screen {idx+1:04d}): RAM match {M["ok"]}; stages {M["stages"]}; '
          f'{M["n"]} RNG steps; final D0 ${M["fin"]:04x} = callcap D0 ${M["cc_d0"]:04x}; '
          f'callcap {M["cc_steps"]} steps, {M["cc_bytes"]} bytes changed')
    print('  targets (object index, number):', sorted(((i, o[3]) for i, o in enumerate(M['objs']) if o[3]), key=lambda t: t[1]))
print(f'mission1.snap itself: {okram}')
print(f'site byte 0 low nibble repeats every 16 objects: {rep16}/{150-16}; parity alternates {par}/149; '
      f'planet byte 0 repeats every 32: {rep32}/{50-32}')
print(f'screen fit pixel = ({FX},{FY}) + {FS}*cell: {fit_n}/51 on white; misses {miss}; white {len(white)}, unexplained {unexpl}')
print(f'grid lines x {vlines} y {hlines} -> cells {vcells}')
print(f'coordinate table $3047c: {xytab}; skipped 0..38: {skip}; coords on a line (3 missions, {len(allc)}): {on_line}')
print(f'station cell {cells[0]}; map units of a cell c: c*512-$2600; station at {tuple(s16(v) for v in M1["sxy"][0])}')
print(f'orbit offsets $303d6: {orbtab}')
print(f'name obj {OBJ}: D4 chain {[hex(v) for v in d4]}, nibbles {nib}, syllables {[SYL[k][nib[k]] for k in range(4)]} -> {nm}; '
      f'star.snap 14782(A6)={star_sel}; duplicate names among 150 at mission 1: {dupn}')
print('syllable tables:', SYL)
print('first names:', names[:6], 'targets:', [(i, names[i]) for i, o in enumerate(M1['objs']) if o[3]])

# ---- svg ------------------------------------------------------------------------------------------
W, H = 900, 1632
s = []; a = s.append
INK, MUTE, ACC, BAD, GRID, GOLD = '#1f2328', '#656d76', '#0969da', '#cf222e', '#d0d7de', '#9a6700'
a('')                                       # the <svg> header, written once the height is known
a('<title id="t">A galaxy from one number</title>')
a('<desc id="d">Captive (Mindscape, 1990) builds each mission\'s star map, 50 planets, 100 moons, a space station, '
  '10 targets and their landing sites from one 16-bit linear congruential generator seeded with the mission '
  'number; body names come from the same generator seeded per body. Sources: reversing/captive/world.md section 1; '
  'model py/world/universe.py; RAM of scratchpad/captive/mission1.snap and callcap re-runs; drawn by gen_universe.py. '
  'Facts: universe.facts.md.</desc>')
a('<style>text{font-family:Helvetica,Arial,sans-serif;fill:%s;font-size:12px}.t{font-size:20px;font-weight:bold}'
  '.h{font-size:14px;font-weight:bold}.m{fill:%s}.c{font-family:Menlo,monospace;font-size:11.5px}'
  '.s{font-size:11px;fill:%s}.e{font-size:11px;font-style:italic;fill:%s}.l{font-size:12.5px}.k{font-size:11px;fill:%s}</style>'
  % (INK, MUTE, MUTE, ACC, INK))
a('')                                       # the background, sized with the header
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
    s[idx] = f'<rect x="{x}" y="{y}" width="{w}" height="{bottom - y}" rx="6" fill="none" stroke="{GRID}"/>'
    return bottom


a('<text x="24" y="38" class="t">A galaxy from one number</text>')
LEAD = ('Captive (Antony Crowther, Mindscape, 1990) is a real-time dungeon crawler: four droids raid procedurally '
        'generated bases on a series of planets. The player picks where to land on a star map holding a space station, '
        '50 planets, 100 moons and 10 numbered targets per mission. None of it is stored on the disk. When a mission '
        'starts, the game runs one 16-bit random number generator, seeded with the mission number, through a fixed chain '
        'of steps (panel A), so the same mission always gets the same map. A small table turns each draw into a position '
        'on the map screen and keeps every dot off the grid lines (B, C). The bodies\' names come from the same generator, '
        'reseeded per body (D), and a different seed gives a different galaxy (E).')
ly_ = para(24, 62, 852, LEAD, 'l', 17, cpx=6.0)


def panel(x, y, w, h, title, ev, below=False):
    """Draw a panel's title; close() sizes its frame once its text is laid out."""
    idx = len(s)
    a('')
    PANELS[idx] = (x, y, w)
    a(f'<text x="{x+14}" y="{y+24}" class="h">{title}</text>')
    if below:
        a(f'<text x="{x+14}" y="{y+42}" class="e">{ev}</text>')
    else:
        a(f'<text x="{x+w-14}" y="{y+24}" text-anchor="end" class="e">{ev}</text>')
    return idx


def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


# A: the chain ---------------------------------------------------------------------------------------
AY = ly_ + 8
pA = panel(24, AY, 852, 300, 'A. One generator, one pass ($30280)',
      f'proven: model = RAM {M1["ok"][0]}/51, {M1["ok"][1]}/100, {M1["ok"][2]}/150; final D0 = callcap D0')
a(f'<text x="44" y="{AY+52}" class="c">D0 = (D0 &#215; ${A:x} + ${C:x}) mod 65536</text>')
a(f'<text x="44" y="{AY+68}" class="s">$3049c: mulu, addi.w; the output D1 = ror.w #2 of D0.</text>')
a(f'<text x="330" y="{AY+52}" class="s" style="fill:{INK};font-weight:bold">Full period: all {visited:,} states, then back to the seed</text>')
a(f'<text x="330" y="{AY+68}" class="s">{A} = 4 &#215; {(A-1)//4} + 1 (a &#8722; 1 divisible by 4) and {C} is odd: the Hull-Dobell conditions for</text>')
a(f'<text x="330" y="{AY+82}" class="s">modulus 2^16. Checked by iteration: {period:,} steps from 0 return to 0. The low bits are weak</text>')
a(f'<text x="330" y="{AY+96}" class="s">(bit k of D0 repeats every {", ".join(str(p) for p in bitp[:4])}, ... steps), which ror.w #2 keeps out of the dot fields.</text>')
bx = [(f'seed', f'mission index', f'14776(A6) = {mission0}', ''),
      ('$30430', 'discard 2', f'{M1["stages"][0][1]} steps', ''),
      ('$30444', '51 map dots', f'{M1["stages"][1][1]} steps', f'{M1["stages"][1][2]["zero"]} zero, {M1["stages"][1][2]["dup"]} dup'),
      ('$303fa', '100 moons', f'{M1["stages"][2][1]} steps', f'{M1["stages"][2][2]["dup"]} dup'),
      ('$302fa', '10 targets', f'{M1["stages"][3][1]} steps', f'{M1["stages"][3][2]["taken"]} taken'),
      ('$3032c', '150 sites', f'{M1["stages"][4][1]} steps', '')]
x0, bw_, gap = 44, 116, 22
y0 = AY + 116
for k, (adr, what, n, rej) in enumerate(bx):
    X = x0 + k * (bw_ + gap)
    a(f'<rect x="{X}" y="{y0}" width="{bw_}" height="74" rx="5" fill="{ACC if k else INK}" fill-opacity="0.08" stroke="{ACC if k else INK}"/>')
    a(f'<text x="{X+bw_/2}" y="{y0+17}" text-anchor="middle" class="c" style="fill:{MUTE}">{adr}</text>')
    a(f'<text x="{X+bw_/2}" y="{y0+35}" text-anchor="middle" class="h" style="font-size:13px">{what}</text>')
    a(f'<text x="{X+bw_/2}" y="{y0+52}" text-anchor="middle" class="s" style="fill:{INK}">{n}</text>')
    if rej:
        a(f'<text x="{X+bw_/2}" y="{y0+66}" text-anchor="middle" class="s">rejected: {rej}</text>')
    if k:
        a(f'<line x1="{X-gap+2}" y1="{y0+37}" x2="{X-4}" y2="{y0+37}" stroke="{INK}" stroke-width="1.4"/>')
        a(f'<polygon points="{X-3},{y0+37} {X-9},{y0+33} {X-9},{y0+41}" fill="{INK}"/>')
        a(f'<text x="{X-gap/2}" y="{y0+30}" text-anchor="middle" class="c" style="font-size:9px;fill:{MUTE}">D0</text>')
outs = ['', '', '13566(A6) = $1eacc', '13770(A6) = $1eb98', 'byte 3 of 14170(A6)', 'bytes 0, 1 of 14170(A6)']
rules = ['', '', 'x, y = 5-bit fields of D1', 'planet 1 + D1&#215;50 &gt;&gt; 16,', 'object D0&#215;150 &gt;&gt; 16;',
         'planets D0 &amp; 31,']
rules2 = ['', '', 'via table $3047c (panel C)', 'orbit slot D1 &amp; 7', 'mission 1 forces object 0', 'moons (D0 &amp; 15) + 7']
for k in range(6):
    X = x0 + k * (bw_ + gap) + bw_ / 2
    for j, t in enumerate((outs[k], rules[k], rules2[k])):
        if t:
            a(f'<text x="{X}" y="{y0+90+14*j}" text-anchor="middle" class="s" style="{"fill:"+INK if j==0 else ""}">{t}</text>')
footA = [f'Mission 1 (index 0): {M1["n"]} draws, ending at D0 = ${M1["fin"]:04x}; missions 2 and 8: {MISSIONS[1]["n"]} and {MISSIONS[7]["n"]}, ending at '
         f'${MISSIONS[1]["fin"]:04x} and ${MISSIONS[7]["fin"]:04x}, the D0 the game returns under callcap.',
         f'$3037a/$3039e then turn cells into map units, c &#215; 512 &#8722; $2600; a moon adds &#177;160 on each axis by its orbit slot (table $303d6).',
         f'Site bytes use raw D0, whose low bits are short-period: their low nibble repeats every 16 objects ({rep16}/{150-16} in RAM), the low bit alternates ({par}/149).']
for k, t in enumerate(footA):
    a(f'<text x="44" y="{AY+256+15*k}" class="s">{t}</text>')
y = para(44, AY + 256 + 15 * len(footA) + 6, 812, 'The boxes are the generator\'s steps in the order they run, left to '
         'right; each hands its random state, in register D0, to the next. "steps" is how many random numbers the step '
         'drew for mission 1, and "rejected" counts draws thrown away (a coordinate of 0, a duplicate, a target already '
         'given out). Under each box: where the result goes in memory and the rule that turns a draw into it.',
         lead='How to read.')
y = para(44, y + 4, 812, 'Each step starts from the state the previous one left, so a rejected draw changes every later '
         'draw, yet the whole map is still fixed by the seed: the model reproduces every table and the final state exactly.',
         lead='Takeaway.')
close(pA, y + 6)

# B: the screen --------------------------------------------------------------------------------------
BY = y + 20
pB = panel(24, BY, 470, 490, 'B. Mission 1, generated over its real screen', f'proven: {fit_n}/51 generated dots on white pixels, {unexpl} white pixels unexplained', True)
cx0, cy0, cw, Z = 60, 67, 90, 4
crop = scr.crop((cx0, cy0, cx0 + cw, cy0 + cw))
ix, iy = 24 + (470 - cw * Z) / 2, BY + 52
a(f'<image x="{ix}" y="{iy}" width="{cw*Z}" height="{cw*Z}" xlink:href="{png_uri(crop, Z)}"/>')
P = lambda c, o: (o + FS * c - (cx0 if o == FX else cy0) + 0.5) * Z
for i, (x, y) in enumerate(cells):
    X, Y = ix + P(x, FX), iy + P(y, FY)
    if i == 0:
        a(f'<rect x="{X-6:.1f}" y="{Y-6:.1f}" width="12" height="12" fill="none" stroke="#f2cc0c" stroke-width="1.6"/>')
    else:
        a(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="5" fill="none" stroke="#ff4d4d" stroke-width="1.3"/>')
tgt = [(i, o[3]) for i, o in enumerate(M1['objs']) if o[3]]
def tgt_by_planet(M):                      # target numbers grouped by planet slot (a moon target at its parent)
    g = {}
    for i, o in enumerate(M['objs']):
        if o[3]:
            g.setdefault(i + 1 if i < 50 else M['moons'][i - 50][0], []).append(o[3])
    return g
TG1 = tgt_by_planet(M1)
print('mission 1 targets by planet slot:', TG1)
for slot, ks in TG1.items():
    x, y = cells[slot]
    X, Y = ix + P(x, FX), iy + P(y, FY)
    a(f'<text x="{X+6:.1f}" y="{Y-5:.1f}" class="s" style="fill:#7ee0ff;font-weight:bold">{",".join(map(str, sorted(ks)))}</text>')
st0 = cells[0]
a(f'<text x="{ix + P(st0[0], FX) - 8:.1f}" y="{iy + P(st0[1], FY) + 18:.1f}" class="s" style="fill:#f2cc0c">station</text>')
ly = iy + cw * Z + 16
capB = ['The map screen of mission1.snap, pixels &#215;4. Red rings: the 50 generated',
        'planets, each on a white pixel. Yellow box: dot 0, the space station, not drawn',
        'as a white pixel. Cyan: targets 1..10 (a moon target at its parent planet).',
        f'The fit was searched, not assumed: pixel = ({FX}, {FY}) + {FS} &#215; cell.']
for k, t in enumerate(capB):
    a(f'<text x="44" y="{ly+14*k}" class="s">{t}</text>')
bend = para(44, ly + 14 * len(capB) + 6, 432, 'A screenshot of the game\'s own mission 1 map, enlarged; the white pixels '
            'are planets as the game drew them, and the rings and box are where the model puts them.', lead='How to read.')
bend = para(44, bend + 4, 432, 'Every planet the game draws is one the model generated, and every white pixel is accounted '
            'for.', lead='Takeaway.')

# C: the coordinate table ----------------------------------------------------------------------------
CX = 506
pC = panel(CX, BY, 370, 490, 'C. No dot on a grid line', f'proven: {on_line} of {len(allc)} coordinates (missions 1, 2, 8) on a line', True)
a(f'<text x="{CX+20}" y="{BY+62}" class="s">The 5-bit field (0..31) indexes the 32-byte table at $3047c:</text>')
gx0, gy0, cwid = CX + 30, BY + 100, 8.0
for c in range(-1, 40):
    if c % 5 == 4:
        X = gx0 + (c + 0.5) * cwid
        a(f'<line x1="{X:.1f}" y1="{gy0-14}" x2="{X:.1f}" y2="{gy0+262}" stroke="#b4906c" stroke-width="1.6"/>')
for c in range(0, 40, 5):
    a(f'<text x="{gx0 + (c + 0.5) * cwid:.1f}" y="{gy0-18}" text-anchor="middle" class="s">{c}</text>')
a(f'<text x="{gx0-8}" y="{gy0-18}" text-anchor="end" class="s">cell</text>')
for i, val in enumerate(xytab):
    Y = gy0 + i * 8
    X = gx0 + (val + 0.5) * cwid
    a(f'<text x="{gx0-8}" y="{Y+3.5:.1f}" text-anchor="end" class="c" style="font-size:8px;fill:{MUTE}">{i}</text>')
    if i == 0:
        a(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="2.8" fill="#ffffff" stroke="{BAD}"/>')
        a(f'<text x="{gx0 + 8 * cwid:.1f}" y="{Y+3.5:.1f}" class="s" style="fill:{BAD};font-size:9px">&#8592; index 0 is rejected (beq $30446)</text>')
    else:
        a(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="2.8" fill="{ACC}"/>')
cy_ = gy0 + 32 * 8 + 22
capC = [f'Rows: index; columns: cell. The table skips {", ".join(str(v) for v in skip[:3])}, ..., {skip[-1]},',
        'every value that is 4 mod 5. The screen draws its grid (brown) at',
        f'cells {", ".join(str(int(c)) for c in vcells[:3])}, ..., {int(vcells[-1])}: {len(vlines)} lines each way, measured on its',
        'pixels. So the 32 entries are the 4 free columns of 8 squares, and',
        'no dot can touch a line. Index 0 is never used: column 0 is empty.']
for k, t in enumerate(capC):
    a(f'<text x="{CX+20}" y="{cy_+14*k}" class="s">{t}</text>')
cend = para(CX + 20, cy_ + 14 * len(capC) + 6, 334, 'Each blue dot is one entry of the table: its row is the 5-bit value '
            'drawn (0 to 31), its column the map cell that value becomes. Brown lines are where the screen draws its grid.',
            lead='How to read.')
cend = para(CX + 20, cend + 4, 334, 'The 32-entry table is what keeps dots off the lines: it lists only cells inside the '
            'grid squares. The cost is the first row and column of the first square, which no draw reaches.',
            lead='Takeaway.')
close(pB, max(bend, cend) + 6)
close(pC, max(bend, cend) + 6)

# D: names -------------------------------------------------------------------------------------------
DY = max(bend, cend) + 20
pD = panel(24, DY, 852, 310, 'D. A name for every body ($3066e)', 'proven on screen for object 13 only; other names inferred')
a(f'<text x="44" y="{DY+50}" class="s">Not stored and not part of the chain: each name is recomputed when shown, with the same LCG reseeded per body.</text>')
steps_ = [('seed', f'mission &#215; 150 + object = {OBJ}', d4[0]), ('LCG', '', d4[1]), ('ror.w #8', 'byte swap', d4[2]),
          ('LCG', '', d4[3]), ('LCG', '', d4[4])]
X = 44
for k, (op, note, val) in enumerate(steps_):
    a(f'<text x="{X}" y="{DY+76}" class="s">{op}</text>')
    a(f'<text x="{X}" y="{DY+94}" class="c" style="font-weight:bold">${val:04x}</text>')
    if note:
        a(f'<text x="{X}" y="{DY+110}" class="s">{note}</text>')
    X += 150 if k == 0 else 92
    if k < 4:
        a(f'<text x="{X-22}" y="{DY+94}" class="c" style="fill:{MUTE}">&#8594;</text>')
nx = 560
a(f'<text x="{nx}" y="{DY+76}" class="s">four nibbles, low first, pick one syllable each</text>')
for k in range(4):
    a(f'<text x="{nx + k*70}" y="{DY+94}" class="c">{nib[k]:x} &#8594; {SYL[k][nib[k]]}</text>')
tx0, ty0, tcw = 44, DY + 150, 25.5
for k in range(4):
    Y = ty0 + k * 22
    a(f'<text x="{tx0}" y="{Y+4}" class="c" style="fill:{MUTE};font-size:10px">${U.SYL[k]:x}</text>')
    for i in range(16):
        X = tx0 + 62 + i * tcw
        sel = i == nib[k]
        if sel:
            a(f'<rect x="{X-12}" y="{Y-10}" width="24" height="18" rx="3" fill="{ACC}" fill-opacity="0.15" stroke="{ACC}"/>')
        a(f'<text x="{X}" y="{Y+4}" text-anchor="middle" class="c" style="{"font-weight:bold" if sel else "fill:"+MUTE}">{SYL[k][i]}</text>')
for i in range(16):
    a(f'<text x="{tx0 + 62 + i*tcw}" y="{ty0-16}" text-anchor="middle" class="c" style="fill:{MUTE};font-size:9px">{i:x}</text>')
crop2 = sscr.crop((62, 174, 142, 188))
nxi = 520
a(f'<image x="{nxi}" y="{ty0-12}" width="{80*4}" height="{14*4}" xlink:href="{png_uri(crop2, 4)}"/>')
a(f'<text x="{nxi}" y="{ty0+60}" class="s">star.snap, object {star_sel} selected (14782(A6) = ${star_sel:x}): the screen</text>')
a(f'<text x="{nxi}" y="{ty0+74}" class="s">prints PLANET- and the generated {nm} for index {OBJ}.</text>')
a(f'<text x="44" y="{DY+252}" class="s">16^4 = 65,536 spellings. Mission 1\'s first planets come out {", ".join(names[:5])}; '
  f'{dupn} of its 150 names repeat an earlier one. The station is the fixed</text>')
a(f'<text x="44" y="{DY+266}" class="s">string STATION ($306fe). Objects 1..50 print PLANET-, 51..150 MOON- ($2ff6e). Every name '
  f'here except {nm} is computed by the model, not read off the screen.</text>')
a(f'<text x="44" y="{DY+286}" class="s">The entry takes D3 = 149 &#8722; object and forms mission &#215; 150 + 149 &#8722; D3 ($30686..$30692); '
  f'the seed is mission &#215; 150 + object either way.</text>')
y = para(44, DY + 306, 812, f'The top row works the name generator through for object {OBJ} of mission 1; each arrow is '
         'one operation on the 16-bit state. The four rows below are the game\'s syllable tables, and the boxed entry in '
         'each is the one picked by that nibble (4 bits) of the final state. The pixel strip is the game\'s own screen.',
         lead='How to read.')
y = para(44, y + 4, 812, 'Names are not stored. One 16-bit seed per body regenerates the name whenever the body is labelled '
         '(inferred from the code), and four syllables picked by four nibbles give 16^4 = 65,536 possible spellings.',
         lead='Takeaway.')
close(pD, y + 6)

# E: three missions ----------------------------------------------------------------------------------
EY = y + 20
pE = panel(24, EY, 852, 0, 'E. Three missions, three galaxies (moons and targets drawn)',
      'proven: each 51/51, 100/100, 150/150 vs RAM')
mw = 250
for j, idx in enumerate((0, 1, 7)):
    M = MISSIONS[idx]
    ox_, oy_ = 44 + j * (mw + 28), EY + 56
    sc_ = mw / (40 * 512)
    def MX(u): return ox_ + (s16(u) + 0x2600 + 512) * sc_
    def MY(u): return oy_ + (s16(u) + 0x2600 + 512) * sc_
    a(f'<rect x="{ox_}" y="{oy_}" width="{mw}" height="{mw}" fill="#0d1117"/>')
    for c in range(-1, 40):
        if c % 5 == 4:
            q = conv(c) if c >= 0 else (-512 - 0x2600) & 0xffff
            a(f'<line x1="{MX(q):.1f}" y1="{oy_}" x2="{MX(q):.1f}" y2="{oy_+mw}" stroke="#6e5a44" stroke-width="0.8"/>')
            a(f'<line x1="{ox_}" y1="{MY(q):.1f}" x2="{ox_+mw}" y2="{MY(q):.1f}" stroke="#6e5a44" stroke-width="0.8"/>')
    for (x, y) in M['pxy']:
        a(f'<circle cx="{MX(x):.1f}" cy="{MY(y):.1f}" r="1.1" fill="#8b949e"/>')
    for i, (x, y) in enumerate(M['sxy']):
        if i == 0:
            a(f'<rect x="{MX(x)-3:.1f}" y="{MY(y)-3:.1f}" width="6" height="6" fill="#f2cc0c"/>')
        else:
            a(f'<circle cx="{MX(x):.1f}" cy="{MY(y):.1f}" r="2.2" fill="#ffffff"/>')
    for i, o in enumerate(M['objs']):
        if o[3]:
            x, y = M['sxy'][i + 1] if i < 50 else M['pxy'][i - 50]
            a(f'<circle cx="{MX(x):.1f}" cy="{MY(y):.1f}" r="4.5" fill="none" stroke="#ff4d4d" stroke-width="1.2"/>')
    for slot, ks in tgt_by_planet(M).items():
        x, y = M['sxy'][slot]
        a(f'<text x="{MX(x)+5:.1f}" y="{MY(y)-4:.1f}" class="s" style="fill:#7ee0ff;font-size:9px">{",".join(map(str, sorted(ks)))}</text>')
    a(f'<text x="{ox_}" y="{oy_+mw+18}" class="h" style="font-size:12px">CAPTIVE MISSION {idx+1:04d}: seed {idx}</text>')
    a(f'<text x="{ox_}" y="{oy_+mw+33}" class="s">{M["n"]} draws, D0 ends ${M["fin"]:04x}; '
      f'{"the snapshot as it stands" if idx == 0 else "poked, re-run by callcap"}</text>')
ey2 = EY + 56 + mw + 54
a(f'<text x="44" y="{ey2}" class="s">White: planets; yellow square: the station; grey: moons, at &#177;160 units on each axis from their planet (a cell '
  f'is 512); red rings: targets 1..10.</text>')
a(f'<text x="44" y="{ey2+14}" class="s">Mission 1 always puts target 1 on object 0 ({names[0]}). Missions 2 and 8: index poked into 14776(A6), '
  f'$302c6 re-run under callcap, model = every table.</text>')
y = para(44, ey2 + 34, 812, 'Each square is one mission\'s whole map, drawn from the model\'s tables, which equal the '
         'game\'s memory for that mission. The seed is the mission index, the mission number minus one.',
         lead='How to read.')
y = para(44, y + 4, 812, 'Only the seed changes between the three maps. The layout rules stay the same: dots inside grid '
         'squares, moons at the eight compass points around their planet.', lead='Takeaway.')
close(pE, y + 6)
y += 32
a(f'<text x="24" y="{y}" class="h">How we know</text>')
y = para(24, y + 20, 852, 'a linear congruential generator computes each number from the last as x × a + c, keeping '
         'the low 16 bits. D0 and D1 are 68000 registers; ror.w #2 rotates a 16-bit word right by 2 bits. Hex numbers '
         'such as $30280 are addresses of the game\'s code; 13566(A6) and the like are addresses of its tables, '
         'counted from the register A6 that points at the game\'s variables.', 'k', lead='Terms.')
y = para(24, y + 3, 852, 'universe.py is a Python model of every step. "model = RAM 51/51" means its 51 map dots equal '
         'the 51 the game holds in memory. mission1.snap and star.snap are saved emulator states of the game at its star '
         'map. callcap makes the emulator call one game routine from a saved state and record the registers and memory it '
         'changes; for missions 2 and 8 the mission number was written into memory ("poked") and the generator re-run '
         'this way.', 'k', lead='Checks.')
y = para(24, y + 3, 852, 'proven: checked against the game in an Atari ST emulator. computed: worked out by this '
         'figure\'s script. inferred: read from the code but not checked.', 'k', lead='Labels.')
H = y + 16
a('</svg>')
s[0] = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" role="img" aria-labelledby="t d">')
s[4] = f'<rect width="{W}" height="{H}" fill="#ffffff"/>'
p = os.path.join(OUT, 'universe.svg')
open(p, 'w').write('\n'.join(s))
print('wrote', p)
