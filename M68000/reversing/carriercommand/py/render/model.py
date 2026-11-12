"""model.py - decode a Carrier Command model (BSP + builder + derived-vertex program) and render it with the engine's own formulas.
Builder routine is run by callcap in the real emulator (identity camera, chosen object angles); everything after is parsed in python:
  header: [long draw routine $8e68|$9066|$9540|...] ($9066/$9540 then [long LOD distance]) [long builder] [builder args]
          [word n][n x (byte op,byte idx)]  derived vertices ($54e4: op 0 load, $18 store, $30 average-with, $48 add)
          [word nv]  vertices to project ($89c)
          [byte np][np x 3 bytes]  BSP plane table ($940a: 3 vertex indices each)
          BSP stream ($8e8c): node = [plane<$80][be16 off][subtree A][subtree B at A+off]; leaf = [$ff][n][n x item]
          item = [flags][if bit0: v0 v1 v2 (back-face test) + len][if bit1: np, np x (nv, nv idx, colour)][bit2: lines][bit3: discs]"""
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent)); _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
import struct, sys
sys.path.insert(0, str(ROOT / 'tools'))
from rig import *
from PIL import Image, ImageDraw
L = lambda a: struct.unpack('>I', RAM[a:a+4])[0]
W16 = lambda a: struct.unpack('>H', RAM[a:a+2])[0]
def s16(v): v &= 0xffff; return v - 65536 if v & 0x8000 else v
A1B = 0x62000
def build(addr, ang=(0, 0, 0), extra=()):
    p = addr + 4; routine = L(addr)
    thr = None
    if routine in (0x9066, 0x9540): thr = L(p); p += 4
    builder = L(p); p += 4
    cmds = [f'w 5dcde 0', f'w 5dce2 0', 'w 60004 %04x%04x' % (ang[0] & 0xffff, ang[1] & 0xffff), 'w 60008 %04x0000' % (ang[2] & 0xffff)] + list(extra)
    cmds.append(f'callcap {builder:x} 400000 A0={p:x} A1={A1B:x} A4=60000')
    out = repl(cmds); r = [x for x in parse_callcaps(out) if x['addr'] == builder]
    assert r, out[-400:]
    r = r[0]
    buf = apply(RAM, r['mem'])
    # the 5dcde/5dce2 pokes are in RAM too (camera record): irrelevant to the vertex table
    vt = [tuple(s16(struct.unpack_from('>h', buf, A1B + 6*i + 2*k)[0]) for k in range(3)) for i in range(256)]
    return dict(routine=routine, thr=thr, builder=builder, after=r['regs'].get('A0', (0, p))[1], vt=vt, mem=r['mem'])
def parse(addr, b):
    p = b['after']
    n = W16(p); p += 2
    ops = [(RAM[p + 2*i], RAM[p + 2*i + 1]) for i in range(n)]; p += 2*n
    vt = list(b['vt'])
    acc = [0, 0, 0]
    for op, idx in ops:
        if op == 0x00: acc = list(vt[idx])
        elif op == 0x18: vt[idx] = tuple(acc)
        elif op == 0x30: acc = [s16(a + c) >> 1 for a, c in zip(acc, vt[idx])]
        elif op == 0x48: acc = [s16(a + c) for a, c in zip(acc, vt[idx])]
        else: raise ValueError(f'op {op:x}')
    nv = W16(p); p += 2
    npl = RAM[p]; p += 1
    planes = [tuple(RAM[p + 3*i: p + 3*i + 3]) for i in range(npl)]; p += 3 * npl
    return dict(ops=ops, vt=vt, nv=nv, planes=planes, bsp=p, nops=n)
def dot(vt, tri, c):
    v0, v1, v2 = (vt[i] for i in tri)
    e1 = [(a - b) >> 1 for a, b in zip(v1, v0)]; e2 = [(a - b) >> 1 for a, b in zip(v2, v0)]
    n = (e1[1]*e2[2] - e1[2]*e2[1], e1[2]*e2[0] - e1[0]*e2[2], e1[0]*e2[1] - e1[1]*e2[0])
    d = [-(c[k] + v0[k]) for k in range(3)]
    return sum(a*b for a, b in zip(d, n))
def walk(m, c, out):
    """painter's-order polygon list (colour, [vertex idx]) by the engine's BSP traversal, with the engine's side flags and face tests."""
    flags = [dot(m['vt'], t, c) >= 0 for t in m['planes']]
    def leaf(p):
        n = RAM[p]; p += 1
        for _ in range(n):
            f = RAM[p]; p += 1; vis = True
            if f & 1:
                tri = RAM[p:p+3]; p += 3
                L_ = RAM[p]; end = p + L_; p += 1
                vis = dot(m['vt'], tri, c) >= 0
                if not vis: p = end; continue
            if f & 2:
                npoly = RAM[p]; p += 1
                for _ in range(npoly):
                    nv = RAM[p]; p += 1; idx = list(RAM[p:p+nv]); p += nv; col = RAM[p]; p += 1
                    out.append((col, idx))
            if f & 4:
                nl = RAM[p]; p += 1
                for _ in range(nl):
                    out.append(('L', RAM[p] & 0x7f, RAM[p+1], RAM[p+2])); p += 3
            if f & 8:
                nd = RAM[p]; p += 1; p += 4 * nd
        return p
    def node(p):
        b = RAM[p]
        if b & 0x80: return leaf(p + 1)
        off = (RAM[p+1] << 8) | RAM[p+2]; a = p + 3; bb = a + off
        if flags[b]: node(a); return node(bb)
        node(bb); return node(a)
    node(m['bsp'])
def colour_rgb(regs):
    return [((w >> 8) & 7) * 36 for w in regs], [((w >> 4) & 7) * 36 for w in regs], [(w & 7) * 36 for w in regs]
def render(m, c, pal, size=(256, 128), scale=3):
    tbl = RAM[0x1544:0x1544 + 128]
    img = Image.new('RGB', size, (40, 40, 40)); chk = Image.new('L', size, 0)
    px = chk.load()
    for y in range(size[1]):
        for x in range(size[0]):
            px[x, y] = 255 if (x + y) & 1 else 0
    polys = []; walk(m, c, polys)
    def proj(v):
        X = v[0] + c[0]; Y = -v[1] - c[1]; Z = v[2] + c[2]
        if Z < 64: return None
        while ((2 * Z) >> 16) != 0: X >>= 1; Y >>= 1; Z >>= 1
        tdiv = lambda a, b: (abs(a) // abs(b)) * (1 if (a < 0) == (b < 0) else -1)
        return (tdiv(X << 8, Z) + 160 - 32, tdiv(Y << 8, Z) + 70 - 6)
    drawn = 0
    for it in polys:
        if it[0] == 'L':
            _, col, a_, b_ = it; pa, pb = proj(m['vt'][a_]), proj(m['vt'][b_])
            if pa and pb: ImageDraw.Draw(img).line([pa, pb], fill=pal[tbl[2*col]]); drawn += 1
            continue
        col, idx = it
        pts = [proj(m['vt'][i]) for i in idx]
        if any(p is None for p in pts): continue
        c1, c2 = tbl[2*col], tbl[2*col+1]
        mask = Image.new('L', size, 0); ImageDraw.Draw(mask).polygon(pts, fill=255)
        img.paste(Image.new('RGB', size, pal[c1]), mask=mask)
        if c2 != c1:
            m2 = Image.new('L', size, 0)
            from PIL import ImageChops
            m2 = ImageChops.multiply(mask, chk)
            img.paste(Image.new('RGB', size, pal[c2]), mask=m2)
        drawn += 1
    return img.resize((size[0] * scale, size[1] * scale), Image.NEAREST), len(polys), drawn
def palette():
    from gfxview import load_video_regs
    regs = load_video_regs(SNAP)
    return [(((w >> 8) & 7) * 36, ((w >> 4) & 7) * 36, (w & 7) * 36) for w in regs['palette_words']]
if __name__ == '__main__':
    addr = int(sys.argv[1], 16); ang = tuple(int(x, 0) for x in sys.argv[2:5]) if len(sys.argv) >= 5 else (0, 0, 0)
    b = build(addr, ang); m = parse(addr, b)
    print('routine %x builder %x after %x nops %d nv %d planes %d bsp@%x' % (b['routine'], b['builder'], b['after'], m['nops'], m['nv'], len(m['planes']), m['bsp']))
