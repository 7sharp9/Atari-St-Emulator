"""Model database reader and contact sheet.

Model headers: 16 bytes each at $15ada + 16*i (i = model 1..28), words
  [nverts, nedges, nfaces, off_verts, off_edges, off_faces, off_end, 0]; offsets from 120(A6) = $15caa.
Type -> model index: word table at $15802.  Vertex: 8 bytes (x, y, z words, one pad word).  Edge: 4 bytes (two words,
  each = 8 * vertex index).  Face: 18-byte header (word 0 colour, 7 = $554 flag...), then nv vertex indices then ne edge indices.
Usage: models.py [snapshot] -> render/models.png and render/models.txt
"""
import os, sys
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import rcommon as R
HDR, TYPETAB, BASE = 0x15ada, 0x15802, 0x15caa

def parse(ram):
    def uw(a): return int.from_bytes(ram[a:a+2], 'big')
    def sw(a):
        v = uw(a); return v - 65536 if v >= 32768 else v
    models = {}
    for i in range(1, 29):
        h = HDR + 16 * i
        nv, ne, nf, ov, oe, of_, oend = [uw(h + 2 * k) for k in range(7)]
        verts = [(sw(BASE + ov + 8 * k), sw(BASE + ov + 8 * k + 2), sw(BASE + ov + 8 * k + 4), uw(BASE + ov + 8 * k + 6)) for k in range(nv)]
        edges = [(uw(BASE + oe + 4 * k) // 8, uw(BASE + oe + 4 * k + 2) // 8) for k in range(ne)]
        faces = []
        a = BASE + of_
        for k in range(nf):
            hd = [uw(a + 2 * j) for j in range(9)]
            nvx, nex = hd[7], hd[8]
            vl = [uw(a + 18 + 2 * j) for j in range(nvx)]
            el = [uw(a + 18 + 2 * nvx + 2 * j) for j in range(nex)]
            faces.append(dict(hdr=hd, v=vl, e=el))
            a += 18 + 2 * (nvx + nex)
        models[i] = dict(nv=nv, ne=ne, nf=nf, verts=verts, edges=edges, faces=faces, end=a - BASE, oend=oend)
    types = [uw(TYPETAB + 2 * t) for t in range(32)]
    return models, types

if __name__ == '__main__':
    snap = sys.argv[1] if len(sys.argv) > 1 else R.SNAP_GAME1
    ram = R.load_ram(snap)
    models, types = parse(ram)
    out = open(os.path.join(R.WORK, 'render', 'models.txt'), 'w')
    for i, m in models.items():
        ts = [t for t in range(32) if types[t] == i]
        cols = sorted(set(f['hdr'][0] for f in m['faces']))
        out.write(f"model {i:2d} types {ts} nv={m['nv']} ne={m['ne']} nf={m['nf']} faceend={m['end']:#x} hdr_end={m['oend']:#x} colours={cols}\n")
    out.close()
    print(open(os.path.join(R.WORK, 'render', 'models.txt')).read())

def sheet(ram, palette, out, cell=150, cols=7):
    import math
    from PIL import Image, ImageDraw
    models, types = parse(ram)
    rows = (len(models) + cols - 1) // cols
    img = Image.new('RGB', (cols * cell, rows * cell), (0, 0, 0))
    dr = ImageDraw.Draw(img)
    yaw, pitch = math.radians(35), math.radians(-20)
    cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    for n, (i, m) in enumerate(models.items()):
        ox, oy = (n % cols) * cell, (n // cols) * cell
        pts = []
        for (x, y, z, _) in m['verts']:
            x1, z1 = x * cy + z * sy, -x * sy + z * cy
            y2, z2 = y * cp - z1 * sp, y * sp + z1 * cp
            pts.append((x1, y2, z2))
        if not pts: continue
        ext = max(max(abs(p[0]), abs(p[1])) for p in pts) or 1
        s = (cell / 2 - 10) / ext
        col = m['faces'][0]['hdr'][0] if m['faces'] else 15
        rgb = palette[col] if col else (255, 255, 255)
        if rgb == (0, 0, 0): rgb = (255, 255, 255)
        for a, b in m['edges']:
            if a < len(pts) and b < len(pts):
                dr.line([ox + cell / 2 + pts[a][0] * s, oy + cell / 2 + pts[a][1] * s,
                         ox + cell / 2 + pts[b][0] * s, oy + cell / 2 + pts[b][1] * s], fill=rgb)
        ts = [t for t in range(32) if types[t] == i]
        dr.text((ox + 3, oy + 2), f"m{i} t{ts} v{m['nv']} e{m['ne']}", fill=(160, 160, 160))
    img.save(out)

def palette_of(snap):
    import gfxview
    regs = gfxview.load_video_regs(snap)
    def c(w): return (((w >> 8) & 7) * 36, ((w >> 4) & 7) * 36, (w & 7) * 36)
    return [c(w) for w in regs['palette_words']]

if __name__ == '__main__':
    sheet(ram, palette_of(snap), os.path.join(R.WORK, 'render', 'models.png'))
    print('wrote models.png')
