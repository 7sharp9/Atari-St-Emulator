#!/usr/bin/env python3
"""Infographic: the self-patching span filler $4678 and its colour setup $494c (render.md section 5).

usage: gen_span.py [outdir] [--emu]   (default WORK/infographics; writes span.svg, span_emu.json and prints
the figures it draws). The emulator is run once (callcap $494c for all 64 colour codes, then callcap $4678 on
the rows the figure shows plus a verification set) and its raw output cached in span_emu.json; --emu re-runs it.
Every byte in the figure is read from c_s30.snap or from those callcaps; every pixel drawn is an emulator
output row. The pixel model checked against them is span_gate.py's (780/780 there). Facts: span.facts.md."""
import pathlib as _pl, sys as _sys
_here = _pl.Path(__file__).resolve().parent
_sys.path.insert(0, str(_here.parent)); _sys.path.insert(0, str(_here.parent / 'render'))
_sys.path.insert(0, str(_here.parents[4] / 'tools'))
from ccpaths import *
import json, random, struct

args = [a for a in _sys.argv[1:] if not a.startswith('--')]
OUT = _pl.Path(args[0]) if args else WORK / 'infographics'
OUT.mkdir(parents=True, exist_ok=True)
CACHE = OUT / 'span_emu.json'
RAM = ram(ANCHOR)
w16 = lambda a: struct.unpack_from('>H', RAM, a)[0]
l32 = lambda a: struct.unpack_from('>I', RAM, a)[0]
s16 = lambda v: v - 0x10000 if v >= 0x8000 else v

# ---- tables read from the snapshot --------------------------------------------------------------
PAIRS = [(RAM[0x1544 + 2 * c], RAM[0x1545 + 2 * c]) for c in range(64)]
SOLID = [([w16(0x49e4 + 16 * i + 2 * k) for k in range(4)], l32(0x49ec + 16 * i), l32(0x49f0 + 16 * i)) for i in range(16)]
ROW_AA = [(l32(0x4ae4 + 8 * i), l32(0x4ae8 + 8 * i)) for i in range(16)]   # indexed by the second colour
ROW_55 = [(l32(0x4b64 + 8 * i), l32(0x4b68 + 8 * i)) for i in range(16)]   # indexed by the first colour
LMASK = [w16(0x4658 + 2 * i) for i in range(16)]
RMASK = [w16(0x476c + 2 * i) for i in range(16)]
VP = l32(0x6fc)                                    # the viewport block A3 points at ($444c: movea.l $6fc.w,A3)
VX, VW = s16(w16(VP)), s16(w16(VP + 16))
from gfxview import load_video_regs, snapshot_regs
PAL = load_video_regs(str(ANCHOR))['palette_words']
SREGS, _ = snapshot_regs(str(ANCHOR))
def rgb(i):
    v = PAL[i]
    return '#%02x%02x%02x' % tuple(((v >> s) & 7) * 255 // 7 for s in (8, 4, 0))
assert all(a == b for a, b in PAIRS[:16]) and all(a != b for a, b in PAIRS[16:])
assert SREGS['a3'] == VP

# the patch $494c should make, derived from the tables by reading its code (render.md 5)
def ror1(v):
    return ((v >> 1) | ((v & 1) << 15)) & 0xffff
def ror_words(v):
    return (ror1(v >> 16) << 16) | ror1(v & 0xffff)
def derive(c):
    c1, c2 = PAIRS[c]
    d = {0x9ee: 0x7f, 0x9ef: 0xff, 0x9f0: 0x80, 0x9f1: 0x01}
    if c1 == c2:
        d[0x46c0] = 0x69
        ops, a0, a5 = SOLID[c1]
        for base in (0x46e8, 0x4758):
            for k, op in enumerate(ops):
                d[base + 2 * k] = op >> 8; d[base + 2 * k + 1] = op & 255
        return d, a0, a5
    d[0x46c0] = 0x68
    i0 = (ROW_55[c1][0] + ROW_AA[c2][0]) & 0xffffffff
    i5 = (ROW_55[c1][1] + ROW_AA[c2][1]) & 0xffffffff
    for addr, v in ((0x47b4, i0), (0x47ba, i5), (0x47c2, ror_words(i0)), (0x47c8, ror_words(i5))):
        for k in range(4):
            d[addr + k] = (v >> (24 - 8 * k)) & 255
    return d, ROW_AA[c2][0], ROW_AA[c2][1]
PATCHED = [0x46c0] + list(range(0x46e8, 0x46f0)) + list(range(0x4758, 0x4760)) + list(range(0x47b4, 0x47cc))

# ---- emulator runs ------------------------------------------------------------------------------
ROWBASE = l32(0x1248)                              # the screen buffer the filler draws into (A6 = $1248 + 160 y)
def row_addr(y):
    return ROWBASE + 160 * y
random.seed(7)
RAND = bytes(random.getrandbits(8) for _ in range(160))
def fill_row(colour):
    words = [0xffff if (colour >> p) & 1 else 0 for p in range(4)]
    return b''.join(struct.pack('>HHHH', *words) for _ in range(20))
SENT = (0x7fff, 0x8001)                            # what $494c writes to $9ee / $9f0

# jobs: (tag, code, xl, xr, row y (D7 high word), ($9ee, $9f0) before, background bytes)
jobs = []
EX_A = (9, 5, 42, 6)                               # panel A: colour 9 over colour 6, screen x 37..74
jobs.append(('A', 9, 5, 42, 40, SENT, fill_row(6)))
for c in range(16):                                # panel B: each solid colour, same span, over colour 0
    jobs.append(('B', c, 5, 42, 41 + c, SENT, fill_row(0)))
EX_C = 32                                          # panel C: one dither, six consecutive rows
for k in range(6):
    jobs.append(('C', EX_C, 0, 31, 60 + k, SENT, fill_row(0)))
for c in range(16, 64):                            # panel C tiles: every dither, two rows
    for k in range(2):
        jobs.append(('T', c, 0, 7, 70 + k, SENT, fill_row(0)))
# panel D: two steep slivers, each a chain from the sentinel, widened by the model, then checked row by row
SLIVERS = [[(2 + 3 * y, 3 + 3 * y) for y in range(8)], [(58 - 4 * y, 59 - 4 * y) for y in range(8)]]
def model(pre, c, xl, xr, y, pe):
    """span_gate.py's model: row bytes after $4678 plus the new ($9ee, $9f0); pe = the old pair."""
    buf = bytearray(pre)
    if xr < 0:
        return buf, pe
    xr = max(xr, s16(pe[1])); xl = min(xl, s16(pe[0]))
    trk = (xr & 0xffff, xl & 0xffff)
    c1, c2 = PAIRS[c]
    xl = max(xl, 0)
    if xl >= VW: return buf, trk
    xr = min(xr, VW - 1)
    if xr < xl: return buf, trk
    odd = (y + 1) & 1                              # D7's high word is incremented before btst #0 ($46a2, $47ac)
    for x in range(xl + VX, xr + VX + 1):
        v = c1 if c1 == c2 else ((c2 if x % 2 == 0 else c1) if odd else (c1 if x % 2 == 0 else c2))
        base = (x >> 4) * 8; b = 15 - (x & 15)
        for p in range(4):
            wv = struct.unpack_from('>H', buf, base + 2 * p)[0]
            wv = (wv & ~(1 << b)) | (((v >> p) & 1) << b)
            struct.pack_into('>H', buf, base + 2 * p, wv)
    return buf, trk
DCOL = 9
D_CHAINS = []
for si, sl in enumerate(SLIVERS):
    pe = SENT; chain = []
    for y, (xl, xr) in enumerate(sl):
        _, trk = model(fill_row(0), DCOL, xl, xr, 80 + 10 * si + y, pe)
        jobs.append(('D', DCOL, xl, xr, 80 + 10 * si + y, pe, fill_row(0)))
        chain.append((xl, xr, pe, trk)); pe = trk
    D_CHAINS.append(chain)
# verification: every code, both phases, spans that cross words, sit in one word, clip, or are empty
VSPANS = [(5, 42), (3, 3), (17, 18), (0, 255), (250, 300), (-5, 10), (10, -3), (100, 240)]
for c in range(64):
    for (xl, xr) in VSPANS:
        for y in (30, 31):
            for pe in (SENT, (60, 80)):
                jobs.append(('V', c, xl, xr, y, pe, RAND))

def run_emulator():
    from rig import repl, parse_callcaps
    out = repl([f'callcap 494c 20000 D0={c:x}' for c in range(64)])
    cc = parse_callcaps(out)
    assert len(cc) == 64 and all(r['status'] == 'returned' for r in cc), out[-800:]
    setup = []
    for r in cc:
        mem = bytearray(RAM)
        for a, (o, n) in r['mem'].items(): mem[a] = n
        a0 = r['regs'].get('A0', (0, SREGS['a0']))[1]; a5 = r['regs'].get('A5', (0, SREGS['a5']))[1]
        setup.append(dict(mem={a: mem[a] for a in PATCHED + [0x9ee, 0x9ef, 0x9f0, 0x9f1]}, A0=a0, A5=a5,
                          changed=sorted(r['mem'])))
    cmds, poked = [], {}
    for j in jobs:
        y, bg = j[4], j[6]
        if poked.get(y) != bg:
            cmds += [f'w {row_addr(y) + i:x} {bg[i:i + 4].hex()}' for i in range(0, 160, 4)]; poked[y] = bg
    # the rows must not be repoked between jobs that share them; check
    rows_bg = {}
    for j in jobs:
        assert rows_bg.setdefault(j[4], j[6]) == j[6], j[:5]
    for (tag, c, xl, xr, y, pe, bg) in jobs:
        m = setup[c]['mem']
        for g in sorted({a & ~3 for a in PATCHED}):
            cmds.append(f'w {g:x} ' + ''.join('%02x' % m.get(g + k, RAM[g + k]) for k in range(4)))
        cmds.append(f'w 9ee {pe[0]:04x}{pe[1]:04x}')
        cmds.append(f'callcap 4678 20000 D1={xl & 0xffff:x} D2={xr & 0xffff:x} D7={y << 16:x} '
                    f'A6={row_addr(y):x} A0={setup[c]["A0"]:x} A5={setup[c]["A5"]:x}')
    res = [r for r in parse_callcaps(repl(cmds)) if r['addr'] == 0x4678]
    assert len(res) == len(jobs), (len(res), len(jobs))
    runs = []
    for (tag, c, xl, xr, y, pe, bg), r in zip(jobs, res):
        row = bytearray(bg); ra = row_addr(y)
        for a, (o, n) in r['mem'].items():
            if ra <= a < ra + 160: row[a - ra] = n
        tr = bytearray(struct.pack('>HH', *pe))
        for a, (o, n) in r['mem'].items():
            if 0x9ee <= a < 0x9f2: tr[a - 0x9ee] = n
        runs.append(dict(status=r['status'], row=row.hex(), trk=list(struct.unpack('>HH', tr))))
    json.dump(dict(snapshot=str(ANCHOR), setup=[dict(s, mem={'%x' % a: v for a, v in s['mem'].items()}) for s in setup],
                   runs=runs, njobs=len(jobs)), open(CACHE, 'w'))

if '--emu' in _sys.argv or not CACHE.exists():
    run_emulator()
E = json.load(open(CACHE))
assert E['njobs'] == len(jobs), 'span_emu.json is from a different job list: re-run with --emu'
SETUP = [dict(s, mem={int(a, 16): v for a, v in s['mem'].items()}) for s in E['setup']]
RUNS = [dict(r, row=bytes.fromhex(r['row'])) for r in E['runs']]

# ---- checks -------------------------------------------------------------------------------------
patch_ok = 0
for c in range(64):
    d, a0, a5 = derive(c)
    m = SETUP[c]['mem']
    exp = {a: d.get(a, RAM[a]) for a in m}
    ok = exp == m and (c >= 16 or (SETUP[c]['A0'], SETUP[c]['A5']) == (a0, a5))
    patch_ok += ok
emu_ok = trk_ok = 0
vstats = {}
for j, r in zip(jobs, RUNS):
    tag, c, xl, xr, y, pe, bg = j
    row, trk = model(bg, c, xl, xr, y, pe)
    good = r['status'] == 'returned' and bytes(row) == r['row']
    emu_ok += good; trk_ok += tuple(r['trk']) == tuple(trk)
    vstats.setdefault(tag, [0, 0]); vstats[tag][0] += good; vstats[tag][1] += 1
nV = vstats['V'][1]
print('viewport: x offset %d, width %d (block at $%x = A3); screen rows from $%x' % (VX, VW, VP, ROWBASE))
print('pairs: codes 0..15 solid, %d dithers; patch bytes from callcap $494c equal the table derivation: %d/64'
      % (sum(a != b for a, b in PAIRS), patch_ok))
print('filler rows equal to span_gate model: %d/%d; $9ee/$9f0 after the call: %d/%d; by panel %s'
      % (emu_ok, len(jobs), trk_ok, len(jobs), {k: '%d/%d' % tuple(v) for k, v in vstats.items()}))
print('palette (shifter, c_s30.snap):', ['%03x' % p for p in PAL])

def pixels(row, x0, n):
    out = []
    for x in range(x0, x0 + n):
        base = (x >> 4) * 8; b = 15 - (x & 15)
        out.append(sum(((struct.unpack_from('>H', row, base + 2 * p)[0] >> b) & 1) << p for p in range(4)))
    return out
def words(row, grp):
    return [struct.unpack_from('>H', row, grp * 8 + 2 * p)[0] for p in range(4)]
def run_of(tag, c=None, y=None):
    return [r for j, r in zip(jobs, RUNS) if j[0] == tag and (c is None or j[1] == c) and (y is None or j[4] == y)]

# ---- svg ----------------------------------------------------------------------------------------
from igtext import para, height
W = 900
s = []
a = s.append
NOTE = '#f6f8fa'

def caption(x, y, w, read, take):
    y = para(a, '**How to read.** ' + read, x, y, w, size=11.5, color='#1f2328')
    return para(a, '**Takeaway.** ' + take, x, y + 4, w, size=11.5, color='#1f2328')

def caption_h(w, read, take):
    return height('**How to read.** ' + read, w, 11.5) + 4 + height('**Takeaway.** ' + take, w, 11.5)

c1, c2 = PAIRS[EX_C]
LEAD = ('Carrier Command (Realtime Games, 1988) is a real-time strategy and vehicle game drawn in filled-polygon '
        '3D on an 8 MHz 68000 with no blitter. Every polygon is painted one horizontal line (a span) at a time by '
        'routine $4678, the most-called routine in the game (2079 calls per 1.2 million emulated instructions). '
        'A general-purpose filler would have to decide, for every word it writes, whether to set or clear each '
        'colour bit. This one does not: before each polygon, routine $494c rewrites the filler\'s own '
        'instructions and constants for that colour (self-modifying code), so the inner loop only writes. It '
        'covers 16 solid colours and 48 two-colour checkerboard dithers this way, and it also stretches each '
        'span so that steep edges leave no gaps.')
A_READ = ('The Atari ST\'s 16-colour low-resolution screen stores pixels in bitplanes: each group of 16 pixels is '
          'four consecutive 16-bit words, one per plane, and a pixel\'s colour number takes one bit from each '
          'word (bit p from plane p; bit 15 is the leftmost pixel). Top strip: real output of $4678 drawing '
          'colour 9 (%1001, so planes 0 and 3) over a row of colour 6 (%0110); the black outline is the span, '
          'screen x 37 to 74. Below it: the four plane words of each 16-pixel group, black for a 1 bit, with '
          'the word in hex.')
A_TAKE = ('Colouring a span means setting its bits in some planes and clearing them in others. Groups wholly '
          'inside the span are plain stores of two longwords (A0, A5); only the two edge groups need a mask '
          'that keeps the pixels outside the span, and that is where the patched instructions sit.')
B_READ = ('One row per solid colour: the colour, its index in binary, the four opcodes the patcher writes into '
          'both edge routines (one per plane, plane 0 first), and the A0 and A5 values the middle stores. Blue '
          '8D5C is an "or" that sets the span\'s bits in that plane; grey C75C is an "and" that clears them.')
B_TAKE = ('Read the opcode column as the colour\'s bits from plane 0 up: the table at $49e4 is just the 16 '
          'precomputed answers. The filler never decides anything per pixel or per word.')
C_READ = (f'Worked example, code {EX_C}: colours {c1} and {c2} alternate pixel by pixel, and the next row is '
          f'shifted by one, which makes a checkerboard. The four constants are what $494c patches into the '
          f'dither loop for this code. The strip is six rows of real output, each labelled with the constant '
          f'pair it used. Below: all 48 dithers, each a small tile of real output.')
C_TAKE = ('Even the choice of loop is patched. The branch at $46c0 becomes bvs (never taken) for a solid colour '
          'or bvc (always taken) for a dither, because the add before it cannot overflow, so the choice costs '
          'nothing per span. The phase comes from the screen row, so the pattern is fixed to the screen, not '
          'to the polygon (from code).')
D_READ = (f'Two thin slanted polygons in colour {DCOL}, eight rows each, magnified so one square is one pixel. '
          f'The outlined dark green squares are the span the edge walk computed for each row; pale green squares '
          f'are the pixels the widening added. Each row was drawn by the game\'s own filler in the emulator, '
          f'with the stored ends of the previous row set first.')
D_TAKE = ('A steep edge moves several pixels per row, so successive spans need not touch. Two comparisons per '
          'row stretch each span back to the previous row\'s far end, and the sliver stays connected. The rule '
          'is proven; that its purpose is closing gaps is inferred.')
KNOW = (f'**How we know.** **Proven** means observed in an emulator running the game\'s own code, with a count of '
        f'matches (N/N = matches out of cases). Every pixel and patched byte on this page is emulator output, by '
        f'callcap: the emulator restores a saved game state (c_s30, a Strategy game in progress), calls one '
        f'routine with chosen inputs and records the result. $494c was called for all 64 colour codes, and the '
        f'bytes it patched equal what the tables at $49e4, $4ae4 and $4b64 predict ({patch_ok}/64). $4678 was '
        f'called on {len(jobs)} rows, and {emu_ok}/{len(jobs)} equal span_gate.py\'s Python model, including '
        f'{nV} rows on a random background (64 codes x 8 spans x 2 phases x 2 previous spans). As a control, a '
        f'model with the dither phase flipped and the widening dropped matches only 531/{len(jobs)}, so the '
        f'check can tell the difference. Colours are the palette loaded in the snapshot. $hex numbers are '
        f'addresses in the game\'s memory, given as citations.')
lead_h = height(LEAD, 852, 13)
INK, MUTE, ACC, BAD, GRID = '#1f2328', '#656d76', '#0969da', '#cf222e', '#d0d7de'
a('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 __H__" width="900" height="__H__" role="img" aria-labelledby="t d">')
a('<title id="t">A filler that rewrites itself per colour</title>')
a('<desc id="d">Carrier Command (1988) fills every polygon scanline with $4678, whose opcodes and immediates '
  '$494c patches for each of 16 solid colours and 48 checkerboard dithers; each span is widened to touch the '
  'previous one. Source: reversing/carriercommand/render.md section 5 and py/render/span_gate.py; bytes read '
  'from c_s30.snap and callcap $494c, pixels from callcap $4678, by py/infographics/gen_span.py. '
  'Facts: span.facts.md.</desc>')
a('<style>text{font-family:Helvetica,Arial,sans-serif;fill:%s;font-size:12px}.t{font-size:20px;font-weight:bold}'
  '.h{font-size:14px;font-weight:bold}.m{fill:%s}.c{font-family:Menlo,monospace;font-size:11.5px}'
  '.cs{font-family:Menlo,monospace;font-size:10.5px}'
  '.s{font-size:11px;fill:%s}</style>' % (INK, MUTE, MUTE))
a('<rect width="900" height="__H__" fill="#ffffff"/>')
a('<text x="24" y="38" class="t">A filler that rewrites itself per colour</text>')
para(a, LEAD, 24, 64, 852, size=13, color=INK)

def panel(x, y, w, h, title):
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="none" stroke="{GRID}"/>')
    a(f'<text x="{x+14}" y="{y+24}" class="h">{title}</text>')
def cell(x, y, w, h, fill, stroke=None):
    st = f' stroke="{stroke}" stroke-width="0.6"' if stroke else ''
    a(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}"{st}/>')

# A: bitplanes ----------------------------------------------------------------------------------
PA = int(64 + lead_h + 2)
hA = 344 + caption_h(820, A_READ, A_TAKE) - 2
panel(24, PA, 852, hA, 'A. Low resolution is four interleaved bitplanes: a colour is one bit in each of four words')
a(f'<text x="38" y="{PA+44}" class="s">16 pixels share four consecutive words, planes 0 to 3; bit 15 is the leftmost pixel. Bit p of the colour index is the pixel\'s bit in plane p,</text>')
a(f'<text x="38" y="{PA+58}" class="s">so colour 9 = %1001 sets planes 0 and 3. Below, $4678 draws colour 9 from screen x 37 to 74 over a row of colour 6 = %0110 (emulator output).</text>')
rowA = run_of('A')[0]['row']
G0 = 2                                               # word groups 2..4 = screen x 32..79
ax0, pw = 128, 15
pyA = PA + 96
pix = pixels(rowA, 16 * G0, 48)
for i, v in enumerate(pix):
    cell(ax0 + i * pw, pyA, pw, 24, rgb(v), '#ffffff')
a(f'<text x="{ax0-10}" y="{pyA+16}" text-anchor="end" class="s">pixels</text>')
for g in range(3):
    gx = ax0 + 16 * pw * g
    a(f'<text x="{gx}" y="{pyA-6}" class="s">x {16*(G0+g)}..{16*(G0+g)+15}</text>')
    a(f'<line x1="{gx}" y1="{pyA-2}" x2="{gx}" y2="{pyA+176}" stroke="{INK}" stroke-width="1"/>')
a(f'<line x1="{ax0+48*pw}" y1="{pyA-2}" x2="{ax0+48*pw}" y2="{pyA+176}" stroke="{INK}" stroke-width="1"/>')
xs, xe = 37 - 16 * G0, 74 - 16 * G0
a(f'<rect x="{ax0+xs*pw}" y="{pyA-1}" width="{(xe-xs+1)*pw}" height="26" fill="none" stroke="{INK}" stroke-width="1.6"/>')
for p in range(4):
    py = pyA + 34 + p * 36
    a(f'<text x="{ax0-10}" y="{py+10}" text-anchor="end" class="s">plane {p}</text>')
    for g in range(3):
        wv = words(rowA, G0 + g)[p]
        for b in range(16):
            on = (wv >> (15 - b)) & 1
            cell(ax0 + (16 * g + b) * pw + 1, py, pw - 2, 12, INK if on else '#eef1f4')
        a(f'<text x="{ax0 + 16*pw*g + 8*pw}" y="{py+26}" text-anchor="middle" class="cs">${wv:04x}</text>')
# instruction notes under each group
lm, rm = LMASK[37 & 15], RMASK[74 & 15]
notes = [
    ('left edge: $46e8..$46ef', f'keep mask $4658[5] = ${lm:04x}', 'or.w D6 / and.w D3, one per plane'),
    ('middle: unrolled loop', 'move.l A0,(A4)+  planes 0-1', 'move.l A5,(A4)+  planes 2-3'),
    ('right edge: $4758..$475f', f'keep mask $476c[10] = ${rm:04x}', 'the same four patched opcodes'),
]
for g, (l1, l2, l3) in enumerate(notes):
    gx = ax0 + 16 * pw * g + 6
    a(f'<text x="{gx}" y="{pyA+194}" class="s" style="fill:{INK};font-weight:bold">{l1}</text>')
    a(f'<text x="{gx}" y="{pyA+208}" class="cs">{l2}</text>')
    a(f'<text x="{gx}" y="{pyA+222}" class="cs">{l3}</text>')

caption(38, PA + 344, 820, A_READ, A_TAKE)
# B: solid colours ------------------------------------------------------------------------------
PB = PA + hA + 14
c1, c2 = PAIRS[EX_C]
hBC = max(456 + caption_h(392, B_READ, B_TAKE), 384 + caption_h(392, C_READ, C_TAKE)) - 2
panel(24, PB, 420, hBC, 'B. 16 solid colours: four patched opcodes each')
a(f'<text x="38" y="{PB+44}" class="s">$494c writes $69 (bvs) to $46c0, then copies one 16-byte entry</text>')
a(f'<text x="38" y="{PB+58}" class="s">of the table at $49e4: four opcodes to both edges, A0 and A5.</text>')
hx = [38, 66, 124, 284, 350]
hy = PB + 84
for x, t in zip(hx, ['', 'colour', 'opcodes at $46e8 and $4758', 'A0', 'A5']):
    a(f'<text x="{x}" y="{hy}" class="s" style="font-weight:bold">{t}</text>')
for c in range(16):
    y = hy + 10 + c * 17
    m = SETUP[c]['mem']
    ops = [(m[0x46e8 + 2 * k] << 8) | m[0x46e9 + 2 * k] for k in range(4)]
    cell(38, y + 1, 20, 13, rgb(c), GRID)
    a(f'<text x="66" y="{y+12}" class="cs">{c:2d} %{c:04b}</text>')
    for k, op in enumerate(ops):
        col = ACC if op == 0x8d5c else MUTE
        a(f'<text x="{124 + 40*k}" y="{y+12}" class="cs" style="fill:{col}">{op:04X}</text>')
    a(f'<text x="284" y="{y+12}" class="cs">{SETUP[c]["A0"]:08x}</text>')
    a(f'<text x="350" y="{y+12}" class="cs">{SETUP[c]["A5"]:08x}</text>')
ly = hy + 10 + 16 * 17 + 18
a(f'<text x="38" y="{ly}" class="cs"><tspan style="fill:{ACC}">8D5C</tspan> or.w D6,(A4)+   set the span\'s bits in that plane</text>')
a(f'<text x="38" y="{ly+15}" class="cs"><tspan style="fill:{MUTE}">C75C</tspan> and.w D3,(A4)+  clear them</text>')
a(f'<text x="38" y="{ly+34}" class="s">Opcode k serves plane k, so the opcode column reads the colour\'s</text>')
a(f'<text x="38" y="{ly+48}" class="s">bits from plane 0. The four words reach planes 0 to 3 by (A4)+.</text>')

# C: dithers ------------------------------------------------------------------------------------
caption(38, PB + 456, 392, B_READ, B_TAKE)
PC = PB
panel(456, PC, 420, hBC, 'C. 48 dithers: patched immediates, phase per row')
c1, c2 = PAIRS[EX_C]
m = SETUP[EX_C]['mem']
L = lambda addr: (m[addr] << 24) | (m[addr+1] << 16) | (m[addr+2] << 8) | m[addr+3]
a(f'<text x="470" y="{PC+44}" class="s">$494c writes $68 (bvc) to $46c0. The filler\'s add.w (A3),D3 never</text>')
a(f'<text x="470" y="{PC+58}" class="s">overflows, so bvc always jumps to the dither loop and bvs never does.</text>')
a(f'<text x="470" y="{PC+78}" class="s">Code {EX_C} = colours {c1} and {c2} (byte pair at $1544 + 2 x {EX_C}). The</text>')
a(f'<text x="470" y="{PC+92}" class="s">immediates are $5555 rows of colour {c1} plus $aaaa rows of colour {c2}:</text>')
iy = PC + 112
a(f'<text x="470" y="{iy}" class="cs">$47b4 A0 = ${L(0x47b4):08x}  $47ba A5 = ${L(0x47ba):08x}</text>')
a(f'<text x="470" y="{iy+15}" class="cs">$47c2 A0 = ${L(0x47c2):08x}  $47c8 A5 = ${L(0x47c8):08x}</text>')
a(f'<text x="470" y="{iy+30}" class="s">the second pair is the first with each word rotated right one bit</text>')
gy = iy + 46
cw = 9
rowsC = [(60 + k, run_of('C', y=60 + k)[0]['row']) for k in range(6)]
NC = 24
for k, (y, row) in enumerate(rowsC):
    px = pixels(row, VX, NC)
    for i, v in enumerate(px):
        cell(470 + i * cw, gy + k * cw, cw, cw, rgb(v))
    odd = (y + 1) & 1
    a(f'<text x="{470 + NC*cw + 10}" y="{gy + k*cw + 8}" class="cs" style="font-size:9.5px">row {y}: {"$47b4/$47ba" if odd else "$47c2/$47c8"}</text>')
a(f'<text x="470" y="{gy + 6*cw + 16}" class="s">btst #0 of D7\'s high word (the row, plus one) picks the pair, so</text>')
a(f'<text x="470" y="{gy + 6*cw + 30}" class="s">the checkerboard is fixed to screen x and y (rows from $4678).</text>')
ty = gy + 6 * cw + 46
a(f'<text x="470" y="{ty}" class="s" style="font-weight:bold">All 48 dither pairs at $1544, codes 16 to 63</text>')
for i, c in enumerate(range(16, 64)):
    tx = 470 + (i % 12) * 33; tyy = ty + 8 + (i // 12) * 25
    # draw the 8x2 emulator rows as a 4x4 tile of 7 px cells (rows repeat with period 2)
    rows2 = [pixels(run_of('T', c=c, y=70 + k)[0]['row'], VX, 4) for k in range(2)]
    for rr in range(3):
        for q in range(4):
            cell(tx + q * 7, tyy + rr * 7, 7, 7, rgb(rows2[rr % 2][q]))
    a(f'<rect x="{tx}" y="{tyy}" width="28" height="21" fill="none" stroke="{GRID}" stroke-width="0.6"/>')

# D: span overlap -------------------------------------------------------------------------------
caption(470, PC + 384, 392, C_READ, C_TAKE)
PD = PB + hBC + 14
hD = 262 + caption_h(820, D_READ, D_TAKE) - 2
panel(24, PD, 852, hD, 'D. Each span is widened to touch the previous one')
dc = 10
dx0, dy0 = 40, PD + 54
NX = 64
a(f'<rect x="{dx0}" y="{dy0}" width="{NX*dc}" height="{8*dc}" fill="#f6f8fa"/>')
for si, chain in enumerate(D_CHAINS):
    for y, (xl, xr, pe, trk) in enumerate(chain):
        row = run_of('D', y=80 + 10 * si + y)[0]['row']
        px = pixels(row, VX, NX)
        for x, v in enumerate(px):
            if v:
                raw = xl <= x <= xr
                cell(dx0 + x * dc, dy0 + y * dc, dc, dc, rgb(DCOL) if raw else '#9be9a8')
        a(f'<rect x="{dx0+xl*dc}" y="{dy0+y*dc}" width="{(xr-xl+1)*dc}" height="{dc}" fill="none" stroke="{INK}" stroke-width="1.2"/>')
for x in range(0, NX + 1, 8):
    a(f'<text x="{dx0 + x*dc}" y="{dy0 + 8*dc + 14}" text-anchor="middle" class="s">{x}</text>')
a(f'<text x="{dx0 + NX*dc/2}" y="{dy0 + 8*dc + 28}" text-anchor="middle" class="s">span x (screen x - {VX}); eight rows, two separate polygons in colour {DCOL}</text>')
lx = dx0
lyD = dy0 + 8 * dc + 50
cell(lx, lyD - 9, 10, 10, rgb(DCOL)); a(f'<text x="{lx+16}" y="{lyD}" class="s">the span the edge walk gives (outlined)</text>')
cell(lx + 250, lyD - 9, 10, 10, '#9be9a8'); a(f'<text x="{lx+266}" y="{lyD}" class="s">pixels added by the widening</text>')
a(f'<text x="{lx}" y="{lyD+22}" class="s">Without the widening these rows, stepping 3 and 4 pixels a row, would not touch even at a corner;</text>')
a(f'<text x="{lx}" y="{lyD+36}" class="s">with it each row reaches back to the previous row\'s far end. That this is to close gaps is inferred.</text>')
a(f'<text x="{lx}" y="{lyD+56}" class="s">Each row: callcap $4678 with $9ee/$9f0 set to the previous row\'s result; {vstats["D"][0]}/{vstats["D"][1]} rows match the model.</text>')
rx = 708
rules = [('h', 'The rule ($4680..$4698)'), ('c', "xr' = max(xr, prev xl')"), ('c', "xl' = min(xl, prev xr')"),
         ('s', "$9ee := xr'   $9f0 := xl'"), ('s', 'then clamp to the 256-pixel'), ('s', f'viewport and add {VX}'),
         ('s', ''), ('s', '$494c starts each polygon'), ('s', 'with $9ee = $7fff, $9f0 = $8001,'),
         ('s', 'so the first row is unchanged.'), ('s', ''), ('s', 'span_gate.py: 780/780 rows,'),
         ('s', '0 tracker mismatches.')]
ry = dy0 + 6
for kind, t in rules:
    if kind == 'h': a(f'<text x="{rx}" y="{ry}" class="s" style="fill:{INK};font-weight:bold">{t}</text>')
    elif kind == 'c': a(f'<text x="{rx}" y="{ry}" class="cs">{t}</text>')
    elif t: a(f'<text x="{rx}" y="{ry}" class="s">{t}</text>')
    ry += 15

caption(38, PD + 262, 820, D_READ, D_TAKE)
KY = PD + hD + 14
kh = height(KNOW, 820, 11.5)
a(f'<rect x="24" y="{KY:.1f}" width="852" height="{kh+16:.1f}" rx="6" fill="{NOTE}" stroke="{GRID}"/>')
para(a, KNOW, 38, KY + 20, 820, size=11.5, color=INK)
H = int(KY + kh + 30)
a('</svg>')
(OUT / 'span.svg').write_text('\n'.join(s).replace('__H__', str(H)))
print('wrote', OUT / 'span.svg')
