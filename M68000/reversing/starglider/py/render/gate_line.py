"""Gate for the edge pipeline: $14f00 (near-plane clip), $14cfc (window clip), $13cb4 (Bresenham line drawer, via the jump vector 44(A6))
and $f8f2 (whole edge: clip, perspective divide, clip, draw) against rref.py.

    python3 gate_line.py [--control]     # --control: line drawer with the wrong error-term update (breaks every non-axis line)
Inputs are labelled POKES/presets: endpoint registers D1..D6 (or D4..D7) and the colour word 520(A6); the base RAM is the g_game1 snapshot
(low-resolution window 16..303 x 10..128, centre (143,68), shift 7, screen $78000).  Compared: the whole memory delta (changed bytes
outside the stack) and the exit endpoint registers.  Colour 10 (unused by any model) is run separately: its shallow-slope slot jumps into the
steep loop (quirk10) and the reference reproduces that.  Expected: all lines `n/n`."""
import os, sys, random
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import rcommon as R
import rref as F
A6 = F.A6
random.seed(7)
COV = []; LOOPS = []; NEARCLIP = []
ram = R.load_ram(R.SNAP_GAME1)
OUT = R.WORK + '/render/caps'
N = int(os.environ.get('N', 60))
CONTROL = '--control' in sys.argv
if CONTROL:
    import types
    src = open(os.path.join(here, 'rref.py')).read().replace("e = (e + D3) & 0xFFFF", "e = (e + D3 + 1) & 0xFFFF")
    F2 = types.ModuleType('rref_bad'); exec(compile(src, 'rref_bad', 'exec'), F2.__dict__); F = F2

def delta_of(res):
    stack = (res['entrySP'] - 512, res['entrySP'] + 16)
    return {a: n for a, o, n in res['mem'] if not (stack[0] <= a < stack[1])}

def regs_ok(r, want):
    return all((r['regN'][int(k[1]) + (8 if k[0]=='A' else 0)] & 0xFFFF) == (v & 0xFFFF) for k, v in want.items())

def mkbase(pokes):
    b = bytearray(ram)
    for k, a, v in pokes:
        if k == 'ww': b[a] = (v >> 8) & 255; b[a + 1] = v & 255
    return b

def run(name, addr, cases, ref):
    jobs = [dict(addr=addr, presets=dict(A6=A6, **pre), pokes=pk) for pre, pk in cases]
    res = R.cc_jobs(R.SNAP_GAME1, jobs, OUT, 'gl_' + ''.join(c for c in name if c.isalnum()))
    ok = 0; shown = 0
    for r, (pre, pk) in zip(res, cases):
        m = F.Mem(mkbase(pk))
        try:
            want_regs = ref(m, pre)
        except RuntimeError:      # the reference's clip2d never terminates: the real routine must be detected looping too
            ok += r['outcome'].startswith('THREW'); LOOPS.append((pre, r['outcome'], r['steps']))
            continue
        good = m.changes() == delta_of(r) and (want_regs is None or regs_ok(r, want_regs))
        ok += good
        COV.append((name, bool(m.changes()), (want_regs or {}).get('D0')))
        if not good and shown < 3:
            shown += 1
            print('  MISS', pre, 'want', sorted(m.changes().items())[:4], 'got', sorted(delta_of(r).items())[:4], want_regs, r['regN'][:8])
    print(f'{name:14s} {ok}/{len(cases)}')
    return ok == len(cases)

def rp(lo, hi): return random.randrange(lo, hi)

ok = True
# $13cb4 drawer: random lines inside the window, all colours 1..15 except 10, then colour 10 shallow/steep
cases = []
for i in range(N):
    col = random.choice([1,2,3,4,5,6,7,8,9,11,12,13,14,15])
    x1, x2 = rp(16, 304), rp(16, 304); y1, y2 = rp(10, 129), rp(10, 129)
    if i % 7 == 0: y2 = y1
    if i % 11 == 0: x2 = x1
    cases.append((dict(D4=x1, D5=y1, D6=x2, D7=y2), [('ww', A6 + 520, col)]))
def ref_draw(m, pre):
    F.draw_line(m, pre['D4'], pre['D5'], pre['D6'], pre['D7']); return None
ok &= run('draw $13cb4', 0x13cb4, cases, ref_draw)
cases = []
for i in range(20):
    x1 = rp(16, 280); y1 = rp(10, 100)
    steep = i % 2
    dx, dy = (rp(1, 30), rp(31, 100)) if steep else (rp(31, 100), rp(1, 30))
    cases.append((dict(D4=x1, D5=y1, D6=x1 + dx, D7=y1 + dy), [('ww', A6 + 520, 10)]))
ok &= run('draw colour 10', 0x13cb4, cases, ref_draw)

# $14cfc window clip: endpoints anywhere in +-1000
cases = [(dict(D4=rp(-150, 450), D5=rp(-80, 220), D6=rp(-150, 450), D7=rp(-80, 220)), []) for _ in range(N * 2)]
def ref_c2(m, pre):
    d0, a, b, c, d = F.clip2d(m, pre['D4'], pre['D5'], pre['D6'], pre['D7'])
    return dict(D0=d0, D4=a, D5=b, D6=c, D7=d)
ok &= run('clip2d $14cfc', 0x14cfc, cases, ref_c2)

# $14f00 near clip: view-space endpoints, z around the plane at 2
def r3(): return (rp(-2000, 2000), rp(-2000, 2000), rp(-300, 2500) if random.random() < .5 else rp(-3, 40))
cases = []
for _ in range(N * 2):
    a, b = r3(), r3()
    cases.append((dict(D1=a[0], D2=a[1], D3=a[2], D4=b[0], D5=b[1], D6=b[2]), []))
def ref_c3(m, pre):
    d0, *v = F.clip_near(m, *(pre[k] for k in ('D1', 'D2', 'D3', 'D4', 'D5', 'D6')))
    if d0 == 0 and (v[2], v[5]) != (F.s16(pre['D3']), F.s16(pre['D6'])): NEARCLIP.append(1)
    return dict(D0=d0, D1=v[0], D2=v[1], D3=v[2], D4=v[3], D5=v[4], D6=v[5])
ok &= run('clip3d $14f00', 0x14f00, cases, ref_c3)

# $f8f2 whole edge
cases = []
for i in range(N * 2):
    a, b = r3(), r3()
    if i % 3 == 0: a = (rp(-300, 300), rp(-200, 200), rp(100, 900)); b = (rp(-300, 300), rp(-200, 200), rp(100, 900))
    cases.append((dict(D1=a[0], D2=a[1], D3=a[2], D4=b[0], D5=b[1], D6=b[2]), [('ww', A6 + 520, random.choice([1, 3, 5, 7, 13, 15]))]))
cases.append((dict(D1=589, D2=-1674, D3=-110, D4=1532, D5=1538, D6=6), [('ww', A6 + 520, 1)]))   # found by search: $14cfc never terminates (the emulator's loop detector fires)
def ref_f8(m, pre):
    F.f8f2(m, *(pre[k] for k in ('D1', 'D2', 'D3', 'D4', 'D5', 'D6'))); return None
ok &= run('edge $f8f2', 0xf8f2, cases, ref_f8)
import collections
c = collections.Counter((n, b) for n, b, d in COV)
print('coverage (cases that changed memory / not):', dict(c))
print('clip3d D0 results:', dict(collections.Counter(d for n, b, d in COV if n.startswith('clip3d'))), ' clip2d D0:', dict(collections.Counter(d for n, b, d in COV if n.startswith('clip2d'))))
print('near-plane clips that moved an endpoint:', len(NEARCLIP))
print('non-terminating inputs (both the reference and the emulator loop):', len(LOOPS), LOOPS[:2])
print('ALL PASS' if ok else 'FAIL')
