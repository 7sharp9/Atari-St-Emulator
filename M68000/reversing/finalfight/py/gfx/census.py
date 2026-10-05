"""census.py: which palette line each tile code is drawn with, over every (work RAM, gfx RAM) dump pair under
scratchpad/finalfight (find '*_gfxram.bin' with a sibling '*_ram.bin', one per distinct gfx RAM content).
For the three tile layers the map entries (code, attr & 0x1f), for sprites the object entries of both buffers
(code, attr & 0x1f, blocked sprites expanded).  Result: usage.pkl {kind: {code: (count, line, dump index)}},
palettes (n x 0xc00 x 3) and the dump names.  Kinds: 's1' (8x8, map code), 's2', 's3', 'spr'.
Run: python census.py   (about 40 s)."""
import glob, hashlib, os, pickle, sys
import numpy as np
from cpsgfx import *

G = None


def dumps():
    seen = set()
    out = []
    pats = [os.path.join(SCR, "**", "*_gfxram.bin")]
    for p in sorted(glob.glob(pats[0], recursive=True)):
        r = p[:-len("_gfxram.bin")] + "_ram.bin"
        if not os.path.exists(r):
            continue
        h = hashlib.md5(open(p, "rb").read()).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        out.append((p, r))
    return out


def main():
    global G
    G = Gfx()
    ds = dumps()
    use = {"s1": {}, "s2": {}, "s3": {}, "spr": {}}
    pals = []
    names = []
    for di, (gp, rp) in enumerate(ds):
        g = np.fromfile(gp, dtype=">u2")
        ram = np.fromfile(rp, dtype=">u2")
        regs = regs_from_ram(ram)
        pal = build_palette(g[cps_base(regs.a[A_PAL], 0x400) // 2:][:0xc00], 0x3f)
        pals.append(pal)
        names.append(os.path.relpath(gp, SCR))
        for L, kind in ((1, "s1"), (2, "s2"), (3, "s3")):
            code, attr = tile_grid(L, g, cps_base(regs.a[(A_S1B, A_S2B, A_S3B)[L - 1]], 0x4000))
            if L == 3:
                code = code & 0x3fff
            line = attr & 0x1f
            keys = code * 64 + line
            u, c = np.unique(keys, return_counts=True)
            for k, n in zip(u.tolist(), c.tolist()):
                cd, ln = divmod(k, 64)
                cur = use[kind].get(cd)
                if cur is None or n > cur[0]:
                    use[kind][cd] = (n, ln, di)
        for base in (0x0, 0x4000):
            ob = g[base // 2:base // 2 + 0x400].astype(int).reshape(-1, 4)
            for e in ob:
                if (e[3] & 0xff00) == 0xff00:
                    break
                for (c, col, fx, fy, sx, sy) in sprite_tiles(int(e[0]), int(e[1]), int(e[2]), int(e[3])):
                    cur = use["spr"].get(c)
                    if cur is None or cur[0] < 1:
                        use["spr"][c] = (1, col, di)
                    else:
                        use["spr"][c] = (cur[0] + 1, cur[1], cur[2]) if cur[1] == col else cur
    pickle.dump(dict(use=use, pals=np.stack(pals), names=names), open(os.path.join(OUT, "usage.pkl"), "wb"))
    print("dumps", len(ds), {k: len(v) for k, v in use.items()})


if __name__ == "__main__":
    main()
