#!/usr/bin/env python3
"""Infographic: the arctangent $aae6 (vehicles.md section 2), drawn from the port atan_port.py.

usage: gen_atan.py [outdir]   (default WORK/infographics; writes atan.svg and prints the figures it draws)
Every curve is computed here from the port, which matched callcap $aae6 on all 529 cases of atan_grid.py;
the table is read from the anchor snapshot by the port. Facts and sources: atan.facts.md beside this script."""
import pathlib as _pl, sys as _sys
_here = _pl.Path(__file__).resolve().parent
_sys.path.insert(0, str(_here.parent)); _sys.path.insert(0, str(_here.parent / 'units'))
from ccpaths import *
import math
import atan_port as P
from atan_port import atan2

OUT = _pl.Path(_sys.argv[1]) if len(_sys.argv) > 1 else WORK / 'infographics'
OUT.mkdir(parents=True, exist_ok=True)
U2D = 360 / 65536
R = 30000

def exact(dx, dz):
    return math.atan2(dx, dz) / (2 * math.pi) * 65536

def wrap(e):
    return ((e + 32768) % 65536) - 32768

# ---- data ---------------------------------------------------------------------------------------
# error over the whole circle at radius R, per octant, rounded (the game) and unrounded (table only)
N = 65536
oct_max = [0.0] * 8
rounded, table_only = [], []          # octant 0 only, (angle units, error units)
for k in range(N):
    th = 2 * math.pi * k / N
    dx = round(R * math.sin(th)); dz = round(R * math.cos(th))
    e = wrap(atan2(dx, dz) - exact(dx, dz))
    o = k * 8 // N
    oct_max[o] = max(oct_max[o], abs(e))
    if k <= 8192 and dz > 0 and 0 <= dx < dz:
        r = int((dx << 15) / dz); t = r << 8; tv = P.TAN[t >> 16]
        table_only.append((k, 16 * t / tv - exact(dx, dz)))
        rounded.append((k, e))
worst = max(oct_max)
tab_worst = max(abs(e) for _, e in table_only)
mult16 = all(atan2(a, b) % 16 == 0 for a in range(-400, 400, 7) for b in range(-400, 400, 11) if (a, b) != (0, 0))

# the stored factors against 4096 pi r / atan(r) at each bin's midpoint
TAB = P.TAN[:128]
def fit(i):
    r = (i + 0.5) / 128
    return 4096 * math.pi * r / math.atan(r)
fit_dev = [TAB[i] - fit(i) for i in range(1, 128)]

# the -32768 bug: dx = -32768, dz swept
bug = [(dz, atan2(-32768, dz)) for dz in range(-32767, 32768, 64)] + [(0, atan2(-32768, 0))]
bug_vals = sorted(set(v for _, v in bug))

print('worst error at R=%d: %.1f units (%.3f deg); per octant %s' % (R, worst, worst * U2D, ['%.1f' % x for x in oct_max]))
print('table-only worst in octant 0: %.1f units (%.3f deg)' % (tab_worst, tab_worst * U2D))
print('results multiples of 16:', mult16)
print('table T[0..127]: %d .. %d; fit deviation (i>=1) %.1f .. %.1f' % (TAB[0], TAB[127], min(fit_dev), max(fit_dev)))
print('dx=-32768 results:', [hex(v) for v in bug_vals])

# ---- svg ----------------------------------------------------------------------------------------
from igtext import para, height
W = 900
s = []
a = s.append
INK, MUTE, ACC, BAD, GRID = '#1f2328', '#656d76', '#0969da', '#cf222e', '#d0d7de'
NOTE = '#f6f8fa'
U1 = U2D  # degrees per unit
tab_lo, tab_hi = TAB[0], TAB[127]

def panel(x, y, w, h, title):
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="none" stroke="{GRID}"/>')
    a(f'<text x="{x+14}" y="{y+24}" class="h">{title}</text>')

def caption(x, y, w, read, take):
    """'How to read' and 'Takeaway' paragraphs; returns the y after them."""
    y = para(a, '**How to read.** ' + read, x, y, w, size=11.5, color=INK)
    y += 4
    return para(a, '**Takeaway.** ' + take, x, y, w, size=11.5, color=INK)

def caption_h(w, read, take):
    return height('**How to read.** ' + read, w, 11.5) + 4 + height('**Takeaway.** ' + take, w, 11.5)

LEAD = ('Carrier Command (Realtime Games, 1988) is a real-time strategy and vehicle game: two aircraft carriers, '
        'one yours and one the computer\'s, fight over a 64-island archipelago in 3D. Whenever something '
        'has to point at something else (the carrier\'s autopilot, a guided missile, about twenty routines in all) '
        'the game needs the compass bearing of a vector (dx, dz), an arctangent. The 68000 has no floating point. '
        'Routine $aae6 gets the bearing from integers with two divides and one table of 128 numbers: fold the '
        'vector into a 45-degree wedge, divide the short side by the long side, then divide that ratio by a '
        'tabulated factor to turn it into an angle. '
        'Angles are in units of 1/65536 of a turn ($4000 = 90 degrees, $8000 = 180), 0 along +z.')

A_READ = ('The circle is the compass, cut into eight 45-degree octants. The black vector (dx, dz) can lie anywhere; '
          'negating and swapping its components moves it to the blue dashed vector in the shaded octant, where '
          '0 <= dx <= dz. Steps 1 to 6 are the routine in order. divs and divu are the 68000\'s signed and unsigned '
          'divide instructions; Q15 means a fraction held as an integer times 32768; T is the table in panel B.')
A_TAKE = ('Only the shaded octant is ever computed. Step 6 reflects the answer back to the original octant, '
          'which costs a subtraction or a negation. There is no polynomial and no CORDIC (the usual '
          'shift-and-add rotation method): two divides and a table load.')
B_READ = (f'Each blue dot is one stored 16-bit word of the table at $3864, plotted against its index i; entry i '
          f'serves every ratio r from i/128 to (i+1)/128. The grey line is 4096 pi r / atan(r) at the middle of '
          f'each entry\'s range. That formula is our fit to the stored numbers (inferred: the game does not '
          f'compute it); entries 1 to 127 lie within {min(fit_dev):.1f} / +{max(fit_dev):.1f} of it.')
B_TAKE = (f'Each factor is ratio divided by angle, so dividing the ratio by it gives the angle. The factor only '
          f'runs from {tab_lo} to {tab_hi} over the whole octant, so 128 steps of it are enough. The real '
          f'arctangent curve is never stored.')
C_READ = (f'We swept 65536 directions evenly round a circle of radius {R} and compared the routine with the '
          f'exact atan2. Across: the true angle inside one octant, 0 to 45 degrees. Up: the error in angle '
          f'units (1 unit = {U1:.4f} degrees). The black line is step 4 alone, before the shift of step 5; '
          f'the pale blue dots are what the game actually returns.')
C_TAKE = (f'The sawtooth comes from one table factor serving each 1/128 of the ratio range; it grows toward '
          f'45 degrees, where panel B\'s curve is steepest. Step 5 truncates to a multiple of 16, so the game '
          f'has 4096 headings to the turn ({16*U1:.3f} degrees each) and that truncation adds up to 16 units '
          f'below the table\'s {tab_worst:.1f}. Worst case: {worst:.0f} units, {worst*U1:.2f} degrees, the same '
          f'in all eight octants.')
D_READ = ('Across: dz over its whole signed 16-bit range, with dx held at -32768, the most negative 16-bit '
          'number. Up: the bearing in degrees. Grey is the true bearing; red is what $aae6 returns, and the '
          'red dot is its answer at dz = 0.')
D_TAKE = ('To fold, the routine makes negative inputs positive with the 68000\'s neg.w. In 16 bits +32768 does '
          'not exist, so neg.w leaves -32768 unchanged and the fold lands in the wrong octant. The answer is '
          'pinned to one value whatever dz is: up to 45 degrees wrong off the axis and 90 on it. dz = -32768 '
          'does the same ($6000, $a000, $c000). It is a real bug in the game, not in our port: 27 of the 529 '
          'test-grid cases hit it, and the emulator returned the same pinned values.')
KNOW = ('**How we know.** **Proven** here means observed in an emulator running the game\'s own code, with a '
        'count of matches. A Python port of $aae6 (py/units/atan_port.py) was checked against the real routine '
        'by callcap: the emulator restores a saved game state (snapshot c_s30, the Strategy game with the '
        'player\'s carrier at the island Vulcan), calls $aae6 with chosen inputs, and records what it returns. '
        'Over a 23 x 23 grid of inputs the port agreed in all 529 cases (529/529); the doc also reports the '
        'routine within 0.15 degrees of exact over 200,000 random inputs. Every curve on this page is then '
        'computed from the port, and the table is read from the same snapshot. The formula in panel B is '
        '**inferred**: it describes the numbers, the code does not contain it. $hex numbers are addresses in '
        'the game\'s memory, given as citations.')

# layout -------------------------------------------------------------------------------------------
LW = 852
lead_end = para(a, LEAD, 24, 66, LW, size=13, color=INK)       # measured first, emitted below in order
s.clear()
lead_y0 = 66
top = lead_end + 2                     # first panel row top
CW2 = 392                              # caption width in the half panels
cap_ab = max(caption_h(CW2, A_READ, A_TAKE), caption_h(CW2, B_READ, B_TAKE))
hAB = 446 - 80 + cap_ab - 2            # captions' first baseline at 446
dy1 = top - 80
topC = top + hAB + 14
cap_c = caption_h(820, C_READ, C_TAKE)
hC = 752 - 494 + cap_c - 2             # caption's first baseline at 752
dy2 = topC - 494
topD = topC + hC + 14
cap_d = caption_h(820, D_READ, D_TAKE)
hD = 954 - 760 + cap_d - 2             # caption's first baseline at 948
dy3 = topD - 760
topK = topD + hD + 14
know_h = height(KNOW, 820, 11.5)
H = int(topK + know_h + 30)

a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">')
a('<title id="t">An arctangent from one table</title>')
a('<desc id="d">Carrier Command (1988) computes atan2 at $aae6 by folding the vector into one octant, taking the '
  'ratio min/max and dividing it by one of 128 tabulated ratio-to-angle factors. Source: '
  'reversing/carriercommand/vehicles.md section 2; curves computed from py/units/atan_port.py by '
  'py/infographics/gen_atan.py. Facts: atan.facts.md.</desc>')
a('<style>text{font-family:Helvetica,Arial,sans-serif;fill:%s;font-size:12px}.t{font-size:20px;font-weight:bold}'
  '.h{font-size:14px;font-weight:bold}.m{fill:%s}.c{font-family:Menlo,monospace;font-size:11.5px}'
  '.s{font-size:11px;fill:%s}</style>' % (INK, MUTE, MUTE))
a(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
a('<text x="24" y="38" class="t">An arctangent from one table</text>')
para(a, LEAD, 24, lead_y0, LW, size=13, color=INK)

# A: the method --------------------------------------------------------------------------------
a(f'<g transform="translate(0,{dy1:.1f})">')
panel(24, 80, 420, hAB, 'A. Fold, divide, look up, unfold')
cx, cy, rad = 130, 260, 86
for i in range(8):
    ang = math.pi / 2 - i * math.pi / 4
    a(f'<line x1="{cx}" y1="{cy}" x2="{cx+rad*math.cos(ang):.1f}" y2="{cy-rad*math.sin(ang):.1f}" stroke="{GRID}"/>')
a(f'<circle cx="{cx}" cy="{cy}" r="{rad}" fill="none" stroke="{MUTE}"/>')
p1 = (cx, cy - rad); p2 = (cx + rad * math.sin(math.pi / 4), cy - rad * math.cos(math.pi / 4))
a(f'<path d="M{cx},{cy} L{p1[0]:.1f},{p1[1]:.1f} A{rad},{rad} 0 0 1 {p2[0]:.1f},{p2[1]:.1f} Z" fill="{ACC}" fill-opacity="0.15"/>')
vx, vz = -0.80, -0.42
a(f'<line x1="{cx}" y1="{cy}" x2="{cx+rad*vx:.1f}" y2="{cy-rad*vz:.1f}" stroke="{INK}" stroke-width="2.2"/>')
a(f'<circle cx="{cx+rad*vx:.1f}" cy="{cy-rad*vz:.1f}" r="3.5" fill="{INK}"/>')
fx, fz = abs(vz), abs(vx)
a(f'<line x1="{cx}" y1="{cy}" x2="{cx+rad*fx:.1f}" y2="{cy-rad*fz:.1f}" stroke="{ACC}" stroke-width="2.2" stroke-dasharray="5 3"/>')
a(f'<circle cx="{cx+rad*fx:.1f}" cy="{cy-rad*fz:.1f}" r="3.5" fill="{ACC}"/>')
a(f'<text x="{cx-6}" y="{cy-rad-8}" class="s">+z, 0</text>')
a(f'<text x="{cx+rad+6}" y="{cy+4}" class="s">+x</text>')
a(f'<text x="{cx-rad-30}" y="{cy-rad*vz+20:.0f}" class="s">(dx, dz)</text>')
a(f'<text x="{cx+rad*fx+6:.0f}" y="{cy-rad*fz-6:.0f}" class="s" style="fill:{ACC}">folded</text>')
a(f'<text x="{cx-rad+4}" y="{cy+rad+28}" class="s">signs and a swap put every</text>')
a(f'<text x="{cx-rad+4}" y="{cy+rad+42}" class="s">vector in the shaded 45 degrees</text>')
steps = [
    ('1', 'halve dx, dz', 'until both fit a signed word'),
    ('2', 'fold: negate, swap so', '0 &lt;= min &lt;= max'),
    ('3', 'r = (min &lt;&lt; 15) / max', 'one divs, Q15, 0 .. 1'),
    ('4', 'a = (r &lt;&lt; 8) / T[r &gt;&gt; 8]', 'one divu, 128-entry table'),
    ('5', 'a &lt;&lt;= 4', 'octant angle, 0 .. $2000'),
    ('6', 'unfold', '$4000 - a, $8000 - a, neg: undo 2'),
]
y = 128
for n, l1, l2 in steps:
    a(f'<circle cx="258" cy="{y-4}" r="9" fill="{ACC}"/><text x="254.5" y="{y}" style="fill:#fff;font-size:11px;font-weight:bold">{n}</text>')
    a(f'<text x="274" y="{y}" class="c">{l1}</text><text x="274" y="{y+15}" class="s">{l2}</text>')
    y += 50
caption(38, 446, CW2, A_READ, A_TAKE)

# B: the table ---------------------------------------------------------------------------------
panel(456, 80, 420, hAB, 'B. The 128 factors at $3864')
bx, by, bw, bh = 516, 120, 330, 262
lo, hi = 12800, 16400
def BX(i): return bx + bw * i / 127
def BY(v): return by + bh * (hi - v) / (hi - lo)
for v in range(13000, 16401, 1000):
    a(f'<line x1="{bx}" y1="{BY(v):.1f}" x2="{bx+bw}" y2="{BY(v):.1f}" stroke="{GRID}" stroke-width="0.6"/>')
    a(f'<text x="{bx-8}" y="{BY(v)+4:.1f}" text-anchor="end" class="s">{v}</text>')
for i in (0, 32, 64, 96, 127):
    a(f'<text x="{BX(i):.1f}" y="{by+bh+16}" text-anchor="middle" class="s">{i}</text>')
a(f'<text x="{bx+bw/2}" y="{by+bh+34}" text-anchor="middle" class="s">entry i, used for r from i/128 to (i+1)/128</text>')
pts = ' '.join(f'{BX(i):.1f},{BY(fit(i)):.1f}' for i in range(0, 128))
a(f'<polyline points="{pts}" fill="none" stroke="{MUTE}" stroke-width="1.4"/>')
for i in range(128):
    a(f'<circle cx="{BX(i):.1f}" cy="{BY(TAB[i]):.1f}" r="1.9" fill="{ACC}"/>')
a(f'<circle cx="{bx+34}" cy="{by+12}" r="3" fill="{ACC}"/><text x="{bx+42}" y="{by+16}" class="s">stored value</text>')
a(f'<line x1="{bx+28}" y1="{by+30}" x2="{bx+40}" y2="{by+30}" stroke="{MUTE}" stroke-width="1.4"/>'
  f'<text x="{bx+42}" y="{by+34}" class="s">4096 pi r / atan(r) at each midpoint (fit)</text>')
a(f'<text x="{bx-44}" y="{by+bh/2}" class="s" transform="rotate(-90 {bx-44} {by+bh/2})" text-anchor="middle">stored factor</text>')
caption(470, 446, CW2, B_READ, B_TAKE)
a('</g>')

# C: the error ---------------------------------------------------------------------------------
a(f'<g transform="translate(0,{dy2:.1f})">')
panel(24, 494, 852, hC, 'C. Error over one octant, radius 30000 (the other seven repeat it)')
cx0, cy0, cw, ch = 96, 530, 750, 150
emax = 30
def CX(k): return cx0 + cw * k / 8192
def CY(e): return cy0 + ch / 2 - (ch / 2) * e / emax
for e in (-27, -16, 0, 16, 27):
    dash = '' if e == 0 else ' stroke-dasharray="3 3"'
    a(f'<line x1="{cx0}" y1="{CY(e):.1f}" x2="{cx0+cw}" y2="{CY(e):.1f}" stroke="{GRID}"{dash}/>')
    a(f'<text x="{cx0-8}" y="{CY(e)+4:.1f}" text-anchor="end" class="s">{e:+d}</text>')
a(f'<text x="40" y="{cy0+ch/2+4}" class="s" transform="rotate(-90 40 {cy0+ch/2})" text-anchor="middle">error, units</text>')
for deg in range(0, 46, 5):
    k = deg / 360 * 65536
    a(f'<text x="{CX(k):.1f}" y="{cy0+ch+16}" text-anchor="middle" class="s">{deg}</text>')
a(f'<text x="{cx0+cw/2}" y="{cy0+ch+32}" text-anchor="middle" class="s">true angle, degrees</text>')
step = max(1, len(rounded) // 1500)
for k, e in rounded[::step]:
    a(f'<circle cx="{CX(k):.1f}" cy="{CY(e):.1f}" r="1.1" fill="{ACC}" fill-opacity="0.35"/>')
pts = ' '.join(f'{CX(k):.1f},{CY(e):.1f}' for k, e in table_only[::max(1, len(table_only)//1200)])
a(f'<polyline points="{pts}" fill="none" stroke="{INK}" stroke-width="1.1"/>')
a(f'<text x="{cx0+cw-4}" y="{CY(27)-5:.1f}" text-anchor="end" class="s">worst {worst:.0f} units = {worst*U2D:.2f} degrees</text>')
a(f'<line x1="{cx0+8}" y1="{cy0+ch+46}" x2="{cx0+22}" y2="{cy0+ch+46}" stroke="{INK}"/>'
  f'<text x="{cx0+28}" y="{cy0+ch+50}" class="s">table alone, before the final shift: at most {tab_worst:.1f} units</text>')
a(f'<circle cx="{cx0+380}" cy="{cy0+ch+46}" r="2" fill="{ACC}"/>'
  f'<text x="{cx0+388}" y="{cy0+ch+50}" class="s">what the game returns: truncated to a multiple of 16, so up to 16 lower</text>')
caption(38, 752, 820, C_READ, C_TAKE)
a('</g>')

# D: the bug -----------------------------------------------------------------------------------
a(f'<g transform="translate(0,{dy3:.1f})">')
panel(24, 760, 852, hD, 'D. The bug: neg.w -32768 is -32768, so dx = -32768 pins the answer')
dx0, dy0, dw, dh = 96, 794, 520, 110
def DX(dz): return dx0 + dw * (dz + 32768) / 65535
def DY(deg): return dy0 + dh * (360 - deg) / 180
for deg in (180, 225, 270, 315, 360):
    a(f'<line x1="{dx0}" y1="{DY(deg):.1f}" x2="{dx0+dw}" y2="{DY(deg):.1f}" stroke="{GRID}" stroke-width="0.6"/>')
    a(f'<text x="{dx0-8}" y="{DY(deg)+4:.1f}" text-anchor="end" class="s">{deg}</text>')
for dz in (-32768, -16384, 0, 16384, 32767):
    a(f'<text x="{DX(dz):.1f}" y="{dy0+dh+16}" text-anchor="middle" class="s">{dz}</text>')
a(f'<text x="{dx0+dw/2}" y="{dy0+dh+30}" text-anchor="middle" class="s">dz, with dx = -32768 (bearing in degrees on the left)</text>')
tru = ' '.join(f'{DX(dz):.1f},{DY(exact(-32768, dz) % 65536 * U2D):.1f}' for dz in range(-32767, 32768, 256))
a(f'<polyline points="{tru}" fill="none" stroke="{MUTE}" stroke-width="1.6"/>')
neg = [p for p in bug if p[0] < 0]; pos = [p for p in bug if p[0] > 0]
for seg in (neg, pos):
    pts = ' '.join(f'{DX(dz):.1f},{DY(v*U2D):.1f}' for dz, v in seg)
    a(f'<polyline points="{pts}" fill="none" stroke="{BAD}" stroke-width="2.4"/>')
a(f'<circle cx="{DX(0):.1f}" cy="{DY(atan2(-32768,0)*U2D):.1f}" r="3.5" fill="{BAD}"/>')
tx = 640
a(f'<text x="{tx}" y="{dy0+6}" class="s"><tspan style="fill:{MUTE};font-weight:bold">grey</tspan>: the true bearing</text>')
a(f'<text x="{tx}" y="{dy0+22}" class="s"><tspan style="fill:{BAD};font-weight:bold">red</tspan>: $aae6, stuck at $a000 (225)</text>')
a(f'<text x="{tx}" y="{dy0+38}" class="s">for dz &lt; 0, $e000 (315) for dz &gt; 0</text>')
a(f'<text x="{tx}" y="{dy0+54}" class="s">and $8000 (180) at dz = 0.</text>')
a(f'<text x="{tx}" y="{dy0+76}" class="s">27 of the 529 grid cases, all</text>')
a(f'<text x="{tx}" y="{dy0+90}" class="s">matched in the emulator.</text>')
caption(38, 954, 820, D_READ, D_TAKE)
a('</g>')

# how we know ----------------------------------------------------------------------------------
a(f'<rect x="24" y="{topK:.1f}" width="852" height="{know_h+16:.1f}" rx="6" fill="{NOTE}" stroke="{GRID}"/>')
para(a, KNOW, 38, topK + 20, 820, size=11.5, color=INK)
a('</svg>')
(OUT / 'atan.svg').write_text('\n'.join(s))
print('wrote', OUT / 'atan.svg', 'height', H)
