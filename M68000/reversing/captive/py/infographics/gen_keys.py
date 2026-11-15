"""Keys you can always reach, almost: the lock-and-key rule of Captive's base generator, its one slip, and what a
route search adds. Drawn in a plain style taken from the box art (slate, gold light, the red circle-arrow logo).

    uv run python -I reversing/captive/py/infographics/gen_keys.py

Inputs:
  - Phoopel (D0 = 13, D2 = 0) from the chained generator (mapgen/full/route.Base; chain gated 400/400).
  - scratchpad/captive/infographics/data/route.json, written by
    `mapgen/full/route.py 0 100 -j 10 --json <that file>` (about 15 min on 10 cores): routes over missions 1..100.
  - Census counts quoted from mapgen.md "Why the key is reachable" and "Sealed keys" (see keys.facts.md).
Writes scratchpad/captive/infographics/keys.svg and prints every number it draws.
"""
import html
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
M = os.path.abspath(os.path.join(HERE, '../../../..'))
sys.path.insert(0, os.path.join(HERE, '..', 'mapgen', 'full'))
sys.path.insert(0, os.path.join(HERE, '..', 'phoopel'))
import route as R  # noqa: E402
from shown import shown  # noqa: E402

OUT = os.path.join(M, 'scratchpad', 'captive', 'infographics')
DATA = os.environ.get('ROUTE_JSON') or os.path.join(OUT, 'data', 'route.json')

BG, PANEL, LINE = '#1d2631', '#263241', '#3a4859'
STEEL, DIM, ROCK = '#7d8b9a', '#3b4757', '#1d2631'
GOLD, GOLD2, RED, INK, MUTED = '#f2b632', '#9c7420', '#d63a2f', '#efe9da', '#a9b3bf'
TITLE = "font-family:'Barlow Condensed';font-weight:800"
BODY = "font-family:'Barlow Condensed';font-weight:400"
W = 1200

out = []


def t(x, y, s, size=20, fill=INK, style=BODY, anchor='start', extra=''):
    out.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" style="{style}" text-anchor="{anchor}" {extra}>'
               f'{html.escape(s)}</text>')


def rect(x, y, w, h, fill, rx=0, stroke=None, sw=0):
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ''
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"{s}/>')


def logo(cx, cy, r):
    """The box art's red disc with a white up-arrow: used for the base entrance (the way in and out)."""
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{RED}"/>')
    a = r * 0.55
    out.append(f'<path d="M{cx} {cy - a} L{cx + a * 0.8} {cy} L{cx + a * 0.3} {cy} L{cx + a * 0.3} {cy + a} '
               f'L{cx - a * 0.3} {cy + a} L{cx - a * 0.3} {cy} L{cx - a * 0.8} {cy} Z" fill="{INK}"/>')


def clipboard(x, y, s):
    rect(x, y, s, s * 1.25, INK, rx=2)
    rect(x + s * 0.3, y - s * 0.12, s * 0.4, s * 0.25, GOLD2, rx=1)
    for k in range(3):
        rect(x + s * 0.18, y + s * (0.35 + 0.27 * k), s * 0.64, max(1.5, s * 0.08), BG)


def flames(x, y, s):
    rect(x, y, s, s, '#3a1a12')
    n = 4
    for i in range(n):
        bx = x + i * s / n
        h = s * (0.85 if i % 2 else 0.6)
        out.append(f'<path d="M{bx + 1} {y + s} L{bx + s / n / 2} {y + s - h} L{bx + s / n - 1} {y + s} Z" '
                   f'fill="{RED if i % 2 == 0 else GOLD}"/>')


def para(x, y, lines, size=19, fill=MUTED, lh=1.3):
    for i, s in enumerate(lines):
        t(x, y + i * size * lh, s, size, fill)
    return y + len(lines) * size * lh


def panel(y, h, letter, title, note=None):
    rect(30, y, W - 60, h, PANEL, rx=6)
    t(56, y + 46, f'{letter}.', 32, GOLD, TITLE)
    t(96, y + 46, title, 32, INK, TITLE)
    if note:
        t(W - 56, y + 44, note, 18, MUTED, BODY, 'end')


# ---------------- data ----------------
rows = json.load(open(DATA))
clip = [r for r in rows if r.get('clip_plan') and r.get('clip_opt')]
lab = [r for r in rows if r.get('label_plan') and r.get('label_opt')]
med = lambda v: statistics.median(v)
n_bases = len(rows)
n_fin_clip = sum(r.get('clip_finishable', False) for r in rows if r['lb'] is not None)
n_fin_lab = sum(r.get('label_finishable', False) for r in rows if r['lb'] is not None)
n_has_gen = sum(r['lb'] is not None for r in rows)
plan_opt = med([r['clip_plan'] / r['clip_opt'] for r in clip])
sweep_opt = med([r['clip_sweep'] / r['clip_opt'] for r in clip if r.get('clip_sweep')])
opt_lb = med([r['clip_opt'] / r['lb'] for r in clip])
need_med = med([r['clip_need'] for r in clip])
locks_med = med([r['locks'] for r in clip])
lab_plan_opt = med([r['label_plan'] / r['label_opt'] for r in lab])
n_sealed = sum(r['sealed'] for r in rows)
n_keyed = sum(r['keyed'] for r in rows)
n_sealed_bases = sum(r['sealed'] > 0 for r in rows)
stuck = [r for r in rows if r['lb'] is not None and not r['clip_finishable']]
stuck_missions = sorted({r['mission'] for r in stuck if r['target'] != 11})
n_astar_limit = sum(1 for r in rows if r.get('clip_finishable') and r.get('clip_opt') is None)
print(f'sealed keys {n_sealed} of {n_keyed} keyed locks, in {n_sealed_bases} bases; not finishable from the clipboards '
      f'{len(stuck)} bases ({sum(r["target"] == 11 for r in stuck)} final bases), {len(stuck_missions)} missions with an '
      f'ordinary target among them; A* node limit {n_astar_limit}')
print(f'bases {n_bases}; with a reachable generator side (all doors open) {n_has_gen}; finishable with clipboards '
      f'{n_fin_clip}; with label inversion {n_fin_lab}')
print(f'clip: {len(clip)} bases with plan and A*; median plan/A* {plan_opt:.2f}, sweep/A* {sweep_opt:.2f}, '
      f'A*/lower bound {opt_lb:.2f}; locks needed median {need_med}, locks per base median {locks_med}')
print(f'label: {len(lab)} bases; median plan/A* {lab_plan_opt:.3f}')

B = R.Base(13, 0)
L4 = B.locks[4]
full_mask = (1 << len(B.locks)) - 1
every = set(B.bfs(B.ent, full_mask))
cut = every - set(B.bfs(B.ent, full_mask & ~(1 << 4))) - {L4['D']}
label = shown(L4['code'], 13)
print(f'Phoopel lock 4: D {L4["D"]} K {L4["K"]} W {L4["W"]} E {L4["E"]} code ${L4["code"]:04x} label {label}; '
      f'cells reachable {len(every)}, cut off {len(cut)}')
assert L4['K'] == L4['D'] and label == 15099 and L4['code'] == 0x8520

# ---------------- layout ----------------
y = 30
rect(30, y, W - 60, 150, PANEL, rx=6)
t(56, y + 70, 'KEYS YOU CAN ALWAYS REACH. ALMOST.', 46, INK, TITLE)
para(56, y + 108, ['Captive (Antony Crowther, Mindscape, 1990) builds every base from one number. Some doors are locked, and the',
                   'code is written on a clipboard somewhere in the base. One rule decides where the clipboard can go.'], 20, MUTED)
logo(W - 84, y + 58, 30)

# A: the rule, schematic
y = 200
h = 290
panel(y, h, 'A', 'Number the cells in the order they were dug', 'schematic, not a real base')
S, G = 52, 10
cells = [((0, 0), 1), ((1, 0), 2), ((2, 0), 3), ((3, 0), 4), ((3, 1), 5), ((3, 2), 6), ((4, 0), 7), ((5, 0), 8),
         ((6, 0), 9), ((7, 0), 10)]
ox, oy = 80, y + 80
for (cx, cy), n in cells:
    x, yy = ox + cx * (S + G), oy + cy * (S + G)
    if n == 7:
        flames(x, yy, S)
    else:
        rect(x, yy, S, S, GOLD if n < 7 else DIM, rx=3)
    t(x + S / 2, yy + S / 2 + 8, str(n), 24, BG if n < 7 else INK, TITLE, 'middle')
clipboard(ox + 3 * (S + G) + S + 14, oy + 2 * (S + G) + 6, 30)
t(ox + 3 * (S + G) + S + 54, oy + 2 * (S + G) + 32, 'key', 20, GOLD)
t(ox + 4 * (S + G) + S / 2, oy + S + 26, 'door', 20, RED, BODY, 'middle')
t(ox + 7 * (S + G) + S / 2, oy + S + 26, 'prize', 20, MUTED, BODY, 'middle')
logo(ox + S / 2, oy - 22, 14)
para(720, y + 100, ['The digger numbers each cell as it carves it.',
                    'A clipboard may only go on a cell numbered',
                    'no higher than its door.',
                    '',
                    'Everything dug before the door (gold) is on the',
                    'entrance side, so the key is never behind',
                    'the door it opens. (Panel C is the exception.)'], 21, INK)

# B: at scale
y = 510
h = 210
panel(y, h, 'B', 'It holds everywhere, and it never tangles', 'model census over 400 bases, mapgen.md')
big = [('8,617 / 8,617', 'keys dug no later than their door'),
       ('5,640', 'keys behind some other lock\'s door'),
       ('0 of 16,357', 'of those waits point to a later door')]
for i, (n, s) in enumerate(big):
    x = 70 + i * 370
    t(x, y + 128, n, 58, GOLD, TITLE)
    t(x, y + 165, s, 20, MUTED)
t(70, y + 196, 'So a player can always open the doors in the order they were dug, and never get stuck.', 20, INK)

# C: the slip, Phoopel
y = 740
h = 520
panel(y, h, 'C', 'The slip: "no higher than" includes the door', 'Phoopel (mission 2); version 1.0, from the model')
X0, X1, Y0, Y1 = 0, 24, 0, 15
cs = 21
mx, my = 70, y + 80
for yy in range(Y0, Y1):
    for xx in range(X0, X1):
        c = (xx, yy)
        if c not in B.adj:
            continue
        col = DIM if c in cut else STEEL
        rect(mx + (xx - X0) * cs, my + (yy - Y0) * cs, cs - 2, cs - 2, col, rx=2)
dx, dy = L4['D']
flames(mx + dx * cs - 1, my + dy * cs - 1, cs + 1)
clipboard(mx + dx * cs + 4, my + dy * cs - 22, 13)
wx, wy = L4['W']
rect(mx + wx * cs + cs - 7, my + wy * cs + 2, 6, cs - 6, GOLD, rx=1)
ex, ey = L4['E']
out.append(f'<circle cx="{mx + ex * cs + cs / 2 - 1}" cy="{my + ey * cs + cs / 2 - 1}" r="6" fill="{GOLD}"/>')
logo(mx + B.ent[0] * cs + cs / 2 - 1, my - 18, 13)
lx = mx + (X1 - X0) * cs + 40
para(lx, y + 100, [f'The door here is cell {dx},{dy}. Its clipboard',
                   'was placed on the door cell itself, and then',
                   'the wall of flames was built on top of it.',
                   '',
                   'Steel: reachable. Dark: cells only this door',
                   f'leads to ({len(cut)} of {len(every):,} in the whole base;',
                   'the top floor shown).',
                   'Gold bar: the switch panel. Gold disc: the prize.'], 20, INK)
t(lx, y + 352, f'{n_sealed} of {n_keyed:,}', 46, GOLD, TITLE)
t(lx, y + 382, 'keys in missions 1 to 100 are sealed this way', 20, MUTED)
t(lx, y + 440, f'{len(stuck)} of {n_bases:,}', 46, RED, TITLE)
t(lx, y + 470, 'bases cannot be finished without guessing a code', 20, MUTED)
t(lx, y + 496, '(up to 65,536 switch settings, one per click)', 18, MUTED)

# D: search
y = 1280
h = 400
panel(y, h, 'D', 'Where search helps: the walk, not the puzzle', f'{len(clip):,} mission bases')
para(70, y + 90, ['Can a base be finished? Opening a door only ever adds floor, so "open everything you can reach,',
                  'repeat" answers it exactly. No search. How short can the walk be? That is a search problem.'], 20, INK)
bars = [('Shortest walk (A* search)', 1.0, GOLD), ('Open the needed doors in dig order', plan_opt, STEEL),
        ('Open every door in dig order', sweep_opt, DIM)]
scale = 600 / max(b[1] for b in bars)
for i, (s, v, col) in enumerate(bars):
    by = y + 170 + i * 58
    t(70, by + 26, s, 21, INK)
    rect(440, by, v * scale, 36, col, rx=3)
    t(440 + v * scale + 12, by + 27, f'{v:.2f}x', 24, INK, TITLE)
para(70, y + 358, [f'Median over {len(clip):,} of the {n_fin_clip:,} finishable bases ({n_astar_limit} hit the search limit), as a multiple '
                   'of the shortest walk: entrance to a generator',
                   'and back, reading each clipboard on the way. A* chooses among the doors the route needs (median '
                   f'{need_med:g} of {locks_med:g} per base).'], 18, MUTED)

# E: the way past the slip
y = 1700
h = 180
panel(y, h, 'E', 'The code is printed on the panel', 'label formula proven 301/301; undoing it is arithmetic')
para(70, y + 90, ['The panel shows the same number as the clipboard: the code mixed with the base number by a scrambling',
                  'step that can be run backwards. Phoopel\'s panel reads 15099; undone, that is switch setting $8520,',
                  f'the one that opens the door in the emulator. With it, {n_fin_lab:,} of the {n_has_gen:,} bases can be finished (model).'], 20, INK)

# footer
y = 1910
para(40, y, ['Model: the generator ported to Python and checked against the game in an emulator (400 of 400 bases identical).',
             'Counts are from the model; Phoopel\'s door, clipboard, panel and code are checked in the emulator.',
             'Prior work: captive.atari.org (from 2007) documents the rule and this bug in Captive 1.0, fixed in 1.2 by a walk-through wall.',
             'Sources: mapgen.md "Locks and keys", "Sealed keys"; route.py; finish.py; panel13.py; keys.facts.md.'], 17, MUTED)

H = y + 4 * 17 * 1.3 + 30
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H:.0f}" viewBox="0 0 {W} {H:.0f}">'
       f'<rect width="100%" height="100%" fill="{BG}"/>' + ''.join(out) + '</svg>')
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, 'keys.svg'), 'w').write(svg)
print('wrote', os.path.join(OUT, 'keys.svg'))
