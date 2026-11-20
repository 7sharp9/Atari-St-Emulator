"""gate_all_models.py <snap> <poses> [--control]   Calls the drawer $26296 directly (stclient `call`-style, interrupts masked) for
EVERY model of the chain $aa72..$ce9a in several synthetic poses (random rotation matrices from the game's own sine table,
random in-front positions) and compares the vertex array at $27154 and the stream of $26780 calls against the Python
model in gate_model.py (imported).  Covers the models no natural frame in the snapshots draws.  Writes nothing."""
import os, sys, struct, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import vcommon
ROOT = vcommon.ROOT
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stclient import StServer
import importlib.util
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gate_model.py')).read()
# reuse the helpers (everything above the driver part)
helpers = src.split("snap = sys.argv[1]; nstops")[0]
G = {'__name__': 'gm', 'sys': sys, '__file__': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gate_model.py')}
sys.argv_saved = sys.argv
exec(helpers, G)
s16, predict, faces, CONTROL = G['s16'], G['predict'], G['faces'], '--control' in sys.argv
G['CONTROL'] = CONTROL

MODELS = [0xaa72, 0xaab8, 0xab62, 0xac66, 0xae30, 0xaee8, 0xafc8, 0xb01a, 0xb06c, 0xb0be, 0xb110, 0xb162, 0xb1ca, 0xb23e, 0xb2f6,
          0xb348, 0xb400, 0xb4e0, 0xb5e6, 0xb756, 0xb806, 0xb920, 0xb9d0, 0xba54, 0xbb88, 0xbc64, 0xbda4, 0xbee4, 0xc088, 0xc2b4,
          0xc390, 0xc472, 0xc5b2, 0xc6f2, 0xc79c, 0xc7e8, 0xc834, 0xc9a6, 0xcb30, 0xcce2, 0xcd50, 0xcdbe, 0xce2c]
snap, nposes = sys.argv[1], int(sys.argv[2])
s = StServer(ROOT); s('load', snapshot=os.path.join(ROOT, snap) if not os.path.isabs(snap) else snap)
RET = 0x800
SP = s.reg('a7') - 64
sine = struct.unpack('>1024h', s.read(0xd0fa, 2048))
def rotmat(rng):
    # Z*Y*X style from three random angles, 1.15 (x 32767), rows = world axes
    import math
    a, b, c = [rng.random() * 2 * math.pi for _ in range(3)]
    ca, sa, cb, sb, cc, sc = math.cos(a), math.sin(a), math.cos(b), math.sin(b), math.cos(c), math.sin(c)
    m = [[cb * cc, -cb * sc, sb], [ca * sc + sa * sb * cc, ca * cc - sa * sb * sc, -sa * cb], [sa * sc - ca * sb * cc, sa * cc + ca * sb * sc, ca * cb]]
    return [int(round(v * 32767)) for r in m for v in r]
rng = random.Random(1988)
res = {}
tot = dict(v=0, vb=0, sh=0, shb=0, c=0, cb=0, tri=0)
for m in MODELS:
    for pose in range(nposes):
        hdr = s.read(m, 8); nv = struct.unpack('>H', hdr[2:4])[0] + 1; nf = struct.unpack('>H', hdr[4:6])[0] + 1
        off = struct.unpack('>H', hdr[6:8])[0]
        mdl = s.read(m, off + 22 * nf)
        mat = rotmat(rng)
        pos = [rng.randint(-1200, 1200), rng.randint(-500, 800), rng.randint(2500, 9000)]
        s.p.stdin.flush()
        for i, v in enumerate(mat): s('poke', addr=0x270d4 + 2 * i, width=2, value=v & 0xffff)
        s('poke', addr=SP, width=4, value=RET); s('set_reg', name='a7', value=SP)
        s('set_reg', name='a6', value=m)
        for nm, v in zip(('d0', 'd1', 'd2'), pos): s('set_reg', name=nm, value=v & 0xffff)
        s('set_reg', name='sr', value=0x2700); s('set_reg', name='pc', value=0x26296)
        camx, camy, camz = struct.unpack('>3h', s.read(0x270ce, 6))
        calls = []; grounds = []; verts = None
        stops = [0x26780, 0x2637c, 0x26550, 0x263b4, 0x2657c]
        r = s('run', max_steps=400000, until_pc=[RET] + stops)
        guard = 0
        while True:
            guard += 1
            pc = int(r['pc'].lstrip('$'), 16) if isinstance(r['pc'], str) else r['pc']
            if r['reason'] != 'until' or guard > 4000: print('bad stop', m, r); break
            if pc == RET: break
            if pc == 0x26780:
                regs = [s16(s.reg('d%d' % i)) for i in range(6)]; calls.append((tuple(regs), s.reg('a0') & 0xffff))
            elif pc in (0x2637c, 0x26550): grounds.append(s.reg('d1') & 0xffff)
            else: verts = struct.unpack('>%dh' % (4 * nv), s.read(0x27154, 8 * nv))
            r = s('run', max_steps=400000, until_pc=[RET] + stops)
        rot = bool(mdl[0] & 1)
        pv, sh, nff, off2, shadow = predict(mdl, rot, pos, mat, grounds, camy)
        a = res.setdefault(m, [0, 0, 0, 0, 0, 0])
        for i in range(nv):
            if verts and (verts[4 * i], verts[4 * i + 1]) == pv[i]: tot['v'] += 1
            else: tot['vb'] += 1
            if shadow and sh[i] is not None:
                if verts and (verts[4 * i + 2], verts[4 * i + 3]) == sh[i]: tot['sh'] += 1
                else: tot['shb'] += 1
        fl = faces(mdl, nf, off)
        exp = []
        if rot:
            M = [mat[0:3], mat[3:6], mat[6:9]]
            if CONTROL: M = [[M[c][r2] for c in range(3)] for r2 in range(3)]
            G2 = G['mulr']; shd = []; vis = []
            for (nrm, idx, col) in fl:
                t = [s16(G2(M[r2][0], nrm[0]) + G2(M[r2][1], nrm[1]) + G2(M[r2][2], nrm[2])) for r2 in range(3)]
                d = s16(G2(pos[0], t[0]) + G2(pos[1], t[1]) + G2(pos[2], t[2]))
                if t[1] >= 0 and shadow and all(sh[i] for i in idx): shd.append((tuple(c for i in idx for c in sh[i]), 0))
                if d <= 0: vis.append((tuple(c for i in idx for c in pv[i] ), col & 0xffff))
            exp = shd + vis
        else:
            for (nrm, idx, col) in fl:
                if shadow and all(sh[i] for i in idx): exp.append((tuple(c for i in idx for c in sh[i]), 0))
                exp.append((tuple(c for i in idx for c in pv[i]), col & 0xffff))
        ok = (calls == exp)
        tot['c' if ok else 'cb'] += 1; tot['tri'] += len(exp)
        a[0] += ok; a[1] += 1
        if rot: a[2] = 1
print('%s models x %d poses (%d drawer calls)' % ('control (matrix transposed)' if CONTROL else 'model', nposes, tot['c'] + tot['cb']))
print('vertex projections %d/%d, shadow projections %d/%d, call streams %d/%d (%d triangle calls predicted)' % (
    tot['v'], tot['v'] + tot['vb'], tot['sh'], tot['sh'] + tot['shb'], tot['c'], tot['c'] + tot['cb'], tot['tri']))
bad = [(hex(m), a) for m, a in res.items() if a[0] != a[1]]
print('models with a stream mismatch:', bad[:12])
print('rotated models:', ' '.join('%x' % m for m, a in res.items() if a[2]))
s.close()
