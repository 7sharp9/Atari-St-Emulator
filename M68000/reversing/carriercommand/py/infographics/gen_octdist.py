#!/usr/bin/env python3
"""Infographic: the octagonal distance max + min/2 and the enemy carrier's next-island score $2337a (ai.md section 2).

usage: gen_octdist.py [outdir]   (default WORK/infographics; writes octdist.svg and prints the figures it draws)
The distance is computed here with the game's integer formula (inlined at $233d2..$233ea, $23402..$23422,
$234b6..$234d6 and $1ad14..$1ad2c). The heat map is py/ai/score.py run on ai/nat/d1.snap, a snapshot taken at the
return of $2337a; score.py reproduces all 64 score words and the target there (gate_score.py: 1344/1344, 21/21).
The Euclidean column is a counterfactual computed here, not game behaviour. Facts and sources: octdist.facts.md."""
import pathlib as _pl, sys as _sys
_here = _pl.Path(__file__).resolve().parent
_sys.path.insert(0, str(_here.parent)); _sys.path.insert(0, str(_here.parent / 'ai'))
from ccpaths import *
import math, struct

OUT = _pl.Path(_sys.argv[1]) if len(_sys.argv) > 1 else WORK / 'infographics'
OUT.mkdir(parents=True, exist_ok=True)

def octd(dx, dy):                       # $233d2: abs, abs, cmp.l / bcs / exg, asr.l #1, add.l
    a, b = abs(dx), abs(dy)
    mx, mn = (a, b) if b < a else (b, a)
    return mx + (mn >> 1)

# ---- the error over angle, integer formula at the cutoff radius ---------------------------------
R = 3000000                              # the score's cutoff, cmp.l #$2dc6c0 at $233f0
N = 90000                                # 0.001-degree steps over one quadrant
err = []
for k in range(N + 1):
    th = math.radians(90 * k / N)
    dx = round(R * math.cos(th)); dy = round(R * math.sin(th))
    err.append((90 * k / N, octd(dx, dy) / math.hypot(dx, dy) - 1))
emax_deg, emax = max(err, key=lambda p: p[1])
emin = min(e for _, e in err)
e45 = [e for d, e in err if abs(d - 45) < 1e-9][0]
emean = sum(e for _, e in err[:-1]) / N
exact_max = math.sqrt(5) / 2 - 1; exact_deg = math.degrees(math.atan(0.5))
r_in = R / (1 + exact_max)               # nearest point of the contour oct = R

# ---- the game state: score.py on d1, and a Euclidean counterfactual -------------------------------
SRC = (_here.parent / 'ai' / 'score.py').read_text().split("if __name__=='__main__':")[0]
def model(src):
    ns = {'__name__': 'score_model', '__file__': str(_here.parent / 'ai' / 'score.py'), 'math': math}
    exec(compile(src, 'score.py', 'exec'), ns)
    return ns['S']
S_oct = model(SRC)
EUC = 'return mx+(mn>>1)'
assert EUC in SRC
S_euc = model(SRC.replace(EUC, 'return math.isqrt(a*a+b*b)'))
wrap = lambda v: ((v + 32768) % 65536) - 32768
def argmax(sc):
    best, bi = -32768, 0
    for i, v in enumerate(sc):
        if v > best: best, bi = v, i
    return bi, best

SNAP = WORK / 'ai' / 'nat' / 'd1.snap'
d = ram(SNAP)
L = lambda a: struct.unpack('>i', d[a:a + 4])[0]
SW = lambda a: struct.unpack('>h', d[a:a + 2])[0]
UW = lambda a: struct.unpack('>H', d[a:a + 2])[0]
sc = [wrap(v) for v in S_oct(d)[0]]
tbl = [SW(0x232fa + 2 * i) for i in range(64)]
match = sum(a == b for a, b in zip(sc, tbl))
pick, pick_s = argmax(sc); game_pick = UW(0x11ba); cur = UW(0x11bc)
esc = [wrap(v) for v in S_euc(d)[0]]
epick, epick_s = argmax(esc)
ex, ey = L(0x5f4a4), L(0x5f4ac)
ix = [L(0x69b82 + 402 * i) for i in range(64)]; iy = [L(0x69b86 + 402 * i) for i in range(64)]
own = list(d[0x69b40:0x69b80])
dm = ram(WORK / 'c_mv.snap'); t = 0x4d184
names = [dm[t + o:dm.index(b'\0', t + o)].decode() for o in struct.unpack('>64H', dm[t:t + 128])]
o48 = octd(ix[epick] - ex, iy[epick] - ey); t48 = math.hypot(ix[epick] - ex, iy[epick] - ey)
inside_true = [i for i in range(64) if i != cur and math.hypot(ix[i] - ex, iy[i] - ey) <= R]
inside_oct = [i for i in range(64) if i != cur and octd(ix[i] - ex, iy[i] - ey) <= R]

# the eleven distinct natural decisions (d1, d2 repeat e2, e3), octagon vs counterfactual
chain = []
flips = {}
for i in range(2, 13):
    r = ram(WORK / 'ai' / 'nat2' / f'e{i}.snap')
    a = argmax([wrap(v) for v in S_oct(r)[0]]); b = argmax([wrap(v) for v in S_euc(r)[0]])
    chain.append((f'e{i}', struct.unpack('>H', r[0x11bc:0x11be])[0], a[0], struct.unpack('>H', r[0x11ba:0x11bc])[0], b[0]))
    if a[0] != b[0]:                    # why it flips: distances of both islands, by each measure
        rl = lambda q: struct.unpack('>i', r[q:q + 4])[0]
        cx_, cy_ = rl(0x5f4a4), rl(0x5f4ac)
        def dd(j):
            ddx, ddy = rl(0x69b82 + 402 * j) - cx_, rl(0x69b86 + 402 * j) - cy_
            return octd(ddx, ddy), math.hypot(ddx, ddy), math.degrees(math.atan2(abs(ddy), abs(ddx)))
        flips[f'e{i}'] = (a[0], dd(a[0]), b[0], dd(b[0]))
same = lambda p, q: ram(WORK / 'ai' / p)[0x232fa:0x2337a] == ram(WORK / 'ai' / q)[0x232fa:0x2337a]
dup = same('nat/d1.snap', 'nat2/e2.snap') and same('nat/d2.snap', 'nat2/e3.snap')
changed = [c for c in chain if c[2] != c[4]]

print('error at R=%d: max %.4f%% at %.3f deg (exact %.4f%% at %.3f); 45 deg %.4f%%; min %.2e; mean %.3f%%'
      % (R, 100 * emax, emax_deg, 100 * exact_max, exact_deg, 100 * e45, emin, 100 * emean))
print('contour oct=R comes in to %d (%.4f R)' % (r_in, r_in / R))
print('d1: model matches %d/64 words; pick %d (%s) score %d; game $11ba %d; current %d (%s)'
      % (match, pick, names[pick], pick_s, game_pick, cur, names[cur]))
print('d1 counterfactual pick %d (%s) score %d; island %d oct %d true %.0f (+%.2f%%); octagon score %d'
      % (epick, names[epick], epick_s, epick, o48, t48, 100 * (o48 / t48 - 1), sc[epick]))
print('d1 islands within R: true distance %s, octagonal %s' % (inside_true, inside_oct))
print('d1 = e2 and d2 = e3 score tables:', dup)
print('chain (snap, current, model pick, game pick, euclid pick):', chain)
for k_, (p_, dp, q_, dq) in flips.items():
    print('flip %s: game %d oct %d true %.0f ang %.1f (+%.2f%%); counterfactual %d oct %d true %.0f ang %.1f (+%.2f%%)'
          % (k_, p_, dp[0], dp[1], dp[2], 100*(dp[0]/dp[1]-1), q_, dq[0], dq[1], dq[2], 100*(dq[0]/dq[1]-1)))
assert all(c[2] == c[3] for c in chain) and match == 64 and pick == game_pick

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

LEAD = ('Carrier Command (Realtime Games, 1988) is a real-time strategy and vehicle game: the player\'s aircraft '
        'carrier and a computer-controlled enemy carrier compete for 64 islands. Each time the enemy carrier '
        'arrives somewhere it decides where to go next by scoring every island, and distance is one term of '
        'that score. True distance is sqrt(dx^2 + dy^2), and the 68000 has no square-root instruction. The '
        'game uses max(|dx|, |dy|) + min(|dx|, |dy|) / 2 instead: two subtractions, a compare, a shift and an '
        'add. This is an octagonal approximation, exact along the axes and up to 11.8% too long in between. '
        'This page shows the error and what it does to the enemy\'s choices.')
A_READ = ('The grey circle is every point at true distance R from the centre; the blue octagon is every point '
          'the game\'s formula puts at distance R. Where the octagon touches the circle the formula is exact. '
          'Where it lies inside, a point truly nearer than R already reads R, so the formula overstates. The '
          'red line marks the worst direction, 26.57 degrees from an axis (and its mirror at 63.43).')
A_TAKE = ('The formula errs long, never short (apart from the half unit the final halving can drop), and by an '
          'amount fixed by the direction alone.')
B_READ = ('Top: how much longer than the truth the formula reads, against direction (0 = along x, 90 = along y; '
          'the pattern repeats every quarter turn). Bottom: the five steps as they appear in the game\'s code, '
          'with what each leaves in the registers D0 and D1.')
B_TAKE = (f'+{100*emax:.1f}% at worst, +{100*e45:.1f}% on the diagonal, +{100*emean:.1f}% on average. The code '
          f'is short enough to be pasted where it is needed rather than called: three copies in the scoring '
          f'routine and one in the travel-time calculation.')
C_READ = (f'A map of the archipelago in the saved state ai/nat/d1, taken just after the enemy carrier, at island '
          f'{cur}, scored every island. Each dot is an island, filled by the score the game stored for it '
          f'(darker blue is higher; the highest wins) and outlined by its owner. The blue octagon around the '
          f'carrier is the 3,000,000-unit cutoff as the game measures it, the grey circle the true 3,000,000; '
          f'an island beyond the cutoff scores a flat -15000. Heavy ring: the island the game chose. Dashed '
          f'ring: the island it would choose with true distance.')
C_TAKE = (f'Island {epick} {names[epick]} is truly inside the cutoff but reads {100*(o48/t48-1):.1f}% long, so it '
          f'falls outside and scores {sc[epick]}; with true distance it would score {esc[epick]} and win '
          f'(computed, not run in the game). Instead the carrier first hops to its own island {pick} and picks '
          f'{epick} at the next decision.')
D_READ = ('Eleven consecutive decisions of the enemy carrier, one column each: states e2 to e12, a chain of saved '
          'arrivals that starts from c_s30. "from" is where the carrier is, "picks" the island the game chose, '
          '"if true" the island our model chooses with true distance. Red boxes mark the decisions that differ, '
          'explained on the right.')
D_TAKE = (f'{len(changed)} of {len(chain)} decisions change: twice an island just past the octagonal cutoff, and '
          f'once an island that is nearer but lies in a direction the formula overstates more. That the game '
          f'would then play differently is inferred; nothing after the pick was run.')
KNOW = ('**How we know.** **Proven** means observed in an emulator running the game\'s own code, with a count of '
        'matches (N/N = matches out of cases). The scoring routine $2337a was ported to Python (py/ai/score.py). '
        'Its gate, a check script that can be re-run (gate_score.py), compares the port with the game in 21 '
        'saved states, each taken the moment the game finished scoring: all 1344 stored score words and all 21 '
        'chosen targets match (1344/1344, 21/21). The states e2 to e12 come from letting the game run on from '
        'c_s30, a saved Strategy game, with each arrival hurried by setting the travel countdown to 1 (the '
        'scoring does not read it). The error curves are computed from the formula itself. "Computed, not run" '
        'means the octagonal distance was replaced by the true one in the port only. $hex numbers are addresses '
        'in the game\'s memory, given as citations.')
CW2 = 392
lead_h = height(LEAD, 852, 13)
T0 = 64 + lead_h + 2
dy1 = T0 - 80
hAB = 494 - 80 + max(caption_h(CW2, A_READ, A_TAKE), caption_h(CW2, B_READ, B_TAKE)) - 2
dy2 = T0 + hAB + 14 - 494
hC = 940 - 494 + caption_h(820, C_READ, C_TAKE) - 2
dy3 = 494 + dy2 + hC + 14 - 948
hD = 1152 - 948 + caption_h(820, D_READ, D_TAKE) - 2
KY = 948 + dy3 + hD + 14
kh = height(KNOW, 820, 11.5)
H = int(KY + kh + 30)
INK, MUTE, ACC, BAD, GRID = '#1f2328', '#656d76', '#0969da', '#cf222e', '#d0d7de'
a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">')
a('<title id="t">Distance without a multiply</title>')
a('<desc id="d">Carrier Command (1988) measures distance as max(|dx|,|dy|) + min(|dx|,|dy|)/2, an octagon that is exact '
  'on the axes and at most 11.8 percent long, and its enemy carrier scores all 64 islands with it at $2337a to choose '
  'where to go. Sources: reversing/carriercommand/ai.md section 2; error computed from the integer formula, scores '
  'from py/ai/score.py on scratchpad ai/nat/d1.snap, by py/infographics/gen_octdist.py. Facts: octdist.facts.md.</desc>')
a('<style>text{font-family:Helvetica,Arial,sans-serif;fill:%s;font-size:12px}.t{font-size:20px;font-weight:bold}'
  '.h{font-size:14px;font-weight:bold}.m{fill:%s}.c{font-family:Menlo,monospace;font-size:11.5px}'
  '.s{font-size:11px;fill:%s}</style>' % (INK, MUTE, MUTE))
a(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
a('<text x="24" y="38" class="t">Distance without a multiply</text>')
para(a, LEAD, 24, 64, 852, size=13, color=INK)

def panel(x, y, w, h, title):
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="none" stroke="{GRID}"/>')
    a(f'<text x="{x+14}" y="{y+24}" class="h">{title}</text>')

# A: the octagon -----------------------------------------------------------------------------------
a(f'<g transform="translate(0,{dy1:.1f})">')
panel(24, 80, 420, hAB, 'A. The distance it really draws')
cx, cy, rad = 234, 262, 140
a(f'<line x1="{cx-rad-14}" y1="{cy}" x2="{cx+rad+14}" y2="{cy}" stroke="{GRID}"/>')
a(f'<line x1="{cx}" y1="{cy-rad-14}" x2="{cx}" y2="{cy+rad+14}" stroke="{GRID}"/>')
for q in (1, -1):
    a(f'<line x1="{cx-rad*0.72}" y1="{cy+q*rad*0.72}" x2="{cx+rad*0.72}" y2="{cy-q*rad*0.72}" stroke="{GRID}" stroke-dasharray="3 3"/>')
a(f'<circle cx="{cx}" cy="{cy}" r="{rad}" fill="none" stroke="{MUTE}" stroke-width="1.6"/>')
v = [(1, 0), (2/3, 2/3), (0, 1), (-2/3, 2/3), (-1, 0), (-2/3, -2/3), (0, -1), (2/3, -2/3)]
pts = ' '.join(f'{cx+rad*x:.1f},{cy-rad*y:.1f}' for x, y in v)
a(f'<polygon points="{pts}" fill="{ACC}" fill-opacity="0.12" stroke="{ACC}" stroke-width="2.2"/>')
th = math.radians(exact_deg)
a(f'<line x1="{cx}" y1="{cy}" x2="{cx+rad*math.cos(th):.1f}" y2="{cy-rad*math.sin(th):.1f}" stroke="{BAD}" stroke-width="1.2"/>')
px, py = cx + rad * math.cos(th) / (1 + exact_max), cy - rad * math.sin(th) / (1 + exact_max)
a(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" fill="{BAD}"/>')
a(f'<text x="{cx+rad*math.cos(th)+6:.0f}" y="{cy-rad*math.sin(th)-2:.0f}" class="s" style="fill:{BAD}">{exact_deg:.2f} deg</text>')
a(f'<circle cx="{cx+rad}" cy="{cy}" r="3.5" fill="{INK}"/><circle cx="{cx}" cy="{cy-rad}" r="3.5" fill="{INK}"/>')
a(f'<text x="{cx+rad+6}" y="{cy+16}" class="s">exact</text>')
a(f'<text x="{cx+6}" y="{cy-rad-6}" class="s">exact</text>')
a(f'<text x="38" y="{cy+rad-10}" class="s" style="fill:{MUTE}">circle: true</text>')
a(f'<text x="38" y="{cy+rad+4}" class="s" style="fill:{MUTE}">distance R</text>')
a(f'<text x="{cx+rad-30}" y="{cy+rad-10}" class="s" style="fill:{ACC}">octagon:</text>')
a(f'<text x="{cx+rad-30}" y="{cy+rad+4}" class="s" style="fill:{ACC}">max + min/2 = R</text>')
a(f'<text x="38" y="440" class="s">Every point on the octagon reads R. Its corners sit on the axes and at (2R/3, 2R/3);</text>')
a(f'<text x="38" y="455" class="s">the red point is {r_in/R:.3f} R from the centre, so the distance there reads {100*exact_max:.1f}% long.</text>')
a(f'<text x="38" y="470" class="s">Before truncation it never reads short; asr.l #1 on min loses at most half a unit.</text>')

# B: error over angle and the code ------------------------------------------------------------------
caption(38, 494, CW2, A_READ, A_TAKE)
panel(456, 80, 420, hAB, 'B. How long it reads, and the code')
bx, by, bw, bh = 506, 118, 340, 150
def BX(deg): return bx + bw * deg / 90
def BY(e): return by + bh * (0.13 - e) / 0.13
for e in (0, 0.04, 0.08, 0.12):
    a(f'<line x1="{bx}" y1="{BY(e):.1f}" x2="{bx+bw}" y2="{BY(e):.1f}" stroke="{GRID}" stroke-width="0.6"/>')
    a(f'<text x="{bx-8}" y="{BY(e)+4:.1f}" text-anchor="end" class="s">{100*e:.0f}%</text>')
for deg in (0, 15, 30, 45, 60, 75, 90):
    a(f'<text x="{BX(deg):.1f}" y="{by+bh+16}" text-anchor="middle" class="s">{deg}</text>')
a(f'<text x="{bx+bw/2}" y="{by+bh+31}" text-anchor="middle" class="s">angle from the x axis, degrees (repeats every 90)</text>')
pts = ' '.join(f'{BX(dg):.1f},{BY(e):.1f}' for dg, e in err[::150])
a(f'<polyline points="{pts}" fill="none" stroke="{ACC}" stroke-width="2"/>')
for dg in (emax_deg, 90 - emax_deg):
    a(f'<circle cx="{BX(dg):.1f}" cy="{BY(emax):.1f}" r="3.5" fill="{BAD}"/>')
a(f'<text x="{BX(emax_deg)-4:.1f}" y="{BY(emax)-8:.1f}" text-anchor="middle" class="s" style="fill:{BAD}">+{100*emax:.1f}%</text>')
a(f'<text x="{BX(45):.1f}" y="{BY(e45)+16:.1f}" text-anchor="middle" class="s">+{100*e45:.1f}%</text>')
a(f'<text x="{BX(45):.1f}" y="{BY(0)-6:.1f}" text-anchor="middle" class="s">mean +{100*emean:.1f}%</text>')
code = [('$233d2', 'sub.l', 'ex,D0 ; bpl ; neg.l D0', '|dx|'),
        ('$233da', 'sub.l', 'ey,D1 ; bpl ; neg.l D1', '|dy|'),
        ('$233e2', 'cmp.l', 'D0,D1 ; bcs ; exg D0,D1', 'D0 = max'),
        ('$233e8', 'asr.l', '#1,D1', 'min / 2'),
        ('$233ea', 'add.l', 'D1,D0', 'max + min/2')]
y = 330
for adr, op, arg, note in code:
    a(f'<text x="470" y="{y}" class="c" style="fill:{MUTE}">{adr}</text><text x="528" y="{y}" class="c">{op}</text>'
      f'<text x="578" y="{y}" class="c">{arg}</text><text x="862" y="{y}" text-anchor="end" class="s">{note}</text>')
    y += 18
a(f'<text x="470" y="440" class="s">No multiply, no square root. Inlined, not called: three times in $2337a</text>')
a(f'<text x="470" y="455" class="s">and once more for the travel countdown (distance / 250, $1ad2e).</text>')
a(f'<text x="470" y="470" class="s">Curve: the formula on integers at radius {R:,}, every 0.001 deg.</text>')

# C: the heat map ------------------------------------------------------------------------------------
caption(470, 494, CW2, B_READ, B_TAKE)
a('</g>')
a(f'<g transform="translate(0,{dy2:.1f})">')
panel(24, 494, 852, hC, 'C. The enemy scores all 64 islands with it ($2337a), state ai/nat/d1')
mx0, my0, mw = 44, 534, 480
xlo, xhi, ylo, yhi = -10200000, 9700000, -7800000, 7300000
sc_px = mw / (xhi - xlo); mh = sc_px * (yhi - ylo)
def MX(x): return mx0 + sc_px * (x - xlo)
def MY(y): return my0 + sc_px * (yhi - y)
a(f'<rect x="{mx0}" y="{my0}" width="{mw}" height="{mh:.1f}" fill="#f6f8fa"/>')
# cutoff: octagon and circle of radius R about the carrier
ov = ' '.join(f'{MX(ex+R*x):.1f},{MY(ey+R*y):.1f}' for x, y in v)
a(f'<circle cx="{MX(ex):.1f}" cy="{MY(ey):.1f}" r="{R*sc_px:.1f}" fill="none" stroke="{MUTE}" stroke-width="1.2"/>')
a(f'<polygon points="{ov}" fill="{ACC}" fill-opacity="0.07" stroke="{ACC}" stroke-width="1.6"/>')
LOW, HIGH = -16000, -4000
def col(v):
    f = min(1, max(0, (v - LOW) / (HIGH - LOW)))
    c0, c1 = (234, 238, 242), (9, 105, 218)
    return '#%02x%02x%02x' % tuple(round(p + (q - p) * f) for p, q in zip(c0, c1))
for i in range(64):
    X, Y = MX(ix[i]), MY(iy[i])
    if i == cur:
        a(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="5.5" fill="#ffffff" stroke="{INK}" stroke-width="1.6"/>')
        continue
    edge = BAD if own[i] == 2 else ('#9a6700' if own[i] == 1 else MUTE)
    a(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="5.5" fill="{col(sc[i])}" stroke="{edge}" stroke-width="1.3"/>')
a(f'<circle cx="{MX(ix[pick]):.1f}" cy="{MY(iy[pick]):.1f}" r="10" fill="none" stroke="{INK}" stroke-width="2"/>')
a(f'<circle cx="{MX(ix[epick]):.1f}" cy="{MY(iy[epick]):.1f}" r="10" fill="none" stroke="{INK}" stroke-width="1.4" stroke-dasharray="3 2"/>')
top = MY(ey + R) - 8
a(f'<line x1="{MX(ix[pick])-6:.1f}" y1="{MY(iy[pick])-9:.1f}" x2="{MX(ix[pick])-30:.1f}" y2="{top+4:.1f}" stroke="{INK}" stroke-width="0.8"/>')
a(f'<text x="{MX(ix[pick])-32:.1f}" y="{top:.1f}" text-anchor="end" class="s" style="fill:{INK};font-weight:bold">'
  f'{pick} {names[pick]}: picked</text>')
a(f'<line x1="{MX(ix[epick])+1:.1f}" y1="{MY(iy[epick])+10:.1f}" x2="{MX(ix[epick])+9:.1f}" y2="{MY(iy[epick])+120:.1f}" stroke="{INK}" stroke-width="0.8"/>')
lab = [(cur, f'{cur} {names[cur]}', 9, 4, 'start'),
       (epick, f'{epick} {names[epick]}', 10, 132, 'middle'),
       (63, '63 base', 9, 4, 'start'),
       (0, f'0 {names[0]}', -9, 4, 'end')]
for i, txt, ddx, ddy, anc in lab:
    a(f'<text x="{MX(ix[i])+ddx:.1f}" y="{MY(iy[i])+ddy:.1f}" text-anchor="{anc}" class="s" style="fill:{INK}">{txt}</text>')
a(f'<text x="{mx0}" y="{my0+mh+16:.1f}" class="s">{sc_px*1e6:.1f} px per million world units, north up. Colour: the score the game stored; '
  f'open ring at 56: the carrier; heavy ring: the pick.</text>')
# legend and story
lx = 560
for k in range(60):
    vv = LOW + (HIGH - LOW) * k / 59
    a(f'<rect x="{lx+k*4}" y="534" width="4.2" height="12" fill="{col(vv)}"/>')
a(f'<text x="{lx}" y="560" class="s">{LOW}</text><text x="{lx+240}" y="560" text-anchor="end" class="s">{HIGH} score</text>')
a(f'<circle cx="{lx+5}" cy="577" r="5" fill="#ffffff" stroke="{BAD}" stroke-width="1.3"/><text x="{lx+16}" y="581" class="s">enemy-owned</text>')
a(f'<circle cx="{lx+105}" cy="577" r="5" fill="#ffffff" stroke="{MUTE}" stroke-width="1.3"/><text x="{lx+116}" y="581" class="s">free</text>')
a(f'<circle cx="{lx+160}" cy="577" r="5" fill="#ffffff" stroke="#9a6700" stroke-width="1.3"/><text x="{lx+171}" y="581" class="s">player</text>')
story = [
    (INK, 'h', f'Model = game: {match}/64 words, pick {pick} = $11ba'),
    (MUTE, 's', 'score.py on this snapshot (taken at the return of $2337a) gives'),
    (MUTE, 's', f'every word of the table at $232fa, and its first maximum is'),
    (MUTE, 's', f'{pick} {names[pick]} ({pick_s}), the island the game stored.'),
    (MUTE, 's', 'Corpus gate: 1344/1344 words, 21/21 targets (gate_score.py).'),
    (None, None, ''),
    (INK, 'h', 'score = -distance / 2048, or -15000 beyond 3,000,000'),
    (MUTE, 's', '+3000 / +2000 a free island, -4000 its own, +4000 next to'),
    (MUTE, 's', 'its supply network, a small base-distance term; never here.'),
    (MUTE, 's', f'The octagon is that 3,000,000 cutoff; the grey circle is'),
    (MUTE, 's', f'the true one. Every free island is outside the octagon, so'),
    (MUTE, 's', f'the carrier hops to its own island {pick} first.'),
    (None, None, ''),
    (BAD, 'h', f'{epick} {names[epick]}: inside the circle, outside the octagon'),
    (MUTE, 's', f'true distance {t48:,.0f}, octagonal {o48:,} (+{100*(o48/t48-1):.1f}%):'),
    (MUTE, 's', f'it scores {sc[epick]}. Measured truly it would score {esc[epick]}'),
    (MUTE, 's', f'and win (dashed ring; computed, not run). The game picks'),
    (MUTE, 's', f'{epick} on the next decision, from {pick} (d2: target {epick}).'),
]
y = 610
for c, cls, txt in story:
    if c is None:
        y += 8; continue
    st = 'font-size:12px;font-weight:bold' if cls == 'h' else ''
    a(f'<text x="{lx}" y="{y}" class="s" style="fill:{c};{st}">{txt}</text>')
    y += 17 if cls == 'h' else 15

# D: the chain ----------------------------------------------------------------------------------------
caption(38, 940, 820, C_READ, C_TAKE)
a('</g>')
a(f'<g transform="translate(0,{dy3:.1f})">')
DY0 = 948
panel(24, DY0, 852, hD, 'D. Eleven arrivals in a row: the game\'s picks, and the picks with true distance')
a(f'<text x="44" y="{DY0+56}" class="s">from</text><text x="44" y="{DY0+76}" class="s">picks</text>'
  f'<text x="44" y="{DY0+96}" class="s">if true</text>')
x0, dxw = 100, 46
for k, (nm, cu, mp, gp, eu) in enumerate(chain):
    X = x0 + k * dxw
    diff = mp != eu
    if diff:
        a(f'<rect x="{X-20}" y="{DY0+40}" width="40" height="66" rx="4" fill="{BAD}" fill-opacity="0.08" stroke="{BAD}"/>')
    a(f'<text x="{X}" y="{DY0+56}" text-anchor="middle" class="c">{cu}</text>')
    a(f'<text x="{X}" y="{DY0+76}" text-anchor="middle" class="c" style="font-weight:bold">{mp}</text>')
    a(f'<text x="{X}" y="{DY0+96}" text-anchor="middle" class="c" style="fill:{BAD if diff else MUTE}">{eu}</text>')
    a(f'<text x="{X}" y="{DY0+122}" text-anchor="middle" class="s">{nm}</text>')
a(f'<text x="44" y="{DY0+148}" class="s">"picks" is the game\'s $11ba, which the model matches in all {len(chain)} '
  f'(ai/nat2: consecutive arrivals from c_s30; panel C is e2).</text>')
a(f'<text x="44" y="{DY0+164}" class="s">"if true" re-runs the model with sqrt(dx^2 + dy^2): computed, not run in the game. '
  f'It changes {len(changed)} of {len(chain)} picks.</text>')
a(f'<text x="44" y="{DY0+180}" class="s">All {len(chain)} are distinct states; ai/nat/d1, d2 repeat e2, e3 word for word.</text>')
y = DY0 + 52
for nm, (p_, dp, q_, dq) in flips.items():
    if dq[0] > R >= dq[1]:
        l1 = f'{nm}: {q_} is past the cutoff'
        l2 = f'octagonally ({dq[0]:,}), not truly ({dq[1]:,.0f})'
    else:
        l1 = f'{nm}: {q_} is nearer ({dq[1]:,.0f} vs {dp[1]:,.0f})'
        l2 = f'but at {dq[2]:.0f} deg reads +{100*(dq[0]/dq[1]-1):.1f}%, {p_} at {dp[2]:.0f} deg +{100*(dp[0]/dp[1]-1):.1f}%'
    a(f'<text x="612" y="{y}" class="s" style="fill:{INK};font-weight:bold">{l1}</text>')
    a(f'<text x="612" y="{y+14}" class="s">{l2}</text>')
    y += 34
caption(38, DY0 + 204, 820, D_READ, D_TAKE)
a('</g>')
a(f'<rect x="24" y="{KY:.1f}" width="852" height="{kh+16:.1f}" rx="6" fill="{NOTE}" stroke="{GRID}"/>')
para(a, KNOW, 38, KY + 20, 820, size=11.5, color=INK)
a('</svg>')
(OUT / 'octdist.svg').write_text('\n'.join(s))
print('wrote', OUT / 'octdist.svg')
