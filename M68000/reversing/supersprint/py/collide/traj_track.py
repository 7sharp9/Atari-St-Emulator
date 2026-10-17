"""traj_track.py - test_trajectory.py generalised to any per-track snapshot (tracks/race_T.snap, stopped at $beb2).
usage: traj_track.py <snap> <nframes> <seed> [tag]
Runs from the snapshot to the first $df18 (the race initialiser still has ~2.7M steps to go), then compares port vs live for N frames.
Scratch goes under agents/collide/tmp (pl.OUT overridden)."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'reversing', 'supersprint', 'py', 'physics'))
import pl
pl.OUT = os.path.join(pl.sscfg.WORK, 'agents', 'collide')
from difflib_ss import *
import gateanim

snap = sys.argv[1]; N = int(sys.argv[2]); seed = int(sys.argv[3]); TRACK = int(sys.argv[4]); USEGATE = (sys.argv[5] != '0') if len(sys.argv) > 5 else True
h = Harness(snap)
MODE = sys.argv[6] if len(sys.argv) > 6 else 'random'
import math
class Chase(Driver):
    """steer the human car (the one with ISDRONE == 0) at the position of the nearest-ahead drone via the joystick-0 byte; fire held.
    seed perturbs the fire release pattern."""
    last = None
    def poke_input(s):
        if s.count % 3 == 0 and Chase.last is not None:
            m = P.Mem(Chase.last.b)
            hum = [c for c in range(4) if m.au(P.ISDRONE, c) == 0]
            dro = [c for c in range(4) if m.au(P.ISDRONE, c) != 0 and m.a(P.FLAG, c) == 0]
            byte = 0x80
            if hum and dro:
                hc = hum[0]; dc = dro[(s.count // 300) % len(dro)]
                dx = m.a(P.X, dc) - m.a(P.X, hc); dy = m.a(P.Y, dc) - m.a(P.Y, hc)
                if abs(dx) + abs(dy) > 6:
                    want = int(round(math.atan2(dx, -dy) / (2 * math.pi) * 16)) % 16
                    diff = (want - m.a(P.HEAD, hc)) % 16
                    if diff in (1, 2, 3, 4, 5, 6, 7, 8): byte |= 8
                    elif diff: byte |= 4
                if s.rng.random() < 0.04: byte &= ~0x80
            s.h.cmd('kbd fe %02x' % byte); s.h.cmd('s 300')
        s.count += 1
drv = Chase(h, seed) if MODE == 'chase' else Driver(h, seed)
FIELDS = {k: getattr(P, k) for k in ('X','Y','HEAD','TGT','SPD','QX','QY','PX','PY','FLAG','WP','STUN','BUMP','F1','F2','GATE','SECTOR','TURN','LAPPOS','TURNCNT','VX','VY','VTX','VTY','AX','AY','RX','RY','WPX','WPY','SAFEX','SAFEY','SAFEH','LAPS','WRENCH')}
DUMP = tuple(int(x) for x in os.environ['DUMP'].split('-')) if os.environ.get('DUMP') else None
DUMPF = {k: getattr(P, k) for k in ('X','Y','SPD','STUN','FLAG','F1','F2','TGT','HEAD','WP','LAPS','SECTOR','TURN','BUMP','ISDRONE')}
FIN = None; FREEZE = int(os.environ.get('FREEZE', '5'))     # FIN = frame at which a live car first shows 4 laps (the finish detection of $c8ac)
ok = {k: 0 for k in FIELDS}; frames = allok = 0; firstbad = []; badframes = []; prev = None; gatebad = []; planebad = [[], [], []]; bgbad = []; spawns = []; mapbad = []
import collections; cov = collections.Counter()
if os.environ.get('RACE'):         # poke the race counter -1748(A4) at $beb2 (before the hazard placement routines run) so oil/cones/tornado/signs are placed for that R
    r0 = h.snap_ram(); h.cmd('w %x %04x%04x' % (A4 - 1748, int(os.environ['RACE']), r0.gu(-1746)))
if h.run_to(0xdf18, 1, 8000000) is None:
    print('never reached df18'); sys.exit(1)
for i in range(N + 1):
    drv.poke_input()
    if h.run_to(0xdf18, 1) is None: break
    cur = h.snap_ram()
    Chase.last = cur
    if prev is not None:
        m = P.Mem(prev.b)
        for off in (-4804, -4803): m.wb(A4 + off, cur.u8(A4 + off))
        (gateanim.next_boundary(m, TRACK, controls=not (FIN is not None and i >= FIN + FREEZE), signs=bool(os.environ.get('SIGNS'))) if USEGATE else P.next_boundary(m))
        c = P.Mem(cur.b); frames += 1; fo = True
        for nm, off in FIELDS.items():
            for car in range(4):
                if m.a(off, car) == c.a(off, car): ok[nm] += 1
                else:
                    fo = False
                    if len(firstbad) < 8: firstbad.append((i, nm, car, m.a(off, car), c.a(off, car)))
        if not (m.gu(-8072) == c.gu(-8072) and m.gu(-8478) == c.gu(-8478)):
            fo = False
            if len(firstbad) < 8: firstbad.append((i, 'cnt', 0, (m.gu(-8072), m.gu(-8478)), (c.gu(-8072), c.gu(-8478))))
        if DUMP and DUMP[0] <= i <= DUMP[1]:
            pv = P.Mem(prev.b)
            for car in range(4):
                print('f%d car%d  prev[%s]  port[%s]  live[%s]' % (i, car, ' '.join('%s=%d' % (n, pv.a(o, car)) for n, o in DUMPF.items()), ' '.join('%s=%d' % (n, m.a(o, car)) for n, o in DUMPF.items()), ' '.join('%s=%d' % (n, c.a(o, car)) for n, o in DUMPF.items())))
            print('f%d globals: R=%d countdown?' % (i, c.gu(-8072)), 'laps', [c.a(P.LAPS, k) for k in range(4)], 'sector', [c.a(P.SECTOR, k) for k in range(4)], 'tiles', [c.a(P.GATE, k) for k in range(4)])
        # surface-map compare (1000 bytes)
        mb = cur.gl(-1910)
        if bytes(m.b[mb:mb+1000]) != bytes(cur.b[mb:mb+1000]):
            d = [k for k in range(1000) if m.b[mb+k] != cur.b[mb+k]]
            sp = lambda a, b: (a & 0x7f) in (13, 17) and (a & 0x80) == (b & 0x80)     # a = value holding the wrench/bonus code, b = the value it replaced (0, or an attribute cell such as 0x08) or became (0)
            if all((sp(cur.b[mb+k], m.b[mb+k]) and (m.b[mb+k] & 0x7f) not in (13, 17)) or (sp(m.b[mb+k], cur.b[mb+k]) and (cur.b[mb+k] & 0x7f) == 0) for k in d):
                spawns.append(i)       # runtime wrench (0x0d) / bonus (0x11) cell placed or expired by $abd4/$ae0e (RNG spawn, 584-frame bonus life): not modelled
            else:
                fo = False
                mapbad.append((i, [(k, m.b[mb+k], cur.b[mb+k]) for k in d[:6]]))
            if len(firstbad) < 8: firstbad.append((i, 'MAP', d[:6], [m.b[mb+k] for k in d[:6]], [cur.b[mb+k] for k in d[:6]]))
        # gate arrays -1832..-1808 (dir, phase, timer, route, count) and the three collision planes + both background pages
        ga = bytes(m.b[A4-1832:A4-1806]); gb = bytes(cur.b[A4-1832:A4-1806])
        if ga != gb:
            fo = False; gatebad.append(i)
            if len(firstbad) < 8: firstbad.append((i, 'GATEARR', list(ga), list(gb)))
        pb = cur.gl(-94)
        for pl_i in range(3):
            lo = pb + 8000 * pl_i + (40 * 32 if pl_i == 2 else 0)      # plane 2 rows 0..31 hold the HUD digit stamps ($158ea/$15e5a): excluded
            hi = pb + 8000 * (pl_i + 1)
            if bytes(m.b[lo:hi]) != bytes(cur.b[lo:hi]):
                fo = False; planebad[pl_i].append(i)
                if len(firstbad) < 8:
                    d = [k for k in range(lo, hi) if m.b[k] != cur.b[k]]
                    firstbad.append((i, 'PLANE%d' % pl_i, len(d), [((k-pb-8000*pl_i)//40, (k-pb-8000*pl_i)%40, m.b[k], cur.b[k]) for k in d[:8]]))
        for bgp in (-78, -86):
            bb = cur.gl(bgp)
            if bytes(m.b[bb:bb+32000]) != bytes(cur.b[bb:bb+32000]):
                bgbad.append((i, bgp))     # informational only: the port draws no car sprites into the screen pages
        # coverage of the live run
        pv = P.Mem(prev.b); cu = c
        for car in range(4):
            if cu.a(P.STUN, car) > pv.a(P.STUN, car) and pv.a(P.STUN, car) == 0 and cu.au(P.ISDRONE, car) == 0: cov['humanbounce'] += 1
            if cu.a(P.FLAG, car) == 2 and pv.a(P.FLAG, car) != 2: cov['crash_c%d' % car] += 1
            if cu.a(P.GATE, car) != pv.a(P.GATE, car): cov['GATEchg'] += 1
            if cu.a(P.SECTOR, car) != pv.a(P.SECTOR, car): cov['SECTORchg'] += 1
            if cu.a(P.LAPS, car) != pv.a(P.LAPS, car): cov['LAPSchg'] += 1
            if (cu.au(P.F1, car) ^ pv.au(P.F1, car)): cov['F1chg'] += 1
            if cu.a(P.BUMP, car) == 0x19: cov['carbump'] += 1
        if fo: allok += 1
        else: badframes.append(i)
    if FIN is None and any(P.Mem(cur.b).a(P.LAPS, k) == 4 for k in range(4)): FIN = i; print('first live frame with a 4-lap car:', i)
    prev = cur
print('%s: frames %d, all fields+map identical in %d' % (os.path.basename(snap), frames, allok))
print('bad fields:', {k: frames*4 - v for k, v in ok.items() if v != frames*4})
print('bad frames:', badframes[:40])
print('gate array mismatches:', len(gatebad), gatebad[:10], ' plane0/1/2 mismatch frames:', [len(x) for x in planebad], [x[:5] for x in planebad], ' bg page mismatches:', len(bgbad), bgbad[:6])
print('map frames differing only by a wrench/bonus cell appearing or expiring (excluded):', spawns)
print('map mismatches not explained by wrench/bonus (frame, [(cell, port, live)]):', mapbad[:10])
print('coverage:', dict(cov))
print('P.COV (surface kind,payload):', dict(sorted(P.COV.items())))
print('first bad (frame, field, car, port, live):', firstbad)
h.close()
