"""gate_model.py <snap> <nstops> [--control]   Gate of the Virus model drawers' vertex transform, projection and face walk.
Own stserver; breakpoints $2629c (rotated entry), $264e2 (unrotated entry), $263b4/$2657c (vertex loop done),
$2637c/$26550 (ground height D1 after the shadow lookup), $2620e (deferred list) and $26780 (polygon fill, one call per
triangle).  For every model record the model data is read from RAM and the vertex array at $27154 and the stream of
$26780 calls are predicted in Python and compared.  --control breaks the prediction on purpose (matrix transposed).
Writes nothing."""
import os, sys, struct, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import vcommon
ROOT = vcommon.ROOT
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from stclient import StServer

CONTROL = '--control' in sys.argv

def s16(v):
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v

def divs(num32, den):
    num32 = struct.unpack('>l', struct.pack('>L', num32 & 0xffffffff))[0]
    den = s16(den)
    q = abs(num32) // abs(den)
    if (num32 < 0) != (den < 0): q = -q
    if q > 32767 or q < -32768:
        return num32 & 0xffff
    return q & 0xffff

def mulr(a, b):     # muls / swap / add.w D,D : 1.15 fixed point, word wrap
    return s16(2 * ((a * b) >> 16))

def pc_of(r):
    p = r['pc']
    return int(p.lstrip('$'), 16) if isinstance(p, str) else p

def rd(s, a, n): return s.read(a, n)

def project(x, y, z):
    sx = (s16(divs(x << 8, z)) + 0xa0) & 0xffff if False else s16(divs(s16(x) << 8, z) + 0xa0)
    sy = s16(divs(s16(y) << 8, z) + 0x46)
    return sx, sy

def predict(mdl, rotated, pos, mat, grounds, CAMY):
    """mdl bytes from the header on. returns (verts, shadows_or_None, list of events)"""
    flags = mdl[0]; nv = struct.unpack('>H', mdl[2:4])[0] + 1; nf = struct.unpack('>H', mdl[4:6])[0] + 1
    off = struct.unpack('>H', mdl[6:8])[0]
    shadow = bool(flags & 2)
    verts = []; sh = []
    g = iter(grounds)
    M = [mat[0:3], mat[3:6], mat[6:9]]
    if CONTROL: M = [[M[c][r] for c in range(3)] for r in range(3)]
    for i in range(nv):
        v = struct.unpack('>3h', mdl[8 + 6 * i:14 + 6 * i])
        if rotated:
            t = [s16(mulr(M[r][0], v[0]) + mulr(M[r][1], v[1]) + mulr(M[r][2], v[2])) for r in range(3)]
        else:
            t = list(v)
        x, y, z = s16(pos[0] + t[0]), s16(pos[1] + t[1]), s16(pos[2] + t[2])
        verts.append(project(x, y, z))
        if shadow:
            try: gd = next(g)
            except StopIteration: gd = None
            if gd is None: sh.append(None)
            else:
                dy = s16(gd - CAMY)
                sh.append((project(x, 0, z)[0], project(x, dy, z)[1]))
    return verts, sh, nf, off, shadow

def faces(mdl, nf, off):
    out = []
    for f in range(nf):
        p = off + 22 * f
        n = struct.unpack('>3h', mdl[p:p + 6])
        idx = [(struct.unpack('>I', mdl[p + 6 + 4 * k:p + 10 + 4 * k])[0] - 0x27154) // 8 for k in range(3)]
        col = struct.unpack('>I', mdl[p + 18:p + 22])[0]
        out.append((n, idx, col))
    return out

snap = sys.argv[1]; nstops = int(sys.argv[2])
s = StServer(ROOT); s('load', snapshot=os.path.join(ROOT, snap) if not os.path.isabs(snap) else snap)
BPS = [0x2629c, 0x264e2, 0x263b4, 0x2657c, 0x2637c, 0x26550, 0x2620e, 0x26780]
s('bp_set', addrs=BPS)
CAMX = CAMY = CAMZ = 0
events = []   # (kind, payload)
last = None; n = 0
cur = None
while n < nstops:
    r = s('run', max_steps=3000000)
    if r['reason'] != 'breakpoint':
        print('stopped', r['reason']); break
    pc = pc_of(r)
    key = (pc, s.reg('a6'), tuple(s.reg('d%d' % i) & 0xffff for i in range(6)), s.reg('a0') & 0xffff, s.reg('a7'))
    if key == last and r["steps"] < 2000: continue
    last = key; n += 1
    if pc in (0x2629c, 0x264e2):
        a6 = s.reg('a6')
        hdr = rd(s, a6, 8)
        if pc == 0x2629c and not (hdr[0] & 1): continue       # falls into $264e2 at once
        nv = struct.unpack('>H', hdr[2:4])[0] + 1; nf = struct.unpack('>H', hdr[4:6])[0] + 1
        off = struct.unpack('>H', hdr[6:8])[0]
        mdl = rd(s, a6, off + 22 * nf)
        pos = [s16(s.reg(x)) for x in ('d0', 'd1', 'd2')]
        mat = struct.unpack('>9h', rd(s, 0x270d4, 18))
        defer = rd(s, 0x62a69, 1)[0] != 0 and pc == 0x2629c
        CAMX, CAMY, CAMZ = struct.unpack('>3h', rd(s, 0x270ce, 6))
        cur = {'a6': a6, 'mdl': mdl, 'pos': pos, 'mat': mat, 'rot': pc == 0x2629c, 'defer': defer, 'cam': (CAMX, CAMY, CAMZ), 'g': [], 'calls': [], 'verts': None, 'dcalls': None, 'lst': None}
        events.append(cur)
    elif pc in (0x2637c, 0x26550) and cur is not None:
        cur['g'].append(s.reg('d1') & 0xffff)
    elif pc in (0x263b4, 0x2657c) and cur is not None:
        nv = struct.unpack('>H', cur['mdl'][2:4])[0] + 1
        cur['verts'] = struct.unpack('>%dh' % (4 * nv), rd(s, 0x27154, 8 * nv))
    elif pc == 0x2620e:
        cur = {'deferred_draw': True, 'calls': []}
        events.append(cur)
    elif pc == 0x26780 and cur is not None:
        regs = [s.reg('d%d' % i) & 0xffff for i in range(6)]
        regs = [s16(v) for v in regs]
        cur['calls'].append((tuple(regs), s.reg('a0') & 0xffff))
s.close()

# ---- compare ----
vok = vbad = shok = shbad = cok = cbad = 0; nmod = 0; defer_models = 0; skipped = 0
byaddr = collections.Counter()
pending = []
for e in events:
    if 'deferred_draw' in e:
        continue
    if e['verts'] is None: skipped += 1; continue
    verts, sh, nf, off, shadow = predict(e['mdl'], e['rot'], e['pos'], e['mat'], e['g'], e['cam'][1])
    nvv = len(verts)
    nmod += 1; byaddr[e['a6']] += 1
    # vertex array: sx,sy at +0, shadow sx,sy at +4 (words 2,3)
    got = e['verts']
    for i in range(nvv):
        if (got[4 * i], got[4 * i + 1]) == verts[i]: vok += 1
        else: vbad += 1
        if shadow and sh[i] is not None:
            if (got[4 * i + 2], got[4 * i + 3]) == sh[i]: shok += 1
            else: shbad += 1
    # polygon calls
    fl = faces(e['mdl'], nf, off)
    exp = []
    if e['rot']:
        M = [e['mat'][0:3], e['mat'][3:6], e['mat'][6:9]]
        if CONTROL: M = [[M[c][r] for c in range(3)] for r in range(3)]
        shd = []; vis = []
        for (nrm, idx, col) in fl:
            t = [s16(mulr(M[r][0], nrm[0]) + mulr(M[r][1], nrm[1]) + mulr(M[r][2], nrm[2])) for r in range(3)]
            d = s16(mulr(e['pos'][0], t[0]) + mulr(e['pos'][1], t[1]) + mulr(e['pos'][2], t[2]))
            if t[1] >= 0 and shadow:
                if all(sh[i] for i in idx):
                    shd.append((tuple(c for i in idx for c in sh[i]), 0))
            if d <= 0:
                vis.append((tuple(c for i in idx for c in verts[i]), col & 0xffff))
        exp = shd + vis
    else:
        for (nrm, idx, col) in fl:
            if shadow and all(sh[i] for i in idx):
                exp.append((tuple(c for i in idx for c in sh[i]), 0))
            exp.append((tuple(c for i in idx for c in verts[i]), col & 0xffff))
    e['exp'] = exp
    e['pidx'] = len(pending); pending.append(e)

# actual call streams: non-deferred models own their 'calls'; deferred models' visible faces arrive in the
# next deferred_draw record (after other models), so attribute those by order.
dq = [e for e in pending if e['defer']]
dd = [e for e in events if 'deferred_draw' in e]
for e in pending:
    if e['defer']:
        # shadows are immediate (A0 = 0 calls of this record), visible faces later
        e['act'] = list(e['calls'])
    else:
        e['act'] = list(e['calls'])
for e, d in zip(dq, dd):
    e['act'] += d['calls']

ntri = 0; nrot = 0
for e in pending[:-1]:       # the last record may be cut by the stop budget
    exp = e['exp']; act = e['act']; ntri += len(exp); nrot += e['rot']
    if e['defer']: defer_models += 1
    # order-sensitive comparison, counting matched triangles in sequence
    ok = len(exp) == len(act) and all(((a[0] == x[0]) and a[1] == x[1]) for a, x in zip(act, exp))
    if ok: cok += 1
    else:
        cbad += 1
        if os.environ.get('DBG') and cbad <= 4:
            print('MISMATCH model %x rot=%s defer=%s exp=%d act=%d' % (e['a6'], e['rot'], e['defer'], len(exp), len(act)))
            for a, x in list(zip(act, exp))[:4]: print('  act', a, 'exp', x)
print('snapshot %s, %d stops, %d model draws with a vertex pass (%d skipped), %d deferred' % (snap, n, nmod, skipped, defer_models))
print('last record dropped (cut by the stop budget); %d triangle calls predicted, %d rotated models' % (ntri, nrot))
print('models by address:', ' '.join('%x:%d' % kv for kv in sorted(byaddr.items())))
print('control' if CONTROL else 'model', 'vertex projections (sx,sy) %d/%d' % (vok, vok + vbad),
      '; shadow projections %d/%d' % (shok, shok + shbad),
      '; whole polygon-call streams (every call: 6 screen words + colour index, in order) %d/%d models' % (cok, cok + cbad))
if os.environ.get('DBG2'):
    for e in pending[:6]:
        v, sh, nf, off, shadow = predict(e['mdl'], e['rot'], e['pos'], e['mat'], e['g'], e['cam'][1])
        print('%x rot=%s pos=%s cam=%s g=%s' % (e['a6'], e['rot'], e['pos'], (CAMX,CAMY,CAMZ), e['g'][:4]))
        print(' pred sh', sh[:3]); print(' got', e['verts'][:12])
