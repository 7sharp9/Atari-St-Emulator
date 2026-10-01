"""route_cross38.py <start.snap> <OUTDIR> <down|up> [pre_wait_steps] [--sweep]: Cadaver 88th pass, F1.  A deterministic, natural-input crossing of room 38 from ANY creature phase.

Room 38's creatures (instance ids >= 900, class 3 patrols: they walk a closed loop at ~25,000 steps per cell, park at corners, and run only while the hero is IN the room: leaving freezes them, so waiting
in room 17/39 changes nothing) hit a hero walking at 25,000 steps per cell (same speed) for -2 per 10,000 steps of contact.  Rule (a creature-table wait-until-clear token in the style of E1's WQ):
  1. OBSERVE: from the settled arrival S0 run the emulator with the hero standing still and record the placement table every 5,000 steps for HORIZON steps (creatures: id >= 900, rect not deleted).
  2. PROFILE: from S0 drive the real crossing once (D lane / L along the south wall / D door for `down`; L, U lane, U door for `up`) and record the hero bbox every 5,000 steps.
  3. PLAN: the earliest wait d at the arrival (hero standing) such that the recorded hero path shifted by d never comes within MARGIN cells (closed rect overlap, z ignored) of a recorded creature rect, and the
     standing hero is never in reach during the wait; fallback: walk to a lane row and wait there (j, w).  The sweep mode reports the worst d over every start phase of the recording.
  4. EXECUTE the plan from S0 with the same driver (wait d, goto legs, optional pause), assert the health is unchanged; if a plan fails the next is tried.
The creature recording is a fork of the same snapshot (the hero standing vs walking does not move a creature: checked by the execution's health), so the plan is exact, not a bare wait.
Reload/determinism: every run reopens a snapshot; only OUTDIR is written."""
import sys, os, json
_args = [a for a in sys.argv[1:] if not a.startswith('--')]
FLAGS = [a for a in sys.argv[1:] if a.startswith('--')]
START_SNAP = os.path.abspath(_args[0]); OUTD = os.path.abspath(_args[1]); DIR = _args[2]; PRE = int(_args[3]) if len(_args) > 3 else 0
HD = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(HD, '..', '..', '..', '..', '..', '..', '..', '..')); os.environ['M68000_ROOT'] = ROOT
os.makedirs(OUTD, exist_ok=True); os.environ['CAD_OUT'] = OUTD
sys.path.insert(0, HD + '/../lib')
from route_lib import *

CH = 5000; HORIZON = 4500000
for _a in FLAGS:
    if _a.startswith('--horizon='): HORIZON = int(_a.split('=')[1])
MARGIN = 2
for _a in FLAGS:
    if _a.startswith('--margin='): MARGIN = int(_a.split('=')[1])
LAG = 85000

def crea(r):
    """creature placement entries (instance id >= 900, rect not deleted): (id, rect(xl,yl,xt,yt), zlow, zhigh)"""
    tbl = r.l(A5 + 56); n = r.w(A5 + 1152); out = []
    for i in range(1, n):
        e = r.mem(tbl + 0x46 * i, 0x46); t = int.from_bytes(e[10:14], 'big')
        if 0x1000 < t < 0x7ffff and e[0] != 255:
            oid = r.w(t + 4)
            if oid >= 900: out.append((oid, tuple(e[0:4]), e[5], e[4]))
    return out

def hit(h, cs, m=None):
    m = MARGIN if m is None else m
    for oid, rc, zl, zh in cs:
        if zl > 41: continue   # a spawned flyer still high above the hero (z bottom > hero top 29 + 12 of descent): cannot touch
        if h[0] + m >= rc[2] and rc[0] + m >= h[2] and h[1] + m >= rc[3] and rc[1] + m >= h[3]: return oid
    return None

def box(a, b): return (max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]))

def legs_for(direction, p):
    if direction == 'down': return [(DOWN, lambda q: q[1] >= 73), (LEFT, lambda q: q[0] <= 22), (DOWN, None)]
    L = [(LEFT, lambda q: q[0] <= 44)] if p[0] > 50 else []
    return L + [(UP, lambda q: q[1] <= 18), (UP, None)]

def synth_up(h0):
    """hero boxes every CH steps of the `up` crossing in free air (measured on E4's lineage: lag 80,000 steps after the press, then one cell per 24,000; the optional L leg from x lead > 50 moves
    from 75,000 at 24,200 per cell and turns into the lane with a 45,000-step lag); profile38.json holds the measured free `down` walk (e2 lineage, health 43, cost 0)"""
    x0, y0 = h0[0], h0[1]; H = []; k = 0; lend = None; x = x0; y = y0
    while True:
        k += 1; t = k * CH
        if x0 > 50 and lend is None:
            x = x0 - (0 if t < 75000 else 1 + (t - 75000) // 24200)
            if x <= 44: lend = t
        else:
            base = (lend + 45000) if lend else 80000
            y = y0 - (0 if t < base else 1 + (t - base) // 24000)
        y = max(y, 12); H.append((x, y, x - 6, y - 6))
        if y <= 12: return H

def drive(r, legs, rec=None, pause=None):
    """legs: (bits, stop cond | None = hold until the room changes); sample the hero every CH steps; pause = (chunk index j, w chunks): release at sample j for w chunks, press again"""
    room0 = r.w(ROOM); k = 0; paused = False
    for bits, cond in legs:
        joy(r, bits)
        for _ in range(500):
            r.cmd('s %d' % CH); k += 1; p = pos(r)
            if rec is not None: rec.append(p)
            if r.w(ROOM) != room0: break
            if cond and cond(p): break
            if pause and not paused and k == pause[0]:
                paused = True; joy(r, 0); r.cmd('s %d' % (CH * pause[1])); joy(r, bits)
        if r.w(ROOM) != room0: break
    joy(r, 0); r.cmd('s 100000')

def solve1(C, k0, H, h0, dmax):
    """earliest d (chunks) with the standing hero safe through chunk d and the walk H (sample i at chunk d+i+1) clear of C; None if none"""
    n = len(C)
    for d in range(0, dmax + 1):
        if k0 + d >= n or hit(h0, C[k0 + d]): return None
        ok = True
        for i, hp in enumerate(H):
            k = k0 + d + i + 1
            if k >= n: return None
            if hit(hp, C[k]): ok = False; break
        if ok: return d
    return None

def hero_at(H, h0, j, w, s):
    """phase 2 hero box s chunks after the start: walk to sample j, stand w chunks, resume with a lag of 0..LAG steps"""
    if s <= j: return H[s - 1] if s >= 1 else h0
    if s <= j + w: return H[j - 1]
    u = s - j - w; a = H[min(len(H) - 1, j - 1 + u)]; b = H[max(j - 1, min(len(H) - 1, j - 1 + u - LAG // CH))]
    return (max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]))

def solve2(C, k0, H, h0, wmax, step=6):
    best = None; n = len(C)
    for j in range(2, len(H) - 2, step):
        for w in range(0, wmax + 1, 2):
            tot = len(H) + w; ok = True
            for s in range(1, tot + 1):
                k = k0 + s
                if k >= n: return best
                hh = hero_at(H, h0, j, w, s)
                if hit(hh, C[k]): ok = False; break
            if ok:
                if best is None or w < best[1]: best = (j, w)
                break
            if s <= j + w and s > j: break   # standing hero hit during the wait: a longer wait cannot help
    return best

def main():
    r = Repl(START_SNAP); room = r.w(ROOM); h_start = r.w(HEALTH)
    print('start room %d pos %s health %d xp %d dir %s pre %d' % (room, pos(r), h_start, r.l(A5 + 1192), DIR, PRE), flush=True)
    if room != 38:
        print('enter 38: hold', 'DOWN' if DIR == 'down' else 'UP', hold(r, DOWN if DIR == 'down' else UP), flush=True)
    r.cmd('s %d' % (100000 + PRE))
    assert r.w(ROOM) == 38, r.w(ROOM)
    s0 = OUTD + '/s0_arrival38.snap'; r.snap(s0); h0 = pos(r); hp0 = r.w(HEALTH)
    print('S0 room 38 pos %s health %d creatures %s' % (h0, hp0, crea(r)), flush=True); r.close()
    # 1. observe (hero standing)
    r = Repl(s0); C = []; nk = HORIZON // CH
    for _ in range(nk + 1): C.append(crea(r)); r.cmd('s %d' % CH)
    print('observed %d steps, health %d -> %d (standing hero)' % (HORIZON, hp0, r.w(HEALTH)), flush=True); r.close()
    # 2. profile the crossing
    legs = legs_for(DIR, h0); prof = json.load(open(HD + '/profile38.json')) if os.path.exists(HD + '/profile38.json') else {}
    if '--measure' in FLAGS or (DIR == 'down' and 'down' not in prof):
        r = Repl(s0); H = []; drive(r, legs, H)
        print('profile (live, may be contact-deformed): %d samples, end room %d pos %s, d=0 cost %d' % (len(H), r.w(ROOM), pos(r), hp0 - r.w(HEALTH)), flush=True); r.close()
        cut = len(H)
        for i in range(1, len(H)):
            if abs(H[i][0] - H[i - 1][0]) > 12 or abs(H[i][1] - H[i - 1][1]) > 12: cut = i; break
        H = H[:cut]
    elif DIR == 'down': H = [tuple(x) for x in prof['down']]
    else: H = synth_up(h0)
    print('hero profile: %d samples (%d steps), start %s end %s' % (len(H), len(H) * CH, h0, H[-1]), flush=True)
    global MARGIN
    margins = [MARGIN] if any(f.startswith('--margin=') for f in FLAGS) else [2, 1]
    json.dump({'C': C, 'H': H, 'h0': h0}, open(OUTD + '/obs_%s.json' % DIR, 'w'))
    if '--obs' in FLAGS: return 0
    MARGIN = margins[0]
    if '--sweep' in FLAGS:
        ds = []
        for k0 in range(0, nk - len(H) - 200, 5):
            d = solve1(C, k0, H, h0, min(300, nk - k0 - len(H) - 2))
            if d is None:
                q = solve2(C, k0, H, h0, 150, 12); ds.append(('p2', q[1] if q else None, q))
            else: ds.append(('p1', d, None))
        w1 = [x[1] * CH for x in ds if x[0] == 'p1']; w2 = [x for x in ds if x[0] == 'p2']
        print('SWEEP over %d start phases (25,000 step spacing): phase-1 (wait at the arrival) solved %d, wait max %d mean %d steps; phase-2 (walk to a lane row, wait there) needed %d times, unsolved %d, max w %s' % (
            len(ds), len(w1), max(w1) if w1 else -1, (sum(w1) // len(w1)) if w1 else -1, len(w2), sum(1 for x in w2 if x[1] is None), max([x[2][1] * CH for x in w2 if x[2]] or [0])), flush=True)
    for MARGIN in margins:
        plans = []
        d1 = solve1(C, 0, H, h0, nk)
        if d1 is not None: plans.append((d1 * CH, d1, None))
        p2 = solve2(C, 0, H, h0, 400)
        if p2: plans.append((p2[1] * CH, 0, p2))
        plans.sort(key=lambda t: t[0])
        print('margin %d plans (total wait steps, d chunks, phase-2 (j,w)): %s' % (MARGIN, plans), flush=True)
        # 4. execute
        for tot, d, ph in plans[:4]:
            r = Repl(s0); rec = []
            if ph is None:
                r.cmd('s %d' % (d * CH)); drive(r, legs, rec)
            else:
                drive(r, legs, rec, (ph[0], ph[1]))
            dev = max([max(abs(a[0] - b[0]), abs(a[1] - b[1])) for a, b in zip(rec[:len(rec) - 4], H)] or [0]) if ph is None else -1
            print('executed walk: %d samples (profile %d), max deviation from the profile %d cells' % (len(rec), len(H), dev), flush=True)
            loss = hp0 - r.w(HEALTH)
            print('EXEC wait %d steps plan %s: end room %d pos %s health %d -> %d (cost %d)' % (tot, ph or 'arrival', r.w(ROOM), pos(r), hp0, r.w(HEALTH), loss), flush=True)
            if loss == 0 and r.w(ROOM) != 38:
                r.snap(OUTD + '/end_%s.snap' % DIR); json.dump({'wait': tot, 'plan': ph, 'room': r.w(ROOM), 'pos': pos(r)}, open(OUTD + '/result.json', 'w')); r.close(); return 0
            r.close()
    if '--force' in FLAGS:   # measurement only: walk at once although no safe plan exists
        r = Repl(s0); drive(r, legs, []); print('FORCED d=0 walk: end room %d pos %s health %d -> %d (cost %d)' % (r.w(ROOM), pos(r), hp0, r.w(HEALTH), hp0 - r.w(HEALTH)), flush=True); r.close()
    print('NO SAFE PLAN'); return 1

if __name__ == '__main__': sys.exit(main())
