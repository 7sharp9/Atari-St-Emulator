#!/usr/bin/env python3
"""Infographic: packets that route themselves (economy.md sections 1, 3 and 4), from a port of the routing code.

usage: gen_routing.py [drive] [outdir]   (default outdir WORK/infographics; writes routing.svg)

The port below reimplements, from the disassembly:
  $21f9e  edge enable by owner          $21e16  matrix reset ($ffff, diagonal 0)
  $21e8a  relax 8 rows per call         $22192  next hop for a packet
  $1817e  the stray write of 500 into the matrix at row 63, column 4 (see routing.facts.md, Flags)
The island graph, owners and positions are read from the anchor snapshot c_s30.

`drive` runs the emulator from c_s30 (4 runs, about 5 minutes) and saves its logs under
<outdir>/routing_drive/; without it the figure is drawn from the saved logs. Each run pokes a state
(owners, edge bits, a reset matrix, the relaxation pointers and flags, a packet) and records either the
matrix before every call of $21e8a or every write to one pool-2 packet; the port is checked against both.
Facts and sources: routing.facts.md beside this script."""
import pathlib as _pl, sys as _sys
_here = _pl.Path(__file__).resolve().parent
_sys.path.insert(0, str(_here.parent))
from ccpaths import *
import os, re, struct, subprocess, statistics

args = [x for x in _sys.argv[1:] if x != 'drive']
DRIVE = 'drive' in _sys.argv[1:]
OUT = _pl.Path(args[0]) if args else WORK / 'infographics'
OUT.mkdir(parents=True, exist_ok=True)
LOGS = OUT / 'routing_drive'
LOGS.mkdir(exist_ok=True)

R = ram(ANCHOR)
def W16(b, a): return struct.unpack('>H', b[a:a + 2])[0]
def L32(b, a): return struct.unpack('>I', b[a:a + 4])[0]

# ---- data from the snapshot ---------------------------------------------------------------------
t = 0x4d184
NAMES = [R[t + o:R.index(b'\0', t + o)].decode() for o in struct.unpack('>64H', R[t:t + 128])]
ISL = [struct.unpack('>4h', R[0x4d41a + 22 * k:0x4d41a + 22 * k + 8]) for k in range(64)]    # x, y, w, h
OWN0 = list(R[0x69b40:0x69b80])
ADJ = []                                   # per island: (cost, neighbour word) as stored, bit 15 = disabled
for k in range(64):
    b = 0x22afa + 32 * k
    ADJ.append([struct.unpack('>HH', R[b + 2 + 4 * j:b + 6 + 4 * j]) for j in range(W16(R, b))])

# ---- the port -----------------------------------------------------------------------------------
def enable(own):
    """$21f9e: a free island's edges are all off; otherwise an edge is on when both ends have the same owner."""
    out = []
    for k in range(64):
        row = []
        for c, nb in ADJ[k]:
            j = nb & 0x3fff
            on = False if own[k] == 0 else (own[j] == 1 if own[k] == 1 else own[j] not in (0, 1))
            row.append((c, j, on))
        out.append(row)
    return out

class Net:
    def __init__(s, own):
        s.E = enable(own)                                  # $21e16 calls $21f9e first
        s.M = [[0xffff] * 64 for _ in range(64)]           # $21e16: $67b40..$69b3f = $ffff, diagonal 0
        for i in range(64): s.M[i][i] = 0
        s.busy = True; s.clean = True; s.left = 7; s.row = 0; s.calls = 0   # $122f, $122e, $df0, $de8
    def call(s):
        """$21e8a: rows row..row+7; M[i][k] = min(M[i][k], M[j][k] + c) over enabled edges, in place."""
        s.calls += 1
        for i in range(s.row, s.row + 8):
            Mi = s.M[i]
            for c, j, on in s.E[i]:
                if not on: continue
                Mj = s.M[j]
                for k in range(64):
                    d = Mj[k]
                    if d & 0x8000: continue                   # bmi: unreachable
                    d = (d + c) & 0xffff
                    if Mi[k] > d: Mi[k] = d; s.clean = False  # bls (unsigned), sf $122e
        if s.left: s.left -= 1; s.row += 8                 # dbf $df0
        elif not s.clean: s.left = 7; s.row = 0; s.clean = True   # a sweep changed something: sweep again
        else: s.busy = False                               # a whole sweep changed nothing: sf $122f
    def hop(s, u, t):
        """$22192: among enabled neighbours strictly closer to t than u, the one minimising M[j][t] + c."""
        if s.M[u][t] & 0x8000: return -1, None
        best, h, cc = 0xffff, -1, None
        for c, j, on in s.E[u]:
            if not on: continue
            d = s.M[j][t]
            if d >= s.M[u][t]: continue
            d = (d + c) & 0xffff
            if d >= best: continue
            best, h, cc = d, j, c
        return h, cc
    def route(s, u, t):
        p = [(u, 0)]
        while u != t:
            u, c = s.hop(u, t)
            if u < 0: return p + [(-1, 0)]
            p.append((u, c))
        return p

def converged(own):
    n = Net(own); n.M[63][4] = 500          # $1817e, see Flags
    while n.busy: n.call()
    return n

# ---- the states drawn ---------------------------------------------------------------------------
LATE = [1 if o == 0 else o for o in OWN0]   # hypothetical: every free island of c_s30 given to the player
SRC, DST, CUT = 46, 0, 28                   # OBSIDIAN -> VULCAN; STAVROS freed for the second route
LATE_CUT = list(LATE); LATE_CUT[CUT] = 0
SLOT = 0x66710 + 199 * 6                    # last pool-2 slot (free in c_s30)

# ---- emulator drives ----------------------------------------------------------------------------
def pokes(own, packet=None):
    L = []
    def wl(a, v): L.append('w %x %08x' % (a, v))
    if own != OWN0:
        for a in range(0x69b40, 0x69b80, 4): wl(a, L32(bytes(own), a - 0x69b40))
        E = enable(own)
        for k in range(64):
            for j, (c, nb) in enumerate(ADJ[k]):
                wl(0x22afa + 32 * k + 2 + 4 * j, (c << 16) | (nb & 0x3fff) | (0 if E[k][j][2] else 0x8000))
    for i in range(64):                      # what $21e16 does, as pokes
        for k in range(0, 64, 2):
            wl(0x67b40 + 128 * i + 2 * k, ((0 if i == k else 0xffff) << 16) | (0 if i == k + 1 else 0xffff))
    wl(0x122c, (L32(R, 0x122c) & 0xffff0000) | 0xffff)          # $122e, $122f set
    wl(0xdf0, (7 << 16) | (L32(R, 0xdf0) & 0xffff))
    wl(0xde8, 0x67b40); wl(0xdec, 0x22afa)
    if packet:
        node, dest = packet                  # node, timer 1, item $12, quantity 1, destination word
        assert R[SLOT] == 0xff
        wl(SLOT, (node << 24) | 0x011201); wl(SLOT + 4, (dest << 16) | W16(R, SLOT + 6))
    return L

def run(name, lines):
    out = subprocess.run(['dotnet', 'exec', str(DLL), 'resume', str(ANCHOR), 'repl'], cwd=str(ROOT),
                         input='\n'.join(lines + ['m 69b40 64', 'q']) + '\n', stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, env={**os.environ, 'ATARI_NOTRACE': '1'})
    (LOGS / f'{name}.txt').write_text(out.stdout)
    print('drive', name, 'exit', out.returncode, len(out.stdout.splitlines()), 'lines')

def drive_fill(name, own, K):
    L = pokes(own) + ['watch 69ac8 2']
    for _ in range(K): L += ['u 21e8a 3000000', 'm 67b40 8192', 'm 122c 4', 's 1']
    run(name, L)

def drive_route(name, own, src, dst, budget):
    run(name, pokes(own, (src, dst)) + ['watch %x 6' % SLOT, 's %d' % budget, 'm %x 6' % SLOT])

if DRIVE:
    drive_fill('fill_c_s30', OWN0, converged(OWN0).calls + 16)
    drive_fill('fill_late', LATE, converged(LATE).calls + 16)
    for name, own in (('route_late', LATE), ('route_cut', LATE_CUT)):
        cost = sum(c for _, c in converged(own).route(SRC, DST))
        drive_route(name, own, SRC, DST, (cost + 40) * 2_500_000)

# ---- checks against the logs --------------------------------------------------------------------
def check_fill(name, own):
    """Compare the dumped matrix before each $21e8a call with the port; inject $1817e's write where the watch saw it."""
    p = LOGS / f'{name}.txt'
    if not p.exists(): return None
    dumps, flags, watch_at, gaps = [], [], [], []
    for l in p.read_text().splitlines():
        n = len(l.split())
        if n == 8192: dumps.append(bytes.fromhex(l.replace(' ', '')))
        elif n == 4 and not l.startswith('---'): flags.append(bytes.fromhex(l.replace(' ', '')))
        elif l.startswith('WATCH:'): watch_at.append(len(dumps))
        m = re.match(r'--- reached PC=\$00021e8a after (\d+) step', l)
        if m: gaps.append(int(m[1]))
    net = Net(own); hist = []; cells = 0; ok = 0; flag_ok = 0
    for n, (d, f) in enumerate(zip(dumps, flags)):
        M = [[W16(d, 128 * i + 2 * k) for k in range(64)] for i in range(64)]
        eq = sum(M[i][k] == net.M[i][k] for i in range(64) for k in range(64))
        cells += eq; ok += eq == 4096
        flag_ok += (f[3] != 0) == net.busy and (f[2] != 0) == net.clean
        hist.append([row[:] for row in net.M])
        if not net.busy: break
        net.call()
        if watch_at and n + 1 == watch_at[0]: net.M[63][4] = 500
    return dict(dumps=len(hist), all_equal=ok, cells=cells, flags=flag_ok, calls=net.calls, busy=net.busy,
                watch_first=watch_at[0] if watch_at else None, gaps=gaps[1:], hist=hist)

def check_route(name, own):
    p = LOGS / f'{name}.txt'
    if not p.exists(): return None
    hops, ticks, cur, landed = [], [], 0, None
    for l in p.read_text().splitlines():
        m = re.match(r'WATCH: step=(\d+) pc=\$(\w+) Write(\w+) \$(\w+) <- \$(\w+)', l)
        if not m: continue
        pc, a, v = int(m[2], 16), int(m[4], 16), int(m[5], 16)
        if pc == 0x2240e: landed = int(m[1])
        if a == SLOT and pc == 0x223fa: hops.append([v, None]); ticks.append(cur); cur = 0
        if a == SLOT + 1 and pc == 0x223fe: hops[-1][1] = v
        if a == SLOT + 1 and pc == 0x223b2: cur += 1
    ticks = ticks[1:] + [cur]       # decrements counted after each hop until the next decision
    port = converged(own).route(SRC, DST)
    want = [[u, c] for u, c in port[1:]]
    return dict(hops=hops, want=want, match=sum(a == b for a, b in zip(hops, want)), n=len(want),
                landed=landed is not None, dwell_ok=sum(t == c for t, (_, c) in zip(ticks, hops)), ticks=ticks)

F0, FL = check_fill('fill_c_s30', OWN0), check_fill('fill_late', LATE)
RL, RC = check_route('route_late', LATE), check_route('route_cut', LATE_CUT)

NL, NC = converged(LATE), converged(LATE_CUT)
PATH, PATH_CUT = NL.route(SRC, DST), NC.route(SRC, DST)
COST, COST_CUT = sum(c for _, c in PATH), sum(c for _, c in PATH_CUT)
snapM = [[W16(R, 0x67b40 + 128 * i + 2 * k) for k in range(64)] for i in range(64)]
N0 = converged(OWN0)
snap_eq = sum(N0.M[i][k] == snapM[i][k] for i in range(64) for k in range(64))
deg = [len(a) for a in ADJ]
oneway = [(k, nb & 0x3fff) for k in range(64) for c, nb in ADJ[k]
          if not any((n2 & 0x3fff) == k for _, n2 in ADJ[nb & 0x3fff])]
cut5 = converged([0 if k == 5 else o for k, o in enumerate(LATE)])
iso5 = sum(1 for k in range(64) if LATE[k] == 1 and k != 5 and cut5.M[k][0] & 0x8000) - 1   # minus 51

print('c_s30 matrix: port %d/4096 equal to the snapshot (port converges in %d calls)' % (snap_eq, N0.calls))
for nm, F in (('fill_c_s30', F0), ('fill_late', FL)):
    if F: print('%s: %d dumps, %d all-4096, %d cells, flags %d, port calls %d (busy %s), $1817e first before dump %s, '
                'steps between calls median %d' % (nm, F['dumps'], F['all_equal'], F['cells'], F['flags'], F['calls'],
                F['busy'], F['watch_first'], statistics.median(F['gaps'])))
for nm, Rr in (('route_late', RL), ('route_cut', RC)):
    if Rr: print('%s: hops %d/%d match, landed %s, dwell = cost %d/%d' % (nm, Rr['match'], Rr['n'], Rr['landed'], Rr['dwell_ok'], len(Rr['hops'])))
print('route', [u for u, _ in PATH], COST, 'hops', len(PATH) - 1, '| cut', CUT, [u for u, _ in PATH_CUT], COST_CUT, 'hops', len(PATH_CUT) - 1)
print('degrees', {d: deg.count(d) for d in sorted(set(deg))}, 'one-way', oneway, 'cost range', min(c for a in ADJ for c, _ in a), max(c for a in ADJ for c, _ in a))
print('late state: player islands', LATE.count(1), '; freeing DUESSA (5) cuts', iso5, 'more islands off VULCAN')

# convergence series for panel B (late state, port; the drive checked it call by call)
hist = FL['hist'] if FL else None
if hist is None:
    n = Net(LATE); n.M[63][4] = 500; hist = [[r[:] for r in n.M]]
    while n.busy: n.call(); hist.append([r[:] for r in n.M])
final = hist[-1]
fin_series = [sum(v < 0x8000 for r in M for v in r) for M in hist]
done_series = [sum(M[i][k] == final[i][k] for i in range(64) for k in range(64) if final[i][k] < 0x8000) for M in hist]
last_change = max(i for i in range(1, len(hist)) if hist[i] != hist[i - 1])
CALLS = len(hist) - 1
FIN = fin_series[-1]
print('late: %d calls, last change at call %d, finite entries %d' % (CALLS, last_change, FIN))

# ---- svg ----------------------------------------------------------------------------------------
W, H = 900, 1356
s = []
a = s.append
INK, MUTE, ACC, BAD, GRID, ENEMY, ALT = '#1f2328', '#656d76', '#0969da', '#cf222e', '#d0d7de', '#cf222e', '#bf8700'
a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">')
a('<title id="t">Packets that route themselves</title>')
a('<desc id="d">Carrier Command (1988) keeps a 64 x 64 all-pairs distance matrix over its island graph, relaxed 8 rows '
  'per main-loop pass; each goods packet takes its next hop from it. Source: reversing/carriercommand/economy.md '
  'sections 1, 3 and 4 and the code at $21e16, $21e8a, $21f9e, $22192; graph from c_s30.snap; computed by '
  'py/infographics/gen_routing.py and checked against emulator runs. Facts: routing.facts.md.</desc>')
a('<style>text{font-family:Helvetica,Arial,sans-serif;fill:%s;font-size:12px}.t{font-size:20px;font-weight:bold}'
  '.h{font-size:14px;font-weight:bold}.m{fill:%s}.c{font-family:Menlo,monospace;font-size:11.5px}'
  '.s{font-size:11px;fill:%s}.n{font-size:9px;fill:%s}</style>' % (INK, MUTE, MUTE, MUTE))
a(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
a('<text x="24" y="38" class="t">Packets that route themselves</text>')
a('<text x="24" y="60" class="m">Carrier Command (Realtime Games, 1988): goods cross the archipelago hop by hop, '
  'each hop read from a distance table the game keeps relaxing.</text>')

def panel(x, y, w, h, title):
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="none" stroke="{GRID}"/>')
    a(f'<text x="{x+14}" y="{y+24}" class="h">{title}</text>')

# A: the map -------------------------------------------------------------------------------------
PA_Y, PA_H = 80, 520
panel(24, PA_Y, 852, PA_H, 'A. The island graph and one packet\'s route (hypothetical ownership)')
a(f'<text x="38" y="{PA_Y+42}" class="s">c_s30\'s 64 islands and 84 links; every island that is free in c_s30 given to the player. '
  'Link labels are the edge cost, which is also the hop\'s time in economy ticks.</text>')
xs = [i[0] for i in ISL]; ys = [i[1] for i in ISL]
mx0, my0, mw, mh = 70, PA_Y + 66, 600, 380
sc = min(mw / (max(xs) - min(xs)), mh / (max(ys) - min(ys)))
def P(k): return (mx0 + (xs[k] - min(xs)) * sc, my0 + (max(ys) - ys[k]) * sc)
E = enable(LATE); EC = enable(LATE_CUT)
drawn = set()
for k in range(64):
    for c, j, on in E[k]:
        key = (min(k, j), max(k, j))
        if key in drawn: continue
        drawn.add(key)
        (x1, y1), (x2, y2) = P(k), P(j)
        st = f'stroke="{GRID}" stroke-width="1.2"' if on else f'stroke="{GRID}" stroke-width="1" stroke-dasharray="3 3"'
        a(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" {st}/>')
NLINKS = len(drawn)
def draw_path(p, col, dash, w):
    pts = ' '.join('%.1f,%.1f' % P(u) for u, _ in p)
    a(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round"{dash}/>')
draw_path(PATH_CUT, ALT, ' stroke-dasharray="6 4"', 2.4)
draw_path(PATH, ACC, '', 3)
on_path = {u for u, _ in PATH} | {u for u, _ in PATH_CUT}
for p, col in ((PATH, ACC), (PATH_CUT, ALT)):
    for (u, _), (v, c) in zip(p, p[1:]):
        if (u, v) in [(x, y) for (x, _), (y, _) in zip(PATH, PATH[1:])] and col == ALT: continue
        (x1, y1), (x2, y2) = P(u), P(v)
        ln = max(1.0, ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5)
        nx, ny = -(y2 - y1) / ln, (x2 - x1) / ln
        if nx < 0: nx, ny = -nx, -ny                  # put labels on the right-hand side of the line
        mxp, myp = (x1 + x2) / 2 + 8 * nx, (y1 + y2) / 2 + 8 * ny
        a(f'<text x="{mxp:.1f}" y="{myp+3:.1f}" text-anchor="middle" class="n" style="fill:{col}">{c}</text>')
for k in range(64):
    x, y = P(k)
    if LATE[k] == 2: fill, rr = ENEMY, 4.5
    elif k == CUT: fill, rr = '#ffffff', 5
    else: fill, rr = (ACC if k in on_path else '#8c959f'), (4.5 if k in on_path else 3.2)
    stroke = f' stroke="{ALT}" stroke-width="2"' if k == CUT else ''
    a(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr}" fill="{fill}"{stroke}/>')
LBL = {SRC: (8, 4, 'start'), DST: (8, 4, 'start'), CUT: (-10, -6, 'end'), 63: (8, 4, 'start'), 38: (-8, 4, 'end'), 5: (-8, -8, 'end')}
for k, (dx, dy, anc) in LBL.items():
    x, y = P(k)
    a(f'<text x="{x+dx:.1f}" y="{y+dy:.1f}" text-anchor="{anc}" class="s" style="fill:{INK}">{NAMES[k]} {k}</text>')
# legend and route text, right of the map
lx, ly = 690, PA_Y + 92
def leg_line(y, col, dash, txt, w=3):
    a(f'<line x1="{lx}" y1="{y-4}" x2="{lx+22}" y2="{y-4}" stroke="{col}" stroke-width="{w}"{dash}/>')
    a(f'<text x="{lx+30}" y="{y}" class="s">{txt}</text>')
leg_line(ly, ACC, '', 'the route')
leg_line(ly + 18, ALT, ' stroke-dasharray="6 4"', f'with {NAMES[CUT]} free', 2.4)
leg_line(ly + 36, GRID, '', 'link on', 1.2)
leg_line(ly + 54, GRID, ' stroke-dasharray="3 3"', 'link off (owners differ)', 1)
a(f'<circle cx="{lx+11}" cy="{ly+68}" r="4.5" fill="{ENEMY}"/><text x="{lx+30}" y="{ly+72}" class="s">enemy (as in c_s30)</text>')
a(f'<circle cx="{lx+11}" cy="{ly+86}" r="3.2" fill="#8c959f"/><text x="{lx+30}" y="{ly+90}" class="s">player</text>')
ty = ly + 126
for line in (f'{NAMES[SRC]} to {NAMES[DST]}:', f'{len(PATH)-1} hops, cost {COST}.', '',
             f'Free {NAMES[CUT]} and its links', 'go off; after the matrix is', 'rebuilt the packet detours',
             f'by the dashed line: {len(PATH_CUT)-1} hops,', f'cost {COST_CUT}.', '',
             'Free DUESSA 5 instead and', f'{iso5} player islands lose', 'every route to VULCAN.'):
    a(f'<text x="{lx}" y="{ty}" class="s">{line}</text>'); ty += 15
if RL and RC:
    chk = (f'Emulator, packet poked at {NAMES[SRC]}: hop by hop it took the port\'s route, {RL["match"]}/{RL["n"]} hops, '
           f'and the detour, {RC["match"]}/{RC["n"]}; each hop\'s timer was the edge cost and the packet landed.')
else:
    chk = 'Routes computed by the port (emulator drive not run).'
a(f'<text x="38" y="{PA_Y+PA_H-36}" class="s">{chk}</text>')
a(f'<text x="38" y="{PA_Y+PA_H-20}" class="s">Ownership is poked, not played: in c_s30 the player holds only VULCAN, '
  'whose row of the matrix is then just its own 0.</text>')

# B: the matrix filling --------------------------------------------------------------------------
PB_Y, PB_H = PA_Y + PA_H + 14, 404
panel(24, PB_Y, 852, PB_H, 'B. The 64 x 64 matrix at $67b40 filling in, 8 rows per main-loop pass')
gap_med = statistics.median(FL['gaps']) if FL else None
a(f'<text x="38" y="{PB_Y+42}" class="s">Same ownership as A, from the reset. Row i, column k: distance from island i to k; '
  'blank is $ffff, no route yet.</text>')
show = [0, 1, 8, 16, 48, last_change]
cell = 1.75; side = 64 * cell; gx = 52; step = (852 - 56 - 6 * side) / 5
def colr(v):
    if v & 0x8000: return None
    f = min(1.0, v / 360)
    r0, g0, b0 = (0xdd, 0xf4, 0xff); r1, g1, b1 = (0x05, 0x30, 0x7a)
    return '#%02x%02x%02x' % (int(r0 + (r1 - r0) * f), int(g0 + (g1 - g0) * f), int(b0 + (b1 - b0) * f))
hy = PB_Y + 62
for n, c in enumerate(show):
    x0 = gx + n * (side + step)
    a(f'<rect x="{x0-0.5}" y="{hy-0.5}" width="{side+1}" height="{side+1}" fill="#f6f8fa" stroke="{GRID}"/>')
    M = hist[c]
    for i in range(64):
        for k in range(64):
            col = colr(M[i][k])
            if col: a(f'<rect x="{x0+k*cell:.2f}" y="{hy+i*cell:.2f}" width="{cell+0.05:.2f}" height="{cell+0.05:.2f}" fill="{col}"/>')
    lab = 'reset' if c == 0 else f'after {c} call' + ('s' if c > 1 else '')
    a(f'<text x="{x0+side/2:.1f}" y="{hy+side+15}" text-anchor="middle" class="s">{lab}</text>')
    a(f'<text x="{x0+side/2:.1f}" y="{hy+side+29}" text-anchor="middle" class="s">{fin_series[c]} filled</text>')
# colour key
ky = hy + side + 44
for i in range(0, 361, 6):
    a(f'<rect x="{gx+i*0.5:.1f}" y="{ky}" width="3.2" height="8" fill="{colr(i)}"/>')
a(f'<text x="{gx}" y="{ky+20}" class="s">0</text><text x="{gx+180}" y="{ky+20}" text-anchor="end" class="s">360+</text>')
a(f'<text x="{gx+190}" y="{ky+8}" class="s">distance (sum of edge costs). Rows 49..63 hold the enemy block; the lone '
  'cell at row 63, column 4 is the stray 500 (C).</text>')
# convergence curve
cx0, cy0, cw, ch = 96, ky + 40, 520, 92
def CXp(c): return cx0 + cw * c / CALLS
def CYp(v): return cy0 + ch - ch * v / FIN
for c in range(0, CALLS + 1, 8):
    a(f'<line x1="{CXp(c):.1f}" y1="{cy0}" x2="{CXp(c):.1f}" y2="{cy0+ch}" stroke="{GRID}" stroke-width="0.5"/>')
for c in range(0, CALLS + 1, 32):
    a(f'<text x="{CXp(c):.1f}" y="{cy0+ch+14}" text-anchor="middle" class="s">{c}</text>')
a(f'<text x="{cx0+cw/2}" y="{cy0+ch+28}" text-anchor="middle" class="s">calls of $21e8a (one per main-loop pass; a grey line every 8 calls = one sweep of 64 rows)</text>')
for v in (0, FIN):
    a(f'<text x="{cx0-8}" y="{CYp(v)+4:.1f}" text-anchor="end" class="s">{v}</text>')
a(f'<line x1="{cx0}" y1="{cy0+ch}" x2="{cx0+cw}" y2="{cy0+ch}" stroke="{MUTE}"/>')
for ser, col, dash in ((fin_series, MUTE, ' stroke-dasharray="4 3"'), (done_series, ACC, '')):
    pts = ' '.join(f'{CXp(c):.1f},{CYp(v):.1f}' for c, v in enumerate(ser))
    a(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="1.8"{dash}/>')
a(f'<line x1="{CXp(last_change):.1f}" y1="{cy0-4}" x2="{CXp(last_change):.1f}" y2="{cy0+ch}" stroke="{INK}" stroke-width="1"/>')
tx = 640
a(f'<line x1="{tx}" y1="{cy0+2}" x2="{tx+18}" y2="{cy0+2}" stroke="{MUTE}" stroke-width="1.8" stroke-dasharray="4 3"/>'
  f'<text x="{tx+24}" y="{cy0+6}" class="s">entries with a route</text>')
a(f'<line x1="{tx}" y1="{cy0+18}" x2="{tx+18}" y2="{cy0+18}" stroke="{ACC}" stroke-width="1.8"/>'
  f'<text x="{tx+24}" y="{cy0+22}" class="s">entries at their final value</text>')
a(f'<text x="{tx}" y="{cy0+44}" class="s">Last change at call {last_change}; the</text>')
a(f'<text x="{tx}" y="{cy0+58}" class="s">sweep after it changes nothing and</text>')
a(f'<text x="{tx}" y="{cy0+72}" class="s">clears $122f at call {CALLS}. Packets</text>')
a(f'<text x="{tx}" y="{cy0+86}" class="s">wait (timer 1) until then.</text>')

# C: the code ------------------------------------------------------------------------------------
PC_Y = PB_Y + PB_H + 14
PC_H = H - PC_Y - 20
panel(24, PC_Y, 852, PC_H, 'C. The code, from the disassembly, checked against the emulator')
code = [
    ('$21e8a  relax, 8 rows per call', [
        'for i in row .. row+7:',
        '  for (c, j) in links(i) if on:',
        '    for k in 0 .. 63:',
        '      if M[j][k] < $8000:',
        '        M[i][k] = min(M[i][k], M[j][k] + c)',
        'after 8 calls (64 rows): sweep again if',
        'anything changed, else clear $122f']),
    ('$22192  next hop from u towards t', [
        'best = $ffff',
        'for (c, j) in links(u) if on:',
        '  if M[j][t] < M[u][t]:      # strictly closer',
        '    if M[j][t] + c < best:',
        '      best = M[j][t] + c; hop = j',
        'node = hop; timer = c        # ticks to wait',
        'no hop: item packet lost, resource lot dumped']),
]
cy = PC_Y + 50
for n, (head, body) in enumerate(code):
    x0 = 38 + n * 420
    a(f'<text x="{x0}" y="{cy}" class="h" style="font-size:12.5px">{head}</text>')
    for m, l in enumerate(body):
        a(f'<text x="{x0}" y="{cy+20+m*15}" class="c" xml:space="preserve">{l.replace("<", "&lt;")}</text>')
by = cy + 20 + 7 * 15 + 14
notes = [
    'Ownership: $21f9e turns a link on only when both ends have the same owner (a free island\'s links are all off). Every "is now a',
    'free / friendly / enemy island" event calls $21e16, which redoes the links, refills the matrix with $ffff (diagonal 0) and restarts',
    'the relaxation. This is distance-vector routing (RIP\'s Bellman-Ford), run in place, with routers that are islands.',
]
for m, l in enumerate(notes):
    a(f'<text x="38" y="{by+m*15}" class="s">{l}</text>')
by += 3 * 15 + 8
if F0 and FL:
    ev = [f'Checked: the matrix before each call and after the last, {F0["calls"]} calls with c_s30\'s own owners and {FL["calls"]} with A\'s, equals the port in all',
          f'4096 entries each time ({F0["all_equal"] + FL["all_equal"]}/{F0["dumps"] + FL["dumps"]} dumps), with $122e and $122f matching; c_s30\'s converged matrix is the port\'s, {snap_eq}/4096.']
else:
    ev = [f'c_s30\'s converged matrix equals the port\'s, {snap_eq}/4096 (emulator drive not run).']
for m, l in enumerate(ev):
    a(f'<text x="38" y="{by+m*15}" class="s" style="fill:{INK}">{l}</text>')
by += len(ev) * 15 + 8
bug = ['Inferred bug: the island tick writes 500 at $1817e with A0 reloaded to row 63 ($69ac0), so instead of an enemy island\'s',
       'field it sets M[63][4] = 500 and the relaxation spreads a 500-cost "route" to CHARISSA 4 through the enemy block.']
for m, l in enumerate(bug):
    a(f'<text x="38" y="{by+m*15}" class="s" style="fill:{BAD}">{l}</text>')
a('</svg>')
(OUT / 'routing.svg').write_text('\n'.join(s))
print('wrote', OUT / 'routing.svg')
