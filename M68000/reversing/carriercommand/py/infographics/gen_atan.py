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
W, H = 900, 962
s = []
a = s.append
INK, MUTE, ACC, BAD, GRID = '#1f2328', '#656d76', '#0969da', '#cf222e', '#d0d7de'
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
a('<text x="24" y="60" class="m">Carrier Command (Realtime Games, 1988), routine $aae6: the heading from one vector to another, '
  'for the autopilot, missiles and about twenty other callers.</text>')

def panel(x, y, w, h, title):
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="none" stroke="{GRID}"/>')
    a(f'<text x="{x+14}" y="{y+24}" class="h">{title}</text>')

# A: the method --------------------------------------------------------------------------------
panel(24, 80, 420, 400, 'A. Fold, divide, look up, unfold')
cx, cy, rad = 130, 260, 86
for i in range(8):
    ang = math.pi / 2 - i * math.pi / 4
    a(f'<line x1="{cx}" y1="{cy}" x2="{cx+rad*math.cos(ang):.1f}" y2="{cy-rad*math.sin(ang):.1f}" stroke="{GRID}"/>')
a(f'<circle cx="{cx}" cy="{cy}" r="{rad}" fill="none" stroke="{MUTE}"/>')
# octant 0 shaded: from +z (up) clockwise to 45 deg (dx>0 to the right)
p1 = (cx, cy - rad); p2 = (cx + rad * math.sin(math.pi / 4), cy - rad * math.cos(math.pi / 4))
a(f'<path d="M{cx},{cy} L{p1[0]:.1f},{p1[1]:.1f} A{rad},{rad} 0 0 1 {p2[0]:.1f},{p2[1]:.1f} Z" fill="{ACC}" fill-opacity="0.15"/>')
# a vector in octant 6 (dx<0, |dx|>|dz|, dz>0)... use dx=-70, dz=-30 (screen: left, down)
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
a(f'<text x="38" y="448" class="s">65536 units to the turn, 0 along +z. No polynomial and no</text>')
a(f'<text x="38" y="463" class="s">CORDIC: two divides and a table load.</text>')

# B: the table ---------------------------------------------------------------------------------
panel(456, 80, 420, 400, 'B. The 128 factors at $3864')
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
  f'<text x="{bx+42}" y="{by+34}" class="s">4096 pi r / atan(r) at each midpoint</text>')
a(f'<text x="470" y="448" class="s">Each factor is ratio over angle, so dividing r by it gives</text>')
a(f'<text x="470" y="463" class="s">the angle. The real curve is not stored, only 128 steps of it.</text>')

# C: the error ---------------------------------------------------------------------------------
panel(24, 494, 852, 252, 'C. Error over one octant, radius 30000 (the other seven repeat it)')
cx0, cy0, cw, ch = 96, 530, 750, 150
emax = 30
def CX(k): return cx0 + cw * k / 8192
def CY(e): return cy0 + ch / 2 - (ch / 2) * e / emax
for e in (-27, -16, 0, 16, 27):
    dash = '' if e == 0 else ' stroke-dasharray="3 3"'
    a(f'<line x1="{cx0}" y1="{CY(e):.1f}" x2="{cx0+cw}" y2="{CY(e):.1f}" stroke="{GRID}"{dash}/>')
    a(f'<text x="{cx0-8}" y="{CY(e)+4:.1f}" text-anchor="end" class="s">{e:+d}</text>')
a(f'<text x="40" y="{cy0+ch/2+4}" class="s" transform="rotate(-90 40 {cy0+ch/2})" text-anchor="middle">units</text>')
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

# D: the bug -----------------------------------------------------------------------------------
panel(24, 760, 852, 182, 'D. The bug: neg.w -32768 is -32768, so dx = -32768 pins the answer')
dx0, dy0, dw, dh = 96, 794, 520, 110
def DX(dz): return dx0 + dw * (dz + 32768) / 65535
def DY(deg): return dy0 + dh * (360 - deg) / 180
for deg in (180, 225, 270, 315, 360):
    a(f'<line x1="{dx0}" y1="{DY(deg):.1f}" x2="{dx0+dw}" y2="{DY(deg):.1f}" stroke="{GRID}" stroke-width="0.6"/>')
    a(f'<text x="{dx0-8}" y="{DY(deg)+4:.1f}" text-anchor="end" class="s">{deg}</text>')
for dz in (-32768, -16384, 0, 16384, 32767):
    a(f'<text x="{DX(dz):.1f}" y="{dy0+dh+16}" text-anchor="middle" class="s">{dz}</text>')
a(f'<text x="{dx0+dw/2}" y="{dy0+dh+30}" text-anchor="middle" class="s">dz, with dx = -32768 (degrees on the left)</text>')
tru = ' '.join(f'{DX(dz):.1f},{DY(exact(-32768, dz) % 65536 * U2D):.1f}' for dz in range(-32767, 32768, 256))
a(f'<polyline points="{tru}" fill="none" stroke="{MUTE}" stroke-width="1.6"/>')
neg = [p for p in bug if p[0] < 0]; pos = [p for p in bug if p[0] > 0]
for seg in (neg, pos):
    pts = ' '.join(f'{DX(dz):.1f},{DY(v*U2D):.1f}' for dz, v in seg)
    a(f'<polyline points="{pts}" fill="none" stroke="{BAD}" stroke-width="2.4"/>')
a(f'<circle cx="{DX(0):.1f}" cy="{DY(atan2(-32768,0)*U2D):.1f}" r="3.5" fill="{BAD}"/>')
tx = 640
a(f'<text x="{tx}" y="{dy0+6}" class="s"><tspan style="fill:{MUTE};font-weight:bold">grey</tspan>: the true angle</text>')
a(f'<text x="{tx}" y="{dy0+22}" class="s"><tspan style="fill:{BAD};font-weight:bold">red</tspan>: $aae6, stuck at $a000 / $e000</text>')
a(f'<text x="{tx}" y="{dy0+38}" class="s">and $8000 at dz = 0: up to 45 degrees</text>')
a(f'<text x="{tx}" y="{dy0+54}" class="s">off, 90 on the axis. dz = -32768 does</text>')
a(f'<text x="{tx}" y="{dy0+70}" class="s">the same ($6000, $a000, $c000).</text>')
a(f'<text x="{tx}" y="{dy0+92}" class="s">27 of the 529 grid cases, all</text>')
a(f'<text x="{tx}" y="{dy0+106}" class="s">matched in the emulator.</text>')
a('</svg>')
(OUT / 'atan.svg').write_text('\n'.join(s))
print('wrote', OUT / 'atan.svg')
