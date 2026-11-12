#!/usr/bin/env python3
"""Infographic: the Manta take-off $1d22c in the carrier's frame (vehicles.md section 5), drawn from captured game state.

usage: gen_takeoff.py [outdir]   (default WORK/infographics; writes takeoff.svg and prints the figures it draws)
Drives the same two runs as py/units/takeoff_proof.py through stserver (c_s30.snap, Manta 0 up the lift with $11386,
launch with $11af6; at rest, and with the carrier turning: $644 = $40 yaw, $648 = $30 target speed), reads slot 0 and
its entity at every entry of the Manta update $1cab4, and checks takeoff_proof.step (the proven model) against every
tick before drawing anything; it exits if one tick differs. Every point drawn is a captured game value; the only model
output drawn is the labelled frozen-heading variant in panel C. Facts and sources: takeoff.facts.md beside this script.
"""
import pathlib as _pl, sys as _sys
_here = _pl.Path(__file__).resolve().parent
_sys.path.insert(0, str(_here.parent)); _sys.path.insert(0, str(_here.parent / 'units'))
from ccpaths import *
import math
import struct
import takeoff_proof as T

sys.path.insert(0, str(ROOT / 'tools'))
from stclient import StServer

OUT = _pl.Path(_sys.argv[1]) if len(_sys.argv) > 1 else WORK / 'infographics'
OUT.mkdir(parents=True, exist_ok=True)
U2D = 360 / 65536


# ---- capture ------------------------------------------------------------------------------------
def capture(pokes):
    """takeoff_proof.main's drive, plus the state read just after the launch call (L), before the first update."""
    s = StServer(str(ROOT))
    s('load', snapshot=str(ANCHOR))
    s('poke', addr=0x126c, width=4, value=0x00ff0001)          # the crack's stack leak (README "Provenance")
    for addr, val in pokes:
        s('poke', addr=addr, width=4, value=val)
    w = lambda a: struct.unpack('>h', s.read(a, 2))[0]
    s.call_resume(0x11386, d2=2)
    s('bp_set', addrs=[0x1cab4])
    for k in range(400):
        assert s('run', max_steps=400000)['reason'] == 'breakpoint'
        if s.read(0x498 + 28, 1)[0] == 1 and w(0xdca) == 0:
            break
    else:
        sys.exit('the Manta never reached the deck')
    lift = k + 1
    s('bp_clear', addrs=[0x1cab4])
    s.call_resume(0x11af6, d2=2)
    L = T.read(s)
    s('bp_set', addrs=[0x1cab4])
    S = []
    for k in range(200):
        assert s('run', max_steps=400000)['reason'] == 'breakpoint'
        S.append(T.read(s))
        if S[-1]['state'] != 2:
            break
    s.close()
    return lift, L, S


def check(L, S):
    """Model ticks matched: (from the launch state, all ticks), and the takeoff_proof count (from S[0])."""
    seq = [L] + S
    ok = []
    for k in range(len(seq) - 1):
        p, g = T.step(seq[k]), seq[k + 1]
        names = T.FIELDS + (T.HANDOFF if g['state'] == 3 else [])
        ok.append(all(p[f] == g[f] for f in names))
    return sum(ok), len(ok), sum(ok[1:]), len(ok) - 1


RUNS = {}
for name, pokes in (('rest', []), ('turn', [(0x644, 0x00400000), (0x648, 0x00300000)])):
    lift, L, S = capture(pokes)
    m_all, n_all, m_pf, n_pf = check(L, S)
    print(f'{name}: lift {lift} ticks; launch alt {L["alt"]} phase {L["phase"]} state {L["state"]}; '
          f'model {m_all}/{n_all} from launch, {m_pf}/{n_pf} as takeoff_proof counts')
    if m_all != n_all:
        sys.exit(f'{name}: the model does not match every tick; not drawing')
    RUNS[name] = dict(lift=lift, seq=[L] + S, n=n_all, n_pf=n_pf)

R, Tn = RUNS['rest']['seq'], RUNS['turn']['seq']


def score(seq):
    return sum(all(T.step(seq[k])[f] == seq[k + 1][f]
                   for f in T.FIELDS + (T.HANDOFF if seq[k + 1]['state'] == 3 else [])) for k in range(len(seq) - 1))


broke = {}
for key, base in T.P0.items():
    T.P.clear(); T.P.update(T.P0)
    T.P[key] = (1 - base) if key in ('add_carrier', 'follow_heading', 'inverse') else base + (1 if base > 0 else -1)
    broke[key] = (score(R) < len(R) - 1, score(Tn) < len(Tn) - 1)
T.P.clear(); T.P.update(T.P0)
n_br_rest = sum(b[0] for b in broke.values()); n_br_turn = sum(b[1] for b in broke.values())
n_br_any = sum(b[0] or b[1] for b in broke.values())
unbroken = [k for k, b in broke.items() if not (b[0] or b[1])]
print(f'controls broken: at rest {n_br_rest}/{len(broke)}, turning {n_br_turn}/{len(broke)}, either {n_br_any}; '
      f'unbroken {unbroken}')
bounds = {}
for key, ph0, done in (('roll_end', 1, lambda x: x['phase'] == 2), ('deck_end', 2, lambda x: x['state'] == 3)):
    lo = max(R[k + 1]['dz'] for k in range(len(R) - 1) if R[k]['phase'] == ph0 and R[k + 1]['phase'] == ph0
             and R[k + 1]['state'] == 2)
    hi = [R[k + 1]['dz'] for k in range(len(R) - 1) if R[k]['phase'] == ph0 and done(R[k + 1])][0]
    bounds[key] = (lo, hi)
print('threshold bounds from the data:', bounds)
N = RUNS['rest']['n']
assert RUNS['turn']['n'] == N
# the carrier frame: deck offset, phase, speed, altitude and pitch are the same tick for tick in both runs
same = all(R[k][f] == Tn[k][f] for k in range(N + 1) for f in ('phase', 'dx', 'dz', 'alt', 'pitch')) and \
    all(R[k]['v'] == Tn[k]['v'] for k in range(N))
print('carrier-frame state identical in both runs (phase, deck x/z, altitude, pitch; speed before hand-off):', same)
assert same
assert all(x['dx'] == 0 for x in R + Tn)

ph = [x['phase'] for x in R]
# ticks per phase: tick k goes from seq[k] to seq[k+1]; it belongs to the phase it starts in
n_rise = sum(1 for k in range(N) if ph[k] == 0)
n_roll = sum(1 for k in range(N) if ph[k] == 1)
n_climb = sum(1 for k in range(N) if ph[k] == 2)
end = R[-1]
print(f'ticks from launch {N}: rise {n_rise}, roll {n_roll}, climb {n_climb}')
print(f'altitude {R[0]["alt"]} -> {end["alt"]}; deck z {R[0]["dz"]} -> {end["dz"]}; pitch {R[0]["pitch"]} -> '
      f'{end["pitch"]} ({end["pitch"]*U2D:.2f} deg); slot pitch at hand-off {end["s4"]}')
k_roll = ph.index(1); k_climb = ph.index(2)
k_floor = next(k for k in range(N + 1) if R[k]['pitch'] == -1655)
print(f'phase 1 from entry {k_roll} (alt {R[k_roll]["alt"]}), phase 2 from entry {k_climb} (deck z {R[k_climb]["dz"]}), '
      f'pitch floor at entry {k_floor}, deck z {R[k_floor]["dz"]}')
vmax_k = next(k for k in range(N + 1) if R[k]['v'] == 60)
print(f'speed 60 reached at entry {vmax_k}, deck z {R[vmax_k]["dz"]}')
climb_deg = math.degrees(math.atan2(10, 60))
print(f'climb path angle atan(10/60) = {climb_deg:.2f} deg; pitch floor {abs(-1655)*U2D:.2f} deg')

hs = [x['cheading'] for x in Tn]
dh = sorted(set(hs[k + 1] - hs[k] for k in range(N)))
print(f'turning: carrier heading {hs[0]} -> {hs[-1]} ({(hs[-1]-hs[0])*U2D:.2f} deg), per tick {dh}; '
      f'carrier speed {Tn[0]["cv"]} -> {Tn[-1]["cv"]}; Manta speed at hand-off {Tn[-1]["v"]} (rest {R[-1]["v"]})')
# the Manta's heading is the carrier's from the tick before
lag = all(Tn[k + 1]['heading'] == Tn[k]['cheading'] for k in range(N))
print('Manta heading = carrier heading one tick earlier:', lag)


# world frame: origin the carrier at launch, axes along/across the carrier heading at launch
def frame(run):
    h0 = run[0]['cheading']
    a = 2 * math.pi * h0 / 65536
    fx, fz = math.sin(a), math.cos(a)            # forward: atan2(dx, dz) convention, 0 along +z (vehicles.md 2)
    ox, oz = run[0]['cx'], run[0]['cz']
    def f(x, z):
        x, z = x - ox, z - oz
        return x * fx + z * fz, x * fz - z * fx  # along, across (+ toward +x of the heading)
    return f


def frozen(run):
    """Model variant (not the game): the deck offset rotated by the launch heading instead of the current one."""
    h0 = run[0]['cheading']
    return [T.deck_to_world(run[k]['dx'], run[k + 1]['dz'], h0, run[k]['cx'], run[k]['cz']) for k in range(N)]


W_ = {}
for name, run in (('rest', R), ('turn', Tn)):
    f = frame(run)
    W_[name] = dict(m=[f(x['x'], x['z']) for x in run], c=[f(x['cx'], x['cz']) for x in run],
                    fz=[f(*p) for p in frozen(run)], f=f)
# offset Manta - carrier (both at the same entry): its bearing tracks the carrier heading of the entry before
def bearing(x, z):
    return math.atan2(x, z) / (2 * math.pi) * 65536
off_err = max(abs(bearing(Tn[k + 1]['x'] - Tn[k]['cx'], Tn[k + 1]['z'] - Tn[k]['cz']) - Tn[k]['cheading'])
              for k in range(k_roll + 2, N))      # deck z >= 274: integer rounding of x makes short offsets noisy
print(f'turning: bearing of (Manta at k+1) - (carrier at k) minus carrier heading at k, deck z >= 274: '
      f'at most {off_err:.1f} units ({off_err*U2D:.2f} deg)')
wt, wr = W_['turn'], W_['rest']
print(f'turning: Manta world travel along {wt["m"][-1][0]-wt["m"][0][0]:.0f}, across {wt["m"][-1][1]:.1f}; '
      f'carrier along {wt["c"][-1][0]:.0f}, across {wt["c"][-1][1]:.1f}')
print(f'rest: Manta along {wr["m"][0][0]:.0f} -> {wr["m"][-1][0]:.0f}, across {min(p[1] for p in wr["m"]):.1f}..'
      f'{max(p[1] for p in wr["m"]):.1f}')
fz_gap = math.hypot(wt['fz'][-1][0] - wt['m'][-1][0], wt['fz'][-1][1] - wt['m'][-1][1])
print(f'turning, last tick: frozen-heading variant {fz_gap:.1f} units from the game '
      f'(across {wt["fz"][-1][1]:.1f} vs {wt["m"][-1][1]:.1f})')
# world speed per tick from captured positions (turning run)
ws = [math.hypot(Tn[k + 1]['x'] - Tn[k]['x'], Tn[k + 1]['z'] - Tn[k]['z']) for k in range(N)]
cs = [math.hypot(Tn[k + 1]['cx'] - Tn[k]['cx'], Tn[k + 1]['cz'] - Tn[k]['cz']) for k in range(N)]
print(f'turning: Manta world step on the last deck tick {ws[-1]:.1f}; carrier step then {cs[-1]:.1f}; '
      f'deck speed {Tn[-2]["v"]}; hand-off speed {Tn[-1]["v"]}')

# ---- svg ----------------------------------------------------------------------------------------
W, H = 900, 1064
s = []
a = s.append
INK, MUTE, ACC, BAD, GRID = '#1f2328', '#656d76', '#0969da', '#cf222e', '#d0d7de'
C_RISE, C_ROLL, C_CLIMB = '#8c959f', '#bf8700', '#1a7f37'
C_TURN = '#8250df'
PHC = [C_RISE, C_ROLL, C_CLIMB]
a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">')
a('<title id="t">Taking off from a moving deck</title>')
a('<desc id="d">Carrier Command (1988) flies the Manta take-off ($1d22c) in the carrier\'s frame: a deck offset that '
  'rises, rolls and climbs, rotated by the carrier\'s heading and added to its position each tick. Source: '
  'reversing/carriercommand/vehicles.md section 5; points are game state captured through stserver by '
  'py/infographics/gen_takeoff.py and checked tick by tick against the model in py/units/takeoff_proof.py. '
  'Facts: takeoff.facts.md.</desc>')
a('<style>text{font-family:Helvetica,Arial,sans-serif;fill:%s;font-size:12px}.t{font-size:20px;font-weight:bold}'
  '.h{font-size:14px;font-weight:bold}.m{fill:%s}.c{font-family:Menlo,monospace;font-size:11.5px}'
  '.s{font-size:11px;fill:%s}</style>' % (INK, MUTE, MUTE))
a(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
a('<text x="24" y="38" class="t">Taking off from a moving deck</text>')
a('<text x="24" y="60" class="m">Carrier Command (Realtime Games, 1988), routine $1d22c: the Manta is flown in the '
  'carrier\'s frame until it leaves the bow,</text>')
a('<text x="24" y="76" class="m">so the same take-off follows the carrier wherever it goes and however it turns.</text>')


def panel(x, y, w, h, title):
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="none" stroke="{GRID}"/>')
    a(f'<text x="{x+14}" y="{y+24}" class="h">{title}</text>')


def dot(x, y, c, r=3.0, op=1.0):
    a(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{c}" fill-opacity="{op}"/>')


# A + B share the deck-z axis -------------------------------------------------------------------
panel(24, 96, 852, 362, f'A. In the carrier\'s frame: the same {N} ticks at rest and turning')
ax0, aw = 120, 700
zmax = 2100
def AX(dz): return ax0 + aw * dz / zmax
# A: plan strip, the deck centreline (side view scale defined here for the threshold lines)
by0, bh = 210, 150
amin, amax = 170, 440
def BY(alt): return by0 + bh * (amax - alt) / (amax - amin)
py0 = 160
a(f'<line x1="{AX(0):.1f}" y1="{py0}" x2="{AX(zmax):.1f}" y2="{py0}" stroke="{GRID}" stroke-width="14" stroke-linecap="butt"/>')
a(f'<text x="{ax0-12}" y="{py0-4}" text-anchor="end" class="s">plan</text>')
a(f'<text x="{ax0-12}" y="{py0+10}" text-anchor="end" class="s">deck x = 0</text>')
for k in range(N + 1):
    dot(AX(R[k]['dz']), py0, PHC[ph[k]] if R[k]['state'] == 2 else INK, 3.0)
for thr, lab in ((650, '650: rotate'), (2000, '2000: airborne')):
    a(f'<line x1="{AX(thr):.1f}" y1="{py0-22}" x2="{AX(thr):.1f}" y2="{py0+12}" stroke="{MUTE}" stroke-dasharray="3 3"/>')
    a(f'<line x1="{AX(thr):.1f}" y1="{BY(285):.1f}" x2="{AX(thr):.1f}" y2="{BY(175):.1f}" stroke="{MUTE}" stroke-dasharray="3 3"/>')
    a(f'<text x="{AX(thr)+4:.1f}" y="{py0-14}" class="s">{lab}</text>')
a(f'<text x="{AX(250):.1f}" y="{py0-14}" text-anchor="middle" class="s">lift, deck z 250</text>')
a(f'<text x="{AX(430):.1f}" y="{py0+24}" text-anchor="middle" class="s">speed +8 a tick</text>')
a(f'<text x="{AX(1300):.1f}" y="{py0+24}" text-anchor="middle" class="s">60 a tick</text>')
# B: side view, altitude against deck z
for alt in (180, 200, 300, 400, 430):
    a(f'<line x1="{AX(0):.1f}" y1="{BY(alt):.1f}" x2="{AX(zmax):.1f}" y2="{BY(alt):.1f}" stroke="{GRID}" stroke-width="0.6"/>')
    a(f'<text x="{ax0-8}" y="{BY(alt)+4:.1f}" text-anchor="end" class="s">{alt}</text>')
a(f'<text x="44" y="{BY(305)}" class="s" transform="rotate(-90 44 {BY(305)})" text-anchor="middle">side: altitude</text>')
for dz in range(0, 2001, 250):
    a(f'<text x="{AX(dz):.1f}" y="{by0+bh+16}" text-anchor="middle" class="s">{dz}</text>')
a(f'<text x="{AX(1050):.1f}" y="{by0+bh+32}" text-anchor="middle" class="s">deck offset z (entity +30), '
  'along the deck centreline from the carrier\'s reference point</text>')
pts = ' '.join(f'{AX(x["dz"]):.1f},{BY(x["alt"]):.1f}' for x in R)
a(f'<polyline points="{pts}" fill="none" stroke="{GRID}" stroke-width="1.2"/>')
SEG = 26
for k in range(N + 1):
    x, y = AX(R[k]['dz']), BY(R[k]['alt'])
    c = PHC[ph[k]] if R[k]['state'] == 2 else INK
    if ph[k] == 0:
        dot(x, y, c, 2.4)
        continue
    t = -R[k]['pitch'] * 2 * math.pi / 65536          # drawn nose up for negative pitch (inferred from the climb)
    if k % 2 == 0 or R[k]['pitch'] != R[k - 1]['pitch'] or R[k]['state'] == 3:
        a(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + SEG*math.cos(t):.1f}" y2="{y - SEG*math.sin(t):.1f}" '
          f'stroke="{c}" stroke-width="1.6"/>')
    dot(x, y, c, 2.4)
notes = [(C_RISE, f'rise: {n_rise} ticks of +2, altitude 180 to 200, at deck z 250'),
         (C_ROLL, f'roll: pitch stays {R[0]["pitch"]} ({-R[0]["pitch"]*U2D:.1f} degrees) as on the lift'),
         (C_CLIMB, f'rotate: pitch -240 a tick to -1655 ({1655*U2D:.1f} degrees)'),
         (C_CLIMB, f'climb: +10 a tick against 60 along, a {climb_deg:.1f} degree path'),
         (INK, f'airborne at deck z {end["dz"]}, altitude {end["alt"]}')]
ny = BY(428)
a(f'<rect x="{AX(10):.1f}" y="{ny-12:.1f}" width="300" height="72" fill="#ffffff"/>')
for c, t_ in notes:
    a(f'<text x="{AX(15):.1f}" y="{ny:.1f}" class="s"><tspan style="fill:{c};font-weight:bold">-</tspan> {t_}</text>')
    ny += 14
# legend row
ly = 424
items = [(C_RISE, f'rise ({n_rise} ticks)'), (C_ROLL, f'roll ({n_roll})'), (C_CLIMB, f'rotate and climb ({n_climb})'),
         (INK, 'airborne (+28 = 3)')]
lx = 120
for c, t in items:
    dot(lx, ly - 4, c, 4)
    a(f'<text x="{lx+9}" y="{ly}" class="s">{t}</text>')
    lx += {C_RISE: 110, C_ROLL: 80, C_CLIMB: 170, INK: 130}[c]
a(f'<text x="{lx}" y="{ly}" class="s">strokes: pitch at its true angle</text>')
a(f'<text x="120" y="{ly+18}" class="s">Every dot is a captured game value; the at-rest and turning runs give the same values here, '
  'tick for tick. Pitch units read as 65536 to the turn (inferred).</text>')

# C: world frame --------------------------------------------------------------------------------
cy_top = 472
panel(24, cy_top, 852, 318, 'B. On the sea: the deck offset rotated by the carrier\'s heading each tick')
cx0, cw = 96, 720
amax_ = 3600
def CX(al): return cx0 + cw * (al + 100) / (amax_ + 100)
ymid = cy_top + 150
all_ac = [p[1] for nm in ('rest', 'turn') for key in ('m', 'c', 'fz') for p in W_[nm][key]]
ac_hi, ac_lo = math.ceil(max(all_ac) / 25) * 25, math.floor(min(all_ac) / 25) * 25 - 25
across_lim = ac_hi
lat_px = 190 / (ac_hi - ac_lo)               # pixels per across unit
def CY(ac): return cy_top + 84 + lat_px * (ac_hi - ac)
mag = lat_px / (cw / (amax_ + 100))
print(f'panel B: across scale {mag:.2f} x the along scale (across {ac_lo}..{ac_hi})')
for ac in range(ac_lo, ac_hi + 1, 25):
    a(f'<line x1="{CX(-100):.1f}" y1="{CY(ac):.1f}" x2="{CX(amax_):.1f}" y2="{CY(ac):.1f}" stroke="{GRID}" '
      f'stroke-width="{0.9 if ac == 0 else 0.5}"/>')
    a(f'<text x="{cx0-8}" y="{CY(ac)+4:.1f}" text-anchor="end" class="s">{ac:+d}</text>')
for al in range(0, amax_ + 1, 500):
    a(f'<text x="{CX(al):.1f}" y="{CY(ac_lo)+16:.1f}" text-anchor="middle" class="s">{al}</text>')
a(f'<text x="{CX(1750):.1f}" y="{CY(ac_lo)+32:.1f}" text-anchor="middle" class="s">world units along the carrier\'s '
  'heading at launch, from the carrier at launch</text>')
a(f'<text x="44" y="{CY(0)}" class="s" transform="rotate(-90 44 {CY(0)})" text-anchor="middle">across, toward +x</text>')
# carrier tracks
for nm, col in (('rest', ACC), ('turn', C_TURN)):
    pts = ' '.join(f'{CX(p[0]):.1f},{CY(p[1]):.1f}' for p in W_[nm]['c'])
    a(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.4" stroke-opacity="0.45"/>')
# offset vectors carrier -> Manta for the turning run, every 6th tick
for k in range(0, N, 6):
    c0, m1 = W_['turn']['c'][k], W_['turn']['m'][k + 1]
    a(f'<line x1="{CX(c0[0]):.1f}" y1="{CY(c0[1]):.1f}" x2="{CX(m1[0]):.1f}" y2="{CY(m1[1]):.1f}" stroke="{C_TURN}" '
      f'stroke-width="0.8" stroke-opacity="0.6"/>')
# frozen-heading variant (model, not game)
pts = ' '.join(f'{CX(p[0]):.1f},{CY(p[1]):.1f}' for p in W_['turn']['fz'])
a(f'<polyline points="{pts}" fill="none" stroke="{BAD}" stroke-width="1.3" stroke-dasharray="4 3"/>')
for nm, col in (('rest', ACC), ('turn', C_TURN)):
    for k, p in enumerate(W_[nm]['m']):
        dot(CX(p[0]), CY(p[1]), col, 2.3)
    p = W_[nm]['c'][0]; dot(CX(p[0]), CY(p[1]), col, 4.5, 0.6)
p = W_['turn']['c'][-1]; dot(CX(p[0]), CY(p[1]), C_TURN, 4.5, 0.6)
pr = W_['rest']['m'][-1]; pt = W_['turn']['m'][-1]; pc = W_['turn']['c'][-1]; pf = W_['turn']['fz'][-1]
a(f'<text x="{CX(pr[0]):.1f}" y="{CY(-20):.1f}" text-anchor="end" class="s" style="fill:{ACC}">at rest: leaves the deck {pr[0]:.0f} along</text>')
a(f'<text x="{CX(pt[0])-8:.1f}" y="{CY(pt[1])-10:.1f}" text-anchor="end" class="s" style="fill:{C_TURN}">turning: {pt[0]:.0f} along, '
  f'{pt[1]:+.0f} across</text>')
a(f'<text x="{CX(2200):.1f}" y="{CY(-20):.1f}" class="s" style="fill:{BAD}">dashes: heading frozen at launch</text>')
a(f'<text x="{CX(2200):.1f}" y="{CY(-20)+13:.1f}" class="s" style="fill:{BAD}">(model variant, not the game): {fz_gap:.0f} short</text>')
a(f'<text x="{CX(pc[0])-6:.1f}" y="{CY(pc[1])-12:.1f}" text-anchor="end" class="s" style="fill:{C_TURN}">carrier after {N} ticks</text>')
a(f'<text x="{CX(0)+8:.1f}" y="{CY(0)+24:.1f}" class="s">carriers at launch</text>')
a(f'<text x="{cx0}" y="{cy_top+46}" class="s">Across is drawn {mag:.0f} times the along scale. Thin lines: carrier to Manta '
  'every 6th tick.</text>')
a(f'<text x="{cx0}" y="{cy_top+60}" class="s">Turning run: heading +{dh[0]} a tick ({(hs[-1]-hs[0])*U2D:.1f} degrees over the take-off), '
  f'carrier speed {Tn[0]["cv"]} to {Tn[-1]["cv"]}; at rest both stay put.</text>')

# D: the per-tick rule --------------------------------------------------------------------------
dy_top = cy_top + 330
panel(24, dy_top, 520, 250, 'C. One tick of $1d22c (slot +28 = 2, phase in +29)')
rows = [
    (C_RISE, '0', 'altitude += 2', 'at 200: phase 1, speed 0'),
    (C_ROLL, '1', 'speed = min(speed + 8, 60); z += speed', 'at deck z >= 650: phase 2'),
    (C_CLIMB, '2', 'pitch = max(pitch - 240, -1655)', 'altitude += 10; z += speed'),
    (INK, '', 'at deck z >= 2000: airborne', 'speed += carrier speed, pitch / -14'),
    (ACC, '', 'heading = carrier heading', 'every phase'),
    (ACC, '', 'pos = carrier + rotate((0, z), heading)', '$1d908, every phase'),
]
y = dy_top + 52
for c, n, l1, l2 in rows:
    a(f'<circle cx="52" cy="{y-4}" r="{9 if n else 5}" fill="{c}"/>')
    if n:
        a(f'<text x="48.5" y="{y}" style="fill:#fff;font-size:11px;font-weight:bold">{n}</text>')
    a(f'<text x="70" y="{y}" class="c">{l1}</text><text x="70" y="{y+14}" class="s">{l2}</text>')
    y += 29
a(f'<text x="38" y="{dy_top+238}" class="s">z: the deck offset. Heading and position use the carrier after its own update this frame.</text>')

# E: the proof ----------------------------------------------------------------------------------
ex = 556
panel(ex, dy_top, 320, 250, 'D. What is proven')
lines = [
    ('model against the game, per tick:', True),
    (f'at rest {RUNS["rest"]["n_pf"]}/{RUNS["rest"]["n_pf"]}, turning {RUNS["turn"]["n_pf"]}/{RUNS["turn"]["n_pf"]}'
     ' (takeoff_proof.py)', False),
    (f'{N}/{N} in both with the launch tick', False),
    ('(checked by gen_takeoff.py)', False),
    ('constants nudged by one break a tick:', True),
    (f'{n_br_turn} of {len(broke)} (turning run); the deck thresholds are', False),
    (f'pinned only to ({bounds["roll_end"][0]}, {bounds["roll_end"][1]}] and ({bounds["deck_end"][0]}, '
     f'{bounds["deck_end"][1]}],', False),
    ('650 and 2000 are read from code', False),
    ('hand-off speed:', True),
    (f'{R[-1]["v"]} at rest, {Tn[-1]["v"]} turning = 60 + {Tn[-2]["cv"]}; the last', False),
    (f'deck tick moved {ws[-1]:.0f} over the sea (from positions)', False),
]
y = dy_top + 50
for t, bold in lines:
    a(f'<text x="{ex+16}" y="{y}" class="s"{" style=\"fill:%s;font-weight:bold\"" % INK if bold else ""}>{t}</text>')
    y += 16 if not bold else 15
a('</svg>')
(OUT / 'takeoff.svg').write_text('\n'.join(s))
print('wrote', OUT / 'takeoff.svg')
