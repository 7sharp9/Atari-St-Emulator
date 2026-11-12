#!/usr/bin/env python3
"""subdivide.py - extract a decoded model as a mesh and subdivide it toward a modern look.

usage: subdivide.py <model id> [levels=3] [crease_deg=35] [sharpness=2]

The model is built with the game's own builder (model.py, object angles 0) and every polygon of every BSP leaf is
kept (no visibility test), with its colour from the engine's colour-code table at $1544 and the game palette (a dither
code becomes the average of its two colours). Meshes are written to $CARRIER_WORK/mesh/ as OBJ + MTL:

  m<id>_orig.obj       the game's polygons
  m<id>_smooth.obj     Catmull-Clark, every edge smooth (open edges kept as boundaries)
  m<id>_crease.obj     Catmull-Clark with semi-sharp creases: an edge whose faces meet at more than crease_deg
                       stays sharp for `sharpness` levels, then rounds (a bevel-like fillet)

  m<id>_fit1.obj, _fit2.obj  the creased surface with its cage fitted (least squares) so the subdivided surface lies
                       on the game's polygons; the cage is the game mesh refined once or twice to give it freedom

Each is scored by silhouette IoU against the game polygons over 72 orthographic views (every 15 degrees of yaw at
pitch -30, 0, 30; 600 px), worst view and mean; the game mesh refined linearly is the control (the raster ceiling).
m<id>_compare.png renders them from two directions, flat shaded. The subdivision is ours, not the game's.
"""
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent)); _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
import math
from model import build, parse, palette, L, RAM
from PIL import Image, ImageDraw


def extract(mid):
    a = L(0x4c4ce + 4 * mid)
    m = parse(a, build(a, (0, 0, 0)))
    polys = []

    def leaf(p):
        n = RAM[p]; p += 1
        for _ in range(n):
            f = RAM[p]; p += 1
            if f & 1: p += 4
            if f & 2:
                npoly = RAM[p]; p += 1
                for _ in range(npoly):
                    nv = RAM[p]; p += 1; idx = list(RAM[p:p + nv]); p += nv; col = RAM[p]; p += 1
                    polys.append((col, idx))
            if f & 4: p += 1 + 3 * RAM[p]
            if f & 8: p += 1 + 4 * RAM[p]

    def node(p):
        b = RAM[p]
        if b & 0x80: return leaf(p + 1)
        off = (RAM[p + 1] << 8) | RAM[p + 2]; aa = p + 3
        node(aa); node(aa + off)
    node(m['bsp'])
    used = sorted({j for _, idx in polys for j in idx})
    remap = {j: k for k, j in enumerate(used)}
    V = [tuple(float(c) for c in m['vt'][j]) for j in used]
    pal = palette(); tbl = RAM[0x1544:0x1544 + 128]
    def rgb(col):
        c1, c2 = pal[tbl[2 * col]], pal[tbl[2 * col + 1]]
        return tuple((x + y) / 2 / 255 for x, y in zip(c1, c2))
    F = [[remap[j] for j in idx] for _, idx in polys]
    C = [rgb(col) for col, _ in polys]
    return V, F, C


def sub(a, b): return tuple(x - y for x, y in zip(a, b))
def add(*vs): return tuple(sum(c) for c in zip(*vs))
def mul(v, k): return tuple(x * k for x in v)
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def dot(a, b): return sum(x * y for x, y in zip(a, b))
def norm(v):
    l = math.sqrt(dot(v, v)) or 1.0
    return mul(v, 1 / l)


def fnormal(V, f):
    n = (0.0, 0.0, 0.0)
    for k in range(len(f)):                       # Newell's method
        a, b = V[f[k]], V[f[(k + 1) % len(f)]]
        n = add(n, ((a[1] - b[1]) * (a[2] + b[2]), (a[2] - b[2]) * (a[0] + b[0]), (a[0] - b[0]) * (a[1] + b[1])))
    return norm(n)


def edges_of(F):
    E = {}
    for fi, f in enumerate(F):
        for k in range(len(f)):
            e = tuple(sorted((f[k], f[(k + 1) % len(f)])))
            E.setdefault(e, []).append(fi)
    return E


def crease_sharpness(V, F, deg, s):
    """Edges whose two faces meet at more than `deg` (the polygons' windings are not consistent, so the angle between
    the face planes is taken unsigned) get sharpness s; open and non-manifold edges are infinitely sharp."""
    E = edges_of(F); S = {}
    lim = math.cos(math.radians(deg))
    for e, fs in E.items():
        if len(fs) != 2: S[e] = math.inf; continue
        c = abs(dot(fnormal(V, F[fs[0]]), fnormal(V, F[fs[1]])))
        S[e] = s if c < lim else 0
    return S


def catmull_clark(V, F, C, S):
    """One level of Catmull-Clark with semi-sharp creases (sharp rules while sharpness >= 1, children get s - 1)."""
    E = edges_of(F)
    for e in E:
        S.setdefault(e, math.inf if len(E[e]) != 2 else 0)
    fp = [mul(add(*[V[i] for i in f]), 1 / len(f)) for f in F]
    ep = {}
    for e, fs in E.items():
        mid = mul(add(V[e[0]], V[e[1]]), 0.5)
        if S[e] >= 1 or len(fs) != 2:
            ep[e] = mid
        else:
            ep[e] = mul(add(V[e[0]], V[e[1]], fp[fs[0]], fp[fs[1]]), 0.25)
    vf = [[] for _ in V]; ve = [[] for _ in V]
    for fi, f in enumerate(F):
        for i in f: vf[i].append(fi)
    for e in E:
        ve[e[0]].append(e); ve[e[1]].append(e)
    NV = []
    for i, v in enumerate(V):
        sharp = [e for e in ve[i] if S[e] >= 1 or len(E[e]) != 2]
        if len(sharp) > 2:
            NV.append(v)                                   # corner
        elif len(sharp) == 2:
            o = [e[0] if e[1] == i else e[1] for e in sharp]
            NV.append(mul(add(mul(v, 6), V[o[0]], V[o[1]]), 1 / 8))     # crease
        else:
            n = len(ve[i])
            Q = mul(add(*[fp[f] for f in vf[i]]), 1 / len(vf[i]))
            R = mul(add(*[mul(add(V[e[0]], V[e[1]]), 0.5) for e in ve[i]]), 1 / n)
            NV.append(mul(add(Q, mul(R, 2), mul(v, n - 3)), 1 / n))
    base = len(NV)
    fidx = {}
    for fi in range(len(F)):
        fidx[fi] = len(NV); NV.append(fp[fi])
    eidx = {}
    for e in E:
        eidx[e] = len(NV); NV.append(ep[e])
    NF, NC, NS = [], [], {}
    for fi, f in enumerate(F):
        n = len(f)
        for k in range(n):
            a, b, c = f[(k - 1) % n], f[k], f[(k + 1) % n]
            e1, e2 = tuple(sorted((a, b))), tuple(sorted((b, c)))
            q = [eidx[e1], b, eidx[e2], fidx[fi]]
            NF.append(q); NC.append(C[fi])
            for pe, child in ((e1, (eidx[e1], b)), (e2, (b, eidx[e2]))):
                NS[tuple(sorted(child))] = S[pe] - 1 if S[pe] >= 1 else 0
    return NV, NF, NC, NS


def write_obj(path, V, F, C):
    mats = sorted(set(C))
    name = {c: 'c%d' % k for k, c in enumerate(mats)}
    mtl = path.with_suffix('.mtl')
    mtl.write_text(''.join('newmtl %s\nKd %.4f %.4f %.4f\n' % (name[c], *c) for c in mats))
    with open(path, 'w') as fo:
        fo.write('mtllib %s\n' % mtl.name)
        for v in V: fo.write('v %.4f %.4f %.4f\n' % v)
        cur = None
        for f, c in zip(F, C):
            if c != cur: fo.write('usemtl %s\n' % name[c]); cur = c
            fo.write('f ' + ' '.join(str(i + 1) for i in f) + '\n')


def render(V, F, C, yaw, pitch, size=360, ss=2):
    """Flat-shaded z-buffer render (perspective, ss x supersampled), so the comparison has no sorting artefacts."""
    import numpy as np
    W = size * ss
    cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    def xf(v):
        x, y, z = v
        x, z = x * cy - z * sy, x * sy + z * cy
        y, z = y * cp - z * sp, y * sp + z * cp
        return x, y, z + 600
    T = [xf(v) for v in V]
    P = [(W / 2 + 520 * ss * t[0] / t[2], W / 2 - 520 * ss * t[1] / t[2], t[2]) for t in T]
    light = norm((-0.4, 0.7, -0.6))
    img = np.zeros((W, W, 3)); img[:] = (24, 26, 30)
    zb = np.full((W, W), np.inf)
    for f, c in zip(F, C):
        k = 0.35 + 0.65 * abs(dot(fnormal(T, f), light))
        col = np.array([255 * min(1, x * k) for x in c])
        for t in range(1, len(f) - 1):                       # fan into triangles
            (x0, y0, z0), (x1, y1, z1), (x2, y2, z2) = P[f[0]], P[f[t]], P[f[t + 1]]
            xa, xb = int(max(0, math.floor(min(x0, x1, x2)))), int(min(W - 1, math.ceil(max(x0, x1, x2))))
            ya, yb = int(max(0, math.floor(min(y0, y1, y2)))), int(min(W - 1, math.ceil(max(y0, y1, y2))))
            if xa > xb or ya > yb: continue
            den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
            if abs(den) < 1e-9: continue
            X, Y = np.meshgrid(np.arange(xa, xb + 1) + 0.5, np.arange(ya, yb + 1) + 0.5)
            l0 = ((y1 - y2) * (X - x2) + (x2 - x1) * (Y - y2)) / den
            l1 = ((y2 - y0) * (X - x2) + (x0 - x2) * (Y - y2)) / den
            l2 = 1 - l0 - l1
            inside = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
            z = l0 * z0 + l1 * z1 + l2 * z2
            sub_z = zb[ya:yb + 1, xa:xb + 1]
            m = inside & (z < sub_z)
            sub_z[m] = z[m]
            img[ya:yb + 1, xa:xb + 1][m] = col
    im = Image.fromarray(img.astype('uint8'))
    return im.resize((size, size), Image.LANCZOS)


def silhouette(V, F, yaw, pitch, size=600, scale=1.65):
    """Orthographic silhouette mask (union of every face) as a numpy bool array."""
    import numpy as np
    cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    im = Image.new('L', (size, size), 0); d = ImageDraw.Draw(im)
    P = []
    for x, y, z in V:
        x, z = x * cy - z * sy, x * sy + z * cy
        y, z = y * cp - z * sp, y * sp + z * cp
        P.append((size / 2 + scale * x, size / 2 - scale * y))
    for f in F:
        d.polygon([P[i] for i in f], fill=255)
    return np.asarray(im) > 0


VIEWS = [(math.radians(y), math.radians(p)) for p in (-30, 0, 30) for y in range(0, 360, 15)]


def iou(A, B):
    """Silhouette IoU of mesh B against mesh A over VIEWS: (min, mean)."""
    r = []
    for yw, pt in VIEWS:
        a, b = silhouette(A[0], A[1], yw, pt), silhouette(B[0], B[1], yw, pt)
        r.append((a & b).sum() / max(1, (a | b).sum()))
    return min(r), sum(r) / len(r)


def subdivide(V, F, C, S0, levels):
    v, f, c, S = V, F, C, dict(S0)
    for _ in range(levels):
        v, f, c, S = catmull_clark(v, f, c, S)
    return v, f, c


def refine_linear(V, F, C, k):
    """k levels with every edge sharp: the same polygons, finer, every point still on the game's surface."""
    v, f, c = V, F, C
    for _ in range(k):
        v, f, c, S = catmull_clark(v, f, c, {e: math.inf for e in edges_of(f)})
    return v, f, c


def fit_cage(V, F, C, levels, refine, deg, s):
    """A cage whose subdivided surface lies on the game's polygons, in the least-squares sense.

    The game mesh is refined `refine` times linearly to give the cage its freedom; its feature edges (faces meeting at
    more than `deg`) get sharpness `s`. Subdivision is linear in the cage, so the matrix M (fine vertex from cage
    vertex) is built by subdividing each unit cage vertex, and the cage solves min |M P - T|, T being the same
    topology subdivided linearly (points on the game's polygons). Returns the subdivided mesh and the max point error.
    """
    import numpy as np
    V0, F0, C0 = refine_linear(V, F, C, refine)
    S0 = crease_sharpness(V0, F0, deg, s) if s else {}
    T = np.array(refine_linear(V0, F0, C0, levels)[0])
    n = len(V0)
    M = np.array([[p[0] for p in subdivide([(1.0 if i == j else 0.0, 0.0, 0.0) for i in range(n)], F0, C0, S0,
                                           levels)[0]] for j in range(n)]).T
    P, *_ = np.linalg.lstsq(M, T, rcond=None)
    err = float(np.linalg.norm(M @ P - T, axis=1).max())
    return subdivide([tuple(map(float, r)) for r in P], F0, C0, S0, levels), err


def main():
    mid = int(sys.argv[1]); levels = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    deg = float(sys.argv[3]) if len(sys.argv) > 3 else 35; s = float(sys.argv[4]) if len(sys.argv) > 4 else 2
    out = WORK / 'mesh'; out.mkdir(parents=True, exist_ok=True)
    V, F, C = extract(mid)
    E = edges_of(F)
    print(f'model {mid}: {len(V)} vertices, {len(F)} polygons, {len(E)} edges, '
          f'{sum(len(x) == 1 for x in E.values())} open, {sum(len(x) > 2 for x in E.values())} non-manifold')
    A = (V, F, C)
    meshes = {'orig': A,
              'smooth': subdivide(V, F, C, {}, levels),
              'crease': subdivide(V, F, C, crease_sharpness(V, F, deg, s), levels)}
    for r in (1, 2):
        meshes[f'fit{r}'], err = fit_cage(V, F, C, levels, r, deg, s)
        print(f'fit{r}: cage refined {r}x, max point error {err:.2f}')
    labels = {'orig': 'game polygons', 'smooth': 'Catmull-Clark', 'crease': 'creased',
              'fit1': 'creased, fitted cage x1', 'fit2': 'creased, fitted cage x2'}
    score = {}
    ctl = iou(A, refine_linear(V, F, C, levels))
    print(f'control, the game polygons refined linearly: silhouette IoU min {ctl[0]:.3f} mean {ctl[1]:.3f}')
    for tag, m in meshes.items():
        score[tag] = iou(A, m)
        print(f'{tag:7s} {len(m[1]):6d} faces  silhouette IoU min {score[tag][0]:.3f} mean {score[tag][1]:.3f}')
        write_obj(out / f'm{mid}_{tag}.obj', *m)
    views = [(math.radians(35), math.radians(-28)), (math.radians(150), math.radians(-12))]
    tags = list(meshes)
    sheet = Image.new('RGB', (len(tags) * 360, 2 * 360 + 24), (24, 26, 30))
    for col, tag in enumerate(tags):
        for row, (yw, pt) in enumerate(views):
            sheet.paste(render(*meshes[tag], yw, pt), (col * 360, 24 + row * 360))
        d = ImageDraw.Draw(sheet)
        d.text((col * 360 + 8, 4), labels[tag], fill=(230, 230, 230))
        d.text((col * 360 + 8, 16), f'IoU min {score[tag][0]:.3f}', fill=(170, 170, 170))
    sheet.save(out / f'm{mid}_compare.png')
    print('wrote', out)


if __name__ == '__main__':
    main()
