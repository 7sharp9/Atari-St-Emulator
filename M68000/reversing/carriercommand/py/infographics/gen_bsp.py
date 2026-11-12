#!/usr/bin/env python3
"""Infographic: BSP trees in 1988 (render.md sections 1, 4 and 6), drawn for the Manta, model 5.

usage: gen_bsp.py [outdir]   (default WORK/infographics; writes bsp.svg and prints every figure it draws)
Run from M68000/ with uv. Inputs:
  - the model: py/render/model.py's decode of model 5 (builder $a2d8 run by callcap from c_s30.snap), parsed into a
    tree by bsp_survey.py;
  - the frame in panel C: one draw of model 5 captured by bsp_order.py from manta/m_deck.snap with the Manta's angle
    words poked (WORK/infographics/bsp/order_deck_e000_2000.json, written by bsp_order_all.sh), whose vertices,
    plane flags, face results and polygon order are the game's own;
  - the check totals: bsp_order_sum.py over every order_*.json (bsp_order_all.sh).
Facts and sources: bsp.facts.md beside this script."""
import pathlib as _pl, sys as _sys, json, subprocess
_here = _pl.Path(__file__).resolve().parent
_sys.path.insert(0, str(_here.parent)); _sys.path.insert(0, str(_here.parent / 'render')); _sys.path.insert(0, str(_here))
from ccpaths import *
import model as M
from bsp_survey import tree, count
_sys.path.insert(0, str(ROOT / 'tools'))
from gfxview import load_video_regs

OUT = _pl.Path(_sys.argv[1]) if len(_sys.argv) > 1 else WORK / 'infographics'
OUT.mkdir(parents=True, exist_ok=True)
BSPDIR = WORK / 'infographics' / 'bsp'
FRAME = BSPDIR / 'order_deck_e000_2000.json'
FRAME_SNAP = WORK / 'manta' / 'm_deck.snap'
MID = 5

# ---- data: the model ----------------------------------------------------------------------------
addr = M.L(0x4c4ce + 4 * MID)
b = M.build(addr, (0, 0, 0)); m = M.parse(addr, b); T = tree(m); cnt = count(T)
VT = m['vt'][:m['nv']]
planes = m['planes']
# the model bytes in the frame's snapshot are the anchor's (the walk below reads the anchor RAM)
fram = ram(FRAME_SNAP)
lo, hi = addr, m['bsp'] + 0x100
assert fram[lo:hi] == M.RAM[lo:hi], 'model 5 differs between c_s30 and m_deck'

def cross_n(tri):
    v0, v1, v2 = (VT[i] for i in tri)
    e1 = [(a - c) >> 1 for a, c in zip(v1, v0)]; e2 = [(a - c) >> 1 for a, c in zip(v2, v0)]
    return (e1[1]*e2[2] - e1[2]*e2[1], e1[2]*e2[0] - e1[0]*e2[2], e1[0]*e2[1] - e1[1]*e2[0])
def side(pi, v):
    n = cross_n(planes[pi]); v0 = VT[planes[pi][0]]
    return sum(n[k] * (v[k] - v0[k]) for k in range(3))

# leaves in stream order, with their ancestors (plane, which subtree)
leaves = []
def collect(t, path):
    if t[0] == 'leaf': leaves.append(dict(addr=t[1], items=t[2], path=path)); return
    collect(t[2], path + [(t[1], 'A')]); collect(t[3], path + [(t[1], 'B')])
collect(T, [])
NAMES = ['nose', 'fin', 'deck and flanks', 'belly and wings']
for L, nm in zip(leaves, NAMES): L['name'] = nm
# every polygon vertex of a leaf lies on the side of each ancestor plane its subtree is (or on the plane)
side_check = []
for k, L in enumerate(leaves):
    for pi, ab in L['path']:
        vals = [side(pi, VT[i]) for it in L['items'] for _, idx, _ in it['polys'] for i in idx]
        side_check.append((k + 1, pi, ab, min(vals), max(vals)))
# plane geometry: all three normals have x = 0, so a side view shows each plane edge-on
normals = [cross_n(t) for t in planes]

# ---- data: the captured frame ---------------------------------------------------------------------
fr = [d for d in json.load(open(FRAME))['draws'] if d['model'] == MID][0]
assert fr['cmp']['same'], 'the captured draw does not match model.py'
fvt = fr['vt']; fc = fr['c']; fflags = fr['flags'][:3]
item_leaf = {}
for k, L in enumerate(leaves):
    for it in L['items']: item_leaf[it['addr']] = k
poly_info = {}
for L in leaves:
    for it in L['items']:
        for p, idx, col in it['polys']: poly_info[p] = (idx, col, it['addr'])
draw_seq = [a for a, _ in fr['polys']]
visit = []   # (item addr, leaf k, face value, [draw numbers])
for ia, fv in zip(fr['items'], fr['faces']):
    nums = [draw_seq.index(p) + 1 for p, _, _ in next(it for L in leaves for it in L['items'] if it['addr'] == ia)['polys'] if p in draw_seq]
    visit.append((ia, item_leaf[ia], fv, nums))
leaf_seq = []
for _, k, _, _ in visit:
    if not leaf_seq or leaf_seq[-1] != k: leaf_seq.append(k)
# game palette in the frame's snapshot, colour code -> two palette entries ($1544), dithers averaged
pw = load_video_regs(str(FRAME_SNAP))['palette_words']
PAL = [(((w >> 8) & 7) * 36, ((w >> 4) & 7) * 36, (w & 7) * 36) for w in pw]
CT = fram[0x1544:0x1544 + 128]
def colour(code):
    a_, b_ = PAL[CT[2 * code]], PAL[CT[2 * code + 1]]
    return '#%02x%02x%02x' % tuple((x + y) // 2 for x, y in zip(a_, b_)), CT[2 * code] != CT[2 * code + 1]

# ---- data: the check totals ---------------------------------------------------------------------
sumtxt = subprocess.run(['uv', 'run', 'python', '-I', str(_here / 'bsp_order_sum.py'), str(BSPDIR)],
                        capture_output=True, text=True, cwd=str(ROOT)).stdout
tot = eval(sumtxt.splitlines()[1])
per = eval(sumtxt.splitlines()[2].split(':', 1)[1])
nruns = int(sumtxt.splitlines()[0].split()[1])

print('model 5 at %x: nv %d, planes %s, %s' % (addr, m['nv'], planes, cnt))
print('normals', normals)
for k, L in enumerate(leaves):
    print('leaf L%d %s @%x: %d items, %d polygons, path %s' % (k + 1, L['name'], L['addr'], len(L['items']),
          sum(len(i['polys']) for i in L['items']), L['path']))
print('side check (leaf, plane, subtree, min, max):', side_check)
print('frame: step %d centre %s flags %s; leaf order %s; polygons drawn %d of %d; items culled %d of %d' % (
    fr['step'], fc, fflags, ['L%d' % (k + 1) for k in leaf_seq], len(draw_seq), cnt['polys'],
    sum(1 for v in fr['faces'] if v < 0), len(fr['faces'])))
print('check:', nruns, 'runs', tot, per)
print('stream bytes @%x:' % m['bsp'], M.RAM[m['bsp']:m['bsp'] + 12].hex(' '))

# ---- svg ----------------------------------------------------------------------------------------
W, H = 900, 1126
s = []
a = s.append
INK, MUTE, ACC, BAD, GRID = '#1f2328', '#656d76', '#0969da', '#cf222e', '#d0d7de'
LEAFC = ['#0969da', '#8250df', '#1a7f37', '#bc4c00']     # L1..L4
a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">')
a('<title id="t">BSP trees in 1988</title>')
a('<desc id="d">Carrier Command (1988) hides surfaces three ways: objects sorted by depth in a binary tree, each model '
  'a precompiled BSP tree walked far side first, and a back-face test per leaf item. Drawn for the Manta, model 5. '
  'Sources: reversing/carriercommand/render.md sections 1, 4 and 6; model decoded by py/render/model.py; the frame and '
  'the order check captured by py/infographics/bsp_order.py; figure by py/infographics/gen_bsp.py. Facts: bsp.facts.md.</desc>')
a('<style>text{font-family:Helvetica,Arial,sans-serif;fill:%s;font-size:12px}.t{font-size:20px;font-weight:bold}'
  '.h{font-size:14px;font-weight:bold}.m{fill:%s}.c{font-family:Menlo,monospace;font-size:11.5px}'
  '.s{font-size:11px;fill:%s}.w{fill:#fff;font-size:11px;font-weight:bold}</style>' % (INK, MUTE, MUTE))
a(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
a('<text x="24" y="38" class="t">BSP trees in 1988</text>')
a('<text x="24" y="60" class="m">Carrier Command (Realtime Games, 1988) has no z-buffer: every model carries a binary space '
  'partition tree, compiled into its data, that orders its faces.</text>')

def panel(x, y, w, h, title):
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="none" stroke="{GRID}"/>')
    a(f'<text x="{x+14}" y="{y+24}" class="h">{title}</text>')
def tag(x, y, text, col):
    wpx = 6.2 * len(text) + 10
    a(f'<rect x="{x}" y="{y-11}" width="{wpx:.0f}" height="15" rx="3" fill="{col}" fill-opacity="0.12" stroke="{col}" stroke-width="0.8"/>'
      f'<text x="{x+5}" y="{y}" style="font-size:10.5px;fill:{col}">{text}</text>')
    return wpx

# A: the model and its planes, side view -------------------------------------------------------
panel(24, 80, 430, 400, 'A. The Manta (model 5) and its three planes')
SX, SY, SC = 236, 282, 1.45       # side view: z to the right (nose), y up
def sv(v): return (SX + SC * v[2], SY - SC * v[1] * 1.6)   # y stretched 1.6x for legibility
# region tints (the four leaves' half-spaces), clipped to a box
zmin, zmax, ymin, ymax = -130, 125, -40, 55
def yP1(z): return (50 - z) / 15
def yP2(z): return 20 - (50 - z) / 15
def poly(pts, **kw):
    attrs = ' '.join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items())
    a('<polygon points="%s" %s/>' % (' '.join(f'{x:.1f},{y:.1f}' for x, y in pts), attrs))
poly([sv((0, ymin, 50)), sv((0, ymax, 50)), sv((0, ymax, zmax)), sv((0, ymin, zmax))], fill=LEAFC[0], fill_opacity='0.07')
poly([sv((0, ymax, zmin)), sv((0, ymax, 50)), sv((0, yP2(50), 50)), sv((0, yP2(-100), -100)), sv((0, yP1(zmin), zmin))], fill=LEAFC[1], fill_opacity='0.07')
poly([sv((0, yP2(50), 50)), sv((0, yP1(50), 50)), sv((0, yP1(-100), -100))], fill=LEAFC[2], fill_opacity='0.10')
poly([sv((0, ymin, zmin)), sv((0, yP1(zmin), zmin)), sv((0, yP1(50), 50)), sv((0, ymin, 50))], fill=LEAFC[3], fill_opacity='0.07')
# the model's polygons, side projection, outlined in their leaf's colour
for k, L in enumerate(leaves):
    for it in L['items']:
        for _, idx, _ in it['polys']:
            poly([sv(VT[i]) for i in idx], fill=LEAFC[k], fill_opacity='0.18', stroke=LEAFC[k], stroke_width='1', stroke_linejoin='round')
# planes, edge-on
def pl(p1, p2, name, lx, ly, anchor='start'):
    x1, y1 = sv(p1); x2, y2 = sv(p2)
    a(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{INK}" stroke-width="1.6" stroke-dasharray="6 3"/>')
    a(f'<text x="{lx}" y="{ly}" class="c" text-anchor="{anchor}" style="font-weight:bold">{name}</text>')
x0, _ = sv((0, 0, 50))
pl((0, ymin, 50), (0, ymax, 50), 'P0', x0 + 5, sv((0, ymax, 0))[1] + 12)
pl((0, yP1(zmin), zmin), (0, yP1(50), 50), 'P1', sv((0, 0, zmin))[0] + 2, sv((0, yP1(zmin), 0))[1] - 6)
pl((0, yP2(-100), -100), (0, yP2(50), 50), 'P2', sv((0, 0, 30))[0], sv((0, yP2(30), 0))[1] - 6, 'end')
for k, (z, y) in enumerate([(95, 40), (-55, 45), (-20, 7), (-40, -28)]):
    x, yy = sv((0, y, z))
    a(f'<text x="{x:.0f}" y="{yy:.0f}" text-anchor="middle" style="font-weight:bold;fill:{LEAFC[k]}">L{k+1}</text>')
# axes
ax, ay = sv((0, ymin, zmin))
a(f'<text x="{SX + SC*100:.0f}" y="{ay+16:.0f}" text-anchor="middle" class="s">nose, z = 100</text>')
a(f'<text x="{SX - SC*100:.0f}" y="{ay+16:.0f}" text-anchor="middle" class="s">tail, z = -100</text>')
a(f'<text x="38" y="{ay+38:.0f}" class="s">Side view (y stretched 1.6x). Every plane contains the x direction,</text>')
a(f'<text x="38" y="{ay+52:.0f}" class="s">so all three are edge-on here: P0 is z = 50, P1 rises 10 in 150</text>')
a(f'<text x="38" y="{ay+66:.0f}" class="s">toward the tail, P2 is the deck. Each plane is three of the</text>')
a(f'<text x="38" y="{ay+80:.0f}" class="s">model\'s own vertices ({", ".join("(%d,%d,%d)" % t for t in planes)}).</text>')
a(f'<text x="38" y="124" class="s">{m["nv"]} vertices from a box builder, {cnt["polys"]} polygons in {cnt["leaves"]} leaves; a leaf</text>')
a(f'<text x="38" y="138" class="s">is the set of faces in one cell of the planes.</text>')

# B: the tree --------------------------------------------------------------------------------------
panel(466, 80, 410, 400, 'B. The tree, as bytes in the model')
def nodebox(x, y, label):
    a(f'<rect x="{x-24}" y="{y-13}" width="48" height="24" rx="12" fill="#f6f8fa" stroke="{INK}"/>'
      f'<text x="{x}" y="{y+4}" text-anchor="middle" class="c" style="font-weight:bold">{label}</text>')
def leafbox(x, y, k):
    L = leaves[k]; npol = sum(len(i['polys']) for i in L['items'])
    a(f'<rect x="{x-56}" y="{y-14}" width="112" height="40" rx="4" fill="{LEAFC[k]}" fill-opacity="0.12" stroke="{LEAFC[k]}"/>')
    a(f'<text x="{x}" y="{y+1}" text-anchor="middle" style="font-weight:bold;fill:{LEAFC[k]}">L{k+1} {L["name"] if len(L["name"]) < 10 else ""}</text>')
    if len(L['name']) >= 10:
        a(f'<text x="{x}" y="{y+1}" text-anchor="middle" style="font-weight:bold;fill:{LEAFC[k]}"></text>')
    a(f'<text x="{x}" y="{y+16}" text-anchor="middle" class="s">{len(L["items"])} items, {npol} polygons</text>')
def edge(x1, y1, x2, y2, lab):
    a(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{MUTE}"/>')
    a(f'<text x="{(x1+x2)/2 + (-9 if x2 < x1 else 5):.0f}" y="{(y1+y2)/2 - 2:.0f}" class="s" text-anchor="{"end" if x2 < x1 else "start"}">{lab}</text>')
n0 = (640, 128); n1 = (720, 190); n2 = (650, 252)
lp = [(550, 190), (584, 318), (712, 318), (806, 256)]
edge(*n0, lp[0][0], lp[0][1] - 14, 'A'); edge(*n0, *n1, 'B')
edge(*n1, *n2, 'A'); edge(*n1, lp[3][0], lp[3][1] - 14, 'B')
edge(*n2, lp[1][0], lp[1][1] - 14, 'A'); edge(*n2, lp[2][0], lp[2][1] - 14, 'B')
nodebox(*n0, 'P0'); nodebox(*n1, 'P1'); nodebox(*n2, 'P2')
for k in range(4): leafbox(*lp[k], k)
# names for the two-word leaves under their boxes
by = 368
a(f'<text x="480" y="{by}" class="s">L3: deck and flanks; L4: belly and wings.</text>')
a(f'<text x="480" y="{by+22}" class="c">node: [plane][offset.w][A ...][B ...]</text>')
a(f'<text x="480" y="{by+38}" class="c">leaf: [$ff][count][items ...]</text>')
a(f'<text x="480" y="{by+54}" class="s">B starts at A + offset. Stream at ${m["bsp"]:x}: {M.RAM[m["bsp"]:m["bsp"]+6].hex(" ")} ...</text>')
a(f'<text x="480" y="{by+76}" class="s">The side flag of a plane is $ff when the eye is on its positive</text>')
a(f'<text x="480" y="{by+90}" class="s">side: then A is drawn before B, otherwise B before A ($8e8c).</text>')

# C: one frame -------------------------------------------------------------------------------------
cy0 = 494
panel(24, cy0, 852, 356, 'C. One frame: the walk the game made, matched by the model')
# render: project the captured view-space vertices with the game's divide, scaled to the box
def gp(v):
    X = v[0] + fc[0]; Y = -v[1] - fc[1]; Z = v[2] + fc[2]
    return (X * 256 / Z, Y * 256 / Z)
pts_all = [gp(fvt[i]) for p in draw_seq for i in poly_info[p][0]]
minx = min(p[0] for p in pts_all); maxx = max(p[0] for p in pts_all)
miny = min(p[1] for p in pts_all); maxy = max(p[1] for p in pts_all)
bx, byy, bw, bh = 44, cy0 + 44, 330, 250
sc = min(bw / (maxx - minx), bh / (maxy - miny))
def rp(v):
    x, y = gp(v); return (bx + (x - minx) * sc + (bw - (maxx - minx) * sc) / 2, byy + (y - miny) * sc + (bh - (maxy - miny) * sc) / 2)
a(f'<rect x="{bx-6}" y="{byy-6}" width="{bw+12}" height="{bh+12}" fill="#f6f8fa" stroke="none"/>')
centres = []
for n, p in enumerate(draw_seq, 1):
    idx, col, _ = poly_info[p]; rgb, dith = colour(col)
    pts = [rp(fvt[i]) for i in idx]
    poly(pts, fill=rgb, stroke='#ffffff', stroke_width='0.8', stroke_linejoin='round')
    centres.append((n, sum(x for x, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts)))
for n, x, y in centres:
    k = item_leaf[poly_info[draw_seq[n - 1]][2]]
    a(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" fill="{LEAFC[k]}" stroke="#fff"/>'
      f'<text x="{x:.1f}" y="{y+3.8:.1f}" text-anchor="middle" class="w" style="font-size:10px">{n}</text>')
a(f'<text x="{bx}" y="{byy+bh+24}" class="s">Polygons in the order the game filled them (game colours, dithers</text>')
a(f'<text x="{bx}" y="{byy+bh+38}" class="s">averaged), from its own view-space vertices. m_deck.snap with the</text>')
a(f'<text x="{bx}" y="{byy+bh+52}" class="s">Manta\'s angle words poked to $e000 / $2000 to turn it.</text>')
# the walk
wx = 404
for j, (pn, fl) in enumerate(zip(('P0', 'P1', 'P2'), fflags)):
    a(f'<text x="{wx + 150*j}" y="{cy0+50}" class="c">{pn} ${fl:02x}: {"A, B" if fl == 0xff else "B, A"}</text>')
a(f'<text x="{wx}" y="{cy0+68}" class="s">side flags computed by $940a from this frame\'s vertices</text>')
yy = cy0 + 96
cw = 23
for k in leaf_seq:
    its = [v for v in visit if v[1] == k]
    a(f'<text x="{wx}" y="{yy+4}" style="font-weight:bold;fill:{LEAFC[k]}">L{k+1}</text>')
    a(f'<text x="{wx+24}" y="{yy+4}" class="s">{leaves[k]["name"]}</text>')
    x = wx + 128
    for ia, kk, fv, nums in its:
        if fv < 0:
            a(f'<rect x="{x}" y="{yy-9}" width="{cw-3}" height="18" rx="3" fill="none" stroke="{GRID}"/>'
              f'<line x1="{x+5}" y1="{yy+4}" x2="{x+cw-8}" y2="{yy-4}" stroke="{BAD}" stroke-width="1.3"/>')
            x += cw
        else:
            wd = cw * len(nums)
            a(f'<rect x="{x}" y="{yy-9}" width="{wd-3}" height="18" rx="3" fill="{LEAFC[k]}"/>'
              f'<text x="{x + (wd-3)/2:.1f}" y="{yy+4}" text-anchor="middle" class="w">{" ".join(str(n) for n in nums)}</text>')
            x += wd
    yy += 34
a(f'<text x="{wx}" y="{yy+4}" class="s">One cell per leaf item, in the order the walk met them. Filled: the</text>')
a(f'<text x="{wx}" y="{yy+18}" class="s">item faces the eye and its polygons are drawn (numbers as on the left).</text>')
a(f'<text x="{wx}" y="{yy+32}" class="s"><tspan style="fill:{BAD};font-weight:bold">Struck</tspan>: the back-face test returned a negative and the item is</text>')
a(f'<text x="{wx}" y="{yy+46}" class="s">skipped: {sum(1 for v in fr["faces"] if v < 0)} of {len(fr["faces"])} here, so {len(draw_seq)} of {cnt["polys"]} polygons are filled.</text>')
a(f'<text x="{wx}" y="{yy+68}" class="s">The far cells come first: the nose (seen from behind P0), then</text>')
a(f'<text x="{wx}" y="{yy+82}" class="s">the belly, the deck, and the fin last, on top of the deck.</text>')
a(f'<text x="{wx}" y="{yy+104}" class="s">model.py\'s walk on the same vertices gives the same {len(fr["items"])} items, face signs</text>')
a(f'<text x="{wx}" y="{yy+118}" class="s">and {len(draw_seq)} polygons in the same order (panel E, row 2).</text>')

# D: back-face test ---------------------------------------------------------------------------------
dy0 = cy0 + 370
panel(24, dy0, 420, 248, 'D. The test in each leaf item ($9426)')
ox, oy = 92, dy0 + 150
v0 = (ox, oy); v1 = (ox + 120, oy + 14); v2 = (ox + 54, oy - 40)
poly([v0, v1, v2], fill=ACC, fill_opacity='0.15', stroke=ACC)
for (x, y), lab, dx in ((v0, 'v0', -22), (v1, 'v1', 6), (v2, 'v2', 6)):
    a(f'<circle cx="{x}" cy="{y}" r="2.5" fill="{INK}"/><text x="{x+dx}" y="{y+4}" class="s">{lab}</text>')
a(f'<line x1="{ox+56}" y1="{oy-6}" x2="{ox+56}" y2="{oy-84}" stroke="{ACC}" stroke-width="2"/>'
  f'<polygon points="{ox+56},{oy-90} {ox+52},{oy-80} {ox+60},{oy-80}" fill="{ACC}"/>'
  f'<text x="{ox+62}" y="{oy-76}" class="s" style="fill:{ACC}">n</text>')
ex, ey = ox + 150, oy - 108
a(f'<line x1="{ox}" y1="{oy}" x2="{ex}" y2="{ey}" stroke="{INK}" stroke-dasharray="4 3"/>'
  f'<circle cx="{ex}" cy="{ey}" r="4" fill="{INK}"/><text x="{ex-8}" y="{ey+4}" text-anchor="end" class="s">eye (origin)</text>'
  f'<text x="{ox+102}" y="{oy-60}" class="s">d</text>')
tx = 258
a(f'<text x="{tx}" y="{dy0+60}" class="c">n = (v1-v0)/2 x (v2-v0)/2</text>')
a(f'<text x="{tx}" y="{dy0+78}" class="c">d = eye - v0</text>')
a(f'<text x="{tx}" y="{dy0+96}" class="c">skip if d . n &lt; 0</text>')
a(f'<text x="{tx}" y="{dy0+118}" class="s">both vectors halved until</text>')
a(f'<text x="{tx}" y="{dy0+132}" class="s">they fit 16 bits</text>')
a(f'<text x="38" y="{dy0+196}" class="s">The same test, on a plane\'s three vertices, gives the side flags</text>')
a(f'<text x="38" y="{dy0+210}" class="s">that steer the walk: $940a stores $ff when it is not negative.</text>')
a(f'<text x="38" y="{dy0+230}" class="s">Three vertex indices per item: no normals are stored.</text>')

# E: three layers and the evidence ------------------------------------------------------------------
panel(456, dy0, 420, 248, 'E. Three layers, and how far each is proven')
ey0 = dy0 + 54
rows = [
    ('1', 'Objects: depth-sorted into a binary tree of', '18-byte nodes at $5a82a (128 max), drawn far', 'to near by $5d94.', ('from code', MUTE)),
    ('2', 'Models: the BSP walk $8e8c, far side first.', f'{tot["draws"]} draws of {len(per)} models: every item, face', f'sign and polygon in the same order as model.py.', ('matched in the emulator', '#1a7f37')),
    ('3', 'Faces: the back-face test $9426.', '120 of 120 callcap cases against the model.', '', ('proven', '#1a7f37')),
]
for n, l1, l2, l3, (tg, tc) in rows:
    a(f'<circle cx="478" cy="{ey0-4}" r="9" fill="{ACC}"/><text x="474.5" y="{ey0}" style="fill:#fff;font-size:11px;font-weight:bold">{n}</text>')
    a(f'<text x="494" y="{ey0}">{l1}</text>')
    a(f'<text x="494" y="{ey0+15}" class="s">{l2}</text>')
    if l3: a(f'<text x="494" y="{ey0+29}" class="s">{l3}</text>')
    tag(494, ey0 + (46 if l3 else 32), tg, tc)
    ey0 += 64 if l3 else 50
a('</svg>')
(OUT / 'bsp.svg').write_text('\n'.join(s))
print('wrote', OUT / 'bsp.svg')
