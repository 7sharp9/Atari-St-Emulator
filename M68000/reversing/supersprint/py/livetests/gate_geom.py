"""gate_geom.py - where each gate sits: diff collision plane 1 (-94(A4)+8000, 8000 B, 1 bpp, 40-byte stride) between the gate fully
closed (pos 0) and fully open (pos 4), per track, from the live race.  Prints the bounding boxes (px) of the differing pixels
per connected cluster and writes data/gate_geom.json."""
from lt import *
import numpy as np
SN = os.path.join(sscfg.WORK, 'agents', 'tracks', 'snaps')
def plane(r):
    p = struct.unpack('>I', r.mem(A4 - 94, 4))[0]
    b = bytearray()
    for o in range(0, 8000, 1000): b += r.mem(p + 8000 + o, 1000)
    return np.unpackbits(np.frombuffer(bytes(b), dtype=np.uint8)).reshape(200, 320)
res = {}
for T in (2, 4, 7):
    r = Repl2(os.path.join(SN, 'race_%d.snap' % T)); r.cmd('s 3000000')
    ng = r.a4w(-1808, 1)[0]
    seen = {}
    for f in range(1500):
        out, _ = r.cmd('bp df18 400000')
        pos = r.a4w(-1820, 3); dr = r.a4w(-1814, 3)
        for g in range(ng):
            if dr[g] == 0 and pos[g] in (0, 4) and (g, pos[g]) not in seen:
                seen[(g, pos[g])] = plane(r)
        if all((g, p) in seen for g in range(ng) for p in (0, 4)): break
    # with several gates moving at once we only keep snapshots with all gates idle: relax if needed
    r.close()
    print('T', T, 'captured', sorted(seen))
    res[T] = seen
    boxes = []
    for g in range(ng):
        d = seen[(g, 0)] != seen[(g, 4)]
        lab = np.zeros(d.shape, int); n = 0; comps = []
        for y0, x0 in zip(*np.nonzero(d)):
            if lab[y0, x0]: continue
            n += 1; st = [(y0, x0)]; lab[y0, x0] = n; pts = []
            while st:
                y, x = st.pop(); pts.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < 200 and 0 <= xx < 320 and d[yy, xx] and not lab[yy, xx]:
                            lab[yy, xx] = n; st.append((yy, xx))
            comps.append(pts)
        comps.sort(key=len, reverse=True)
        big = [c for c in comps if len(c) >= 100]
        for c in big:
            ys = [p[0] for p in c]; xs = [p[1] for p in c]
            print('  gate %d: component %d px bbox x %d..%d y %d..%d (closed plane has %d set px of those, open %d)' % (g, len(c), min(xs), max(xs), min(ys), max(ys), sum(seen[(g, 0)][y, x] for y, x in c), sum(seen[(g, 4)][y, x] for y, x in c)))
            boxes.append((g, int(min(xs)), int(max(xs)), int(min(ys)), int(max(ys))))
    res[T] = {'bbox': boxes}
json.dump({str(k): (v if 'bbox' in v else None) for k, v in res.items() if isinstance(v, dict) and 'bbox' in v}, open(os.path.join(DATA, 'gate_geom.json'), 'w'))
