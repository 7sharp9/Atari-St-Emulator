#!/usr/bin/env python3
"""Build and check reversing/populous/landscape_infographic.html.

Usage (from M68000/):
  uv run python reversing/populous/py/landscape_infographic.py            # check, then build the page
  uv run python reversing/populous/py/landscape_infographic.py --check    # check only

The page runs py/landscape_core.js, a JS port of the landscape code. --check proves the port
against the Python models that are themselves proven against the emulator (terrain.md,
graphics.md), by running landscape_check.js in node on random states and comparing:

  gen     genWorld            vs popgen.build_world           heights, alt, shape, feat, seed
  replay  replayWorld        rebuilds genWorld's heights, alt, shape and feat from the recorded log and
                              scatter placements (the page's generation scrubber, final stage)
  cmd     cmdRaise/cmdLower   vs powers_ref raise/lower + $c0ee     whole maps, corner-change count
  power   earthquake, volcano, swamp, flood vs powers_ref       whole maps, seed, RNG draw count
  render  renderTerrain       vs pop_render.Frame.terrain       every pixel of the 320x200 frame
  corner  cornerAt            vs popdrive.Game.corner_at        corner and highlight y

It exits non-zero on any mismatch. The build embeds the counts in the page.
Needs: node, $POP_WORK (M68000/scratchpad/pop) with files/ and game_start.snap.
"""
import json
import os
import random
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "powers"))
sys.setrecursionlimit(100000)

import popgen                      # noqa: E402
import pop_assets as A             # noqa: E402
import pop_render as R             # noqa: E402
import popdrive                    # noqa: E402
from popcfg import WORK            # noqa: E402
from snapram import ram as snap_ram  # noqa: E402
import powers_ref as P             # noqa: E402

OUT = os.path.normpath(os.path.join(HERE, "..", "landscape_infographic.html"))
TMPL = os.path.join(HERE, "landscape_infographic.tmpl.html")
CORE = os.path.join(HERE, "landscape_core.js")

# Worlds whose generation is byte-identical to the emulator (terrain.md section 3, verify_gen.py).
PRESETS = [
    {"name": "GENESIS", "desc": "conquest world 0 (LEVEL record 0)", "seed": 0x6302, "pre": 4, "land": 0},
    {"name": "SADINDON", "desc": "conquest world 1235 (desert)", "seed": 0x0454, "pre": 4, "land": 1},
    {"name": "Custom $1234", "desc": "a number typed at the world dialog; the coin flip made it desert", "seed": 0x1234, "pre": 5, "land": 1},
]


def enc(img):
    return "".join("." if c < 0 else "%x" % c for row in img for c in row)


def export_data():
    lands = []
    for n in range(4):
        hdr, _ = A.land_raw(n)
        lands.append({"blocks": [enc(b) for b in A.land_blocks(n)], "mm": list(hdr[0x60:0x70])})
    spr = A.sprites16()
    return {
        "pal": A.GAMEPAL,
        "lands": lands,
        "spr76": enc(spr[76]),
        "spr77": enc(spr[77]),
        "presets": PRESETS,
    }


# ------------------------------------------------------------------ state <-> RAM image
def state_of_world(wd):
    return {"seed": wd.seed, "h": list(wd.h), "alt": list(wd.alt), "shape": list(wd.shape), "feat": list(wd.feat)}


def put_state(m, st, paint=True):
    """Write a world state into a RAM image, with no people: no leader, no magnets, no occupants."""
    struct.pack_into(">4225h", m, P.HGT, *st["h"])
    m[P.ALT:P.ALT + 4096] = bytes(st["alt"])
    m[P.SHAPE:P.SHAPE + 4096] = bytes(st["shape"])
    m[P.FEAT:P.FEAT + 4096] = bytes(st["feat"])
    m[P.OCC:P.OCC + 4096] = bytes(4096)
    for a in (P.SIDE, P.SIDE + 2, P.SIDE + 16, P.SIDE + 18):
        P.ww(m, a, 0)
    P.ww(m, P.SEED, st["seed"])
    P.ww(m, P.PAINT, 1 if paint else 0)       # paint-map mode passes the power gate
    P.ww(m, P.PAUSE, 0)
    P.ww(m, P.ARMA, 0)
    P.ww(m, P.POINTS, 0)


def get_state(m):
    return {"seed": P.ruw(m, P.SEED),
            "h": list(struct.unpack_from(">4225h", m, P.HGT)),
            "alt": list(m[P.ALT:P.ALT + 4096]),
            "shape": list(m[P.SHAPE:P.SHAPE + 4096]),
            "feat": list(m[P.FEAT:P.FEAT + 4096])}


def scribble(st, rnd):
    """Make a state that is not just generator output: random legal raise/lower ops and odd cell codes."""
    wd = popgen.World(st["seed"])
    wd.h = list(st["h"]); wd.alt = list(st["alt"]); wd.shape = list(st["shape"]); wd.feat = list(st["feat"])
    for _ in range(rnd.randint(0, 12)):
        x, y = rnd.randint(0, 64), rnd.randint(0, 64)
        (wd.raise_pt if rnd.random() < 0.6 else wd.lower_pt)(x, y)
    wd.tiles(0, 0, 63, 63)
    for _ in range(rnd.randint(0, 60)):
        c = rnd.randrange(4096)
        wd.shape[c] = rnd.choice([0x0f, 0x1f, 0x20, 0x42, 0x2f, 0x35, 0x30])
        if rnd.random() < 0.3:
            wd.feat[c] = rnd.choice([0x32, 0x33, 0x34, 0x22, 0])
    return {"seed": rnd.randint(0, 0x7fff), "h": wd.h, "alt": wd.alt, "shape": wd.shape, "feat": wd.feat}


def diff_state(a, b, keys=("seed", "h", "alt", "shape", "feat")):
    return [k for k in keys if a[k] != b[k]]


def random_world(rnd):
    seed, pre = rnd.randint(0, 0x7fff), rnd.choice([4, 5])
    return state_of_world(popgen.build_world(seed, pre))


# ------------------------------------------------------------------ the check
def check(verbose=True):
    if not os.path.exists(os.path.join(WORK, "game_start.snap")):
        sys.exit("need %s/game_start.snap (README: rebuild the working data)" % WORK)
    rnd = random.Random(20260930)
    data = export_data()
    base_ram = bytearray(snap_ram(os.path.join(WORK, "game_start.snap")))
    tests, meta = [], []           # meta[i] = (group, expected, info)

    # gen: named presets, then random seeds
    cases = [(p["seed"], p["pre"]) for p in PRESETS] + [(rnd.randint(0, 0x7fff), rnd.choice([4, 5])) for _ in range(100)]
    for seed, pre in cases:
        tests.append({"kind": "gen", "seed": seed, "pre": pre})
        meta.append(("gen", state_of_world(popgen.build_world(seed, pre)), (seed, pre)))
    # replay log: the recorded corner changes rebuild the heights (internal consistency of the scrubber)
    for seed, pre in cases[:30]:
        tests.append({"kind": "genrec", "seed": seed, "pre": pre})
        meta.append(("replay", None, (seed, pre)))

    # cmd: raise/lower a random corner, including peaks (big cascades) and sea
    for i in range(80):
        st = scribble(random_world(rnd), rnd)
        op = "raise" if i % 2 == 0 else "lower"
        if i % 4 < 2:                       # aim at a high corner to get a long cascade
            hi = max(range(4225), key=lambda k: (st["h"][k], rnd.random()))
            x, y = hi % 65, hi // 65
        else:
            x, y = rnd.randint(0, 64), rnd.randint(0, 64)
        m = base_ram
        put_state(m, st)
        P.ww(m, P.POINTS, 0)
        for a, v in zip(P.BOX, (x, x, y, y)):
            P.ww(m, a, v)
        (P.raise_point if op == "raise" else P.lower_point)(m, x, y)
        P._clamp_box_derive(m)
        exp = get_state(m); exp["points"] = P.rw(m, P.POINTS); exp["cost"] = 4 * exp["points"] + 10
        tests.append({"kind": "cmd", "op": op, "x": x, "y": y, "state": st})
        meta.append(("cmd", exp, (op, x, y)))

    # powers
    def power_case(op, n):
        for _ in range(n):
            st = scribble(random_world(rnd), rnd)
            x, y = rnd.randint(0, 56), rnd.randint(0, 56)
            m = base_ram
            put_state(m, st)
            if op == "flood":
                P.flood(m, 0)
            elif op == "eq":
                P.earthquake(m, 0, x, y)
            elif op == "volcano":
                P.volcano(m, 0, x, y)
            elif op == "swamp":
                P.swamp(m, 0, x, y)
            exp = get_state(m)
            tests.append({"kind": "power", "op": op, "x": x, "y": y, "state": st})
            meta.append(("power:" + op, exp, (x, y)))
    for op, n in (("eq", 40), ("volcano", 40), ("swamp", 40), ("flood", 20)):
        power_case(op, n)

    # render: generated worlds on all four lands, plus the real game_start maps
    fr = R.Frame(os.path.join(WORK, "game_start.snap"))
    blocks_py = [A.land_blocks(n) for n in range(4)]
    gs =bytearray(snap_ram(os.path.join(WORK, "game_start.snap")))
    real = {"seed": P.ruw(gs, P.SEED), "h": list(struct.unpack_from(">4225h", gs, P.HGT)),
            "alt": list(gs[P.ALT:P.ALT + 4096]), "shape": list(gs[P.SHAPE:P.SHAPE + 4096]),
            "feat": list(gs[P.FEAT:P.FEAT + 4096])}
    rcases = []
    for i in range(12):
        st = random_world(rnd) if i % 3 else scribble(random_world(rnd), rnd)
        rcases.append((st, i % 4, rnd.randint(0, 56), rnd.randint(0, 56), i % 2))
    for i in range(4):                      # the real game_start world, four views
        rcases.append((real, 0, [0, 5, 12, 56][i], [0, 9, 16, 56][i], i % 2))
    for st, land, cx, cy, shim in rcases:
        m = bytearray(snap_ram(os.path.join(WORK, "game_start.snap")))
        put_state(m, st)
        m[R.ENTMAP:R.ENTMAP + 4096] = bytes(4096)
        P.ww(m, 0x3d526, 0); P.ww(m, 0x3c4ca, 0)
        fr.m = R.Mem(m); fr.blocks = blocks_py[land]
        fr.cx, fr.cy, fr.shim, fr.org = cx, cy, shim, 0x2858
        scr = R.Screen([[-1] * 320 for _ in range(200)])
        fr.terrain(scr)
        pix = bytes(255 if c < 0 else c for row in scr.p for c in row)
        tests.append({"kind": "render", "land": land, "cx": cx, "cy": cy, "shim": shim, "state": st})
        meta.append(("render", pix.hex(), (land, cx, cy, shim)))

    # corner picking: a grid of pointer positions over several heights fields and view origins
    for _ in range(6):
        st = scribble(random_world(rnd), rnd)
        ox, oy = rnd.randint(0, 56), rnd.randint(0, 56)
        g = popdrive.Game(bytes(base_ram))
        g.h = list(st["h"])
        pts = [[x, y] for x in range(0x40, 320, 3) for y in range(0, 200, 3)]
        exp = []
        for x, y in pts:
            r = g.corner_at(x, y, (ox, oy)) if g.land_ok(x, y) else None
            exp.append(None if r is None else [r[0][0], r[0][1], r[1]])
        tests.append({"kind": "corner", "ox": ox, "oy": oy, "pts": pts, "state": st})
        meta.append(("corner", exp, len(pts)))

    with tempfile.TemporaryDirectory() as td:
        fin, fout = os.path.join(td, "in.json"), os.path.join(td, "out.json")
        json.dump({"data": data, "tests": tests}, open(fin, "w"))
        subprocess.run(["node", os.path.join(HERE, "landscape_check.js"), fin, fout], check=True)
        got = json.load(open(fout))

    tally = {}
    bad = []
    for (group, exp, info), g in zip(meta, got):
        ok, n = True, 1
        if group == "gen":
            ok = not diff_state(exp, g)
        elif group == "replay":
            ok = g["h"] == g["replay"] and g["nlog"] == g["lastCum"] and g["ncl"] == 22 and g["full"] and g["noScatter"]
        elif group == "cmd":
            ok = not diff_state(exp, g, ("h", "alt", "shape", "feat")) and exp["points"] == g["points"] and exp["cost"] == g["cost"]
        elif group.startswith("power"):
            ok = not diff_state(exp, g)
        elif group == "render":
            ok = exp == g["pix"]
        elif group == "corner":
            ok = exp == g["res"]
            n = info
            if ok:
                t = tally.setdefault(group, [0, 0, 0])
                t[0] += 1; t[1] += 1; t[2] += sum(1 for r in exp if r)
                continue
        t = tally.setdefault(group, [0, 0, 0])
        t[0] += 1 if ok else 0
        t[1] += 1
        if not ok:
            bad.append((group, info, diff_state(exp, g) if isinstance(exp, dict) else ""))
    if verbose:
        for grp, (a, b, c) in sorted(tally.items()):
            extra = "  (%d pointer positions hit a corner)" % c if grp == "corner" else ""
            print("%-14s %d/%d%s" % (grp, a, b, extra))
        for b in bad[:10]:
            print("MISMATCH", b)
    if bad:
        sys.exit(1)
    return {k: [v[0], v[1]] for k, v in tally.items()}, data


def build(proof, data):
    if not os.path.exists(TMPL):
        print("no template yet; check only")
        return
    data = dict(data)
    data["proof"] = proof
    page = open(TMPL).read()
    page = page.replace("/*__CORE__*/", open(CORE).read())
    page = page.replace("__DATA__", json.dumps(data, separators=(",", ":")))
    open(OUT, "w").write(page)
    print("wrote %s (%d KB)" % (OUT, len(page) // 1024))


if __name__ == "__main__":
    proof, data = check()
    if "--check" not in sys.argv:
        build(proof, data)
