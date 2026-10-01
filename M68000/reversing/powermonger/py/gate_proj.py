"""140th: the projectile loop `$596a` (`pm_fsm_ref.call_596a`, with `call_4624`, `_proj_end`, `_proj_area`) against the real 68000
through `callcap 596a` on entries captured by `proj_scan.py` / `proj_corpus.py` (natural entries of lands 0, 5, 25 and 60 with a
live slot) and, with `synth`, on synthetic states (a poked slot: type `$12` area effect on a cell holding a building, a building going
up, a tree and a man; an arrow on a pigeon, a marker, a man).

Compared: every byte the real call changed against every byte the model changed, over the whole of RAM except the stack
(`$2c800..$2c930`).  A byte missing on either side is a mismatch.

    cd M68000 && python reversing/powermonger/py/gate_proj.py [name-substring] [synth]
"""
import collections
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(ROOT / "tools"))
import pm_fsm_ref as P
from pm_fsm_diff import Harness

C = "scratchpad/pm140/proj/corpus"
OUT = "scratchpad/pm140/proj/g"
STACK = (0x2c800, 0x2c930)
(ROOT / OUT).mkdir(parents=True, exist_ok=True)
args = [a for a in sys.argv[1:] if a not in ("synth", "reuse")]
only = args[0] if args else None
snaps = sorted((ROOT / C).glob("*/*.snap"))
anchor = snaps[0]
h = Harness(str(anchor.relative_to(ROOT)), str(anchor.with_suffix(".ram").relative_to(ROOT)),
            disk="scratchpad/powermonger.st", out_dir=OUT)
tot = ok = n = 0
arms, fails, excluded = collections.Counter(), [], []
for sn in snaps:
    name = f"{sn.parent.name}/{sn.stem}"
    if only and only not in name:
        continue
    ram0 = sn.with_suffix(".ram").read_bytes()
    out = ROOT / OUT / f"o_{sn.stem}.json"
    if not (out.exists() and "reuse" in sys.argv):
        out.unlink(missing_ok=True)
        h.run_repl([f"callcap 596a 2000000 {OUT}/o_{sn.stem}.json"], str(sn.relative_to(ROOT)))
    j = json.load(open(out))
    if j.get("outcome") != "returned":
        fails.append((name, "outcome", j.get("outcome")))
        continue
    real = {a: b1 for a, b0, b1 in j["mem"] if not STACK[0] <= a < STACK[1]}
    P.init_tables(ram0)
    m = P.Mem(ram0)
    P.PROJ_TRACE.clear()
    try:
        P.call_596a(m)
    except AssertionError as e:
        excluded.append((name, str(e)[:60]))
        continue
    model = {a: m.r[a] for a in range(len(ram0)) if m.r[a] != ram0[a] and not STACK[0] <= a < STACK[1]}
    keys = set(real) | set(model)
    bad = [a for a in keys if real.get(a, ram0[a]) != model.get(a, ram0[a])]
    arms.update(P.PROJ_TRACE)
    tot += len(keys)
    ok += len(keys) - len(bad)
    n += 1
    if bad:
        fails.append((name, [(hex(a), real.get(a, ram0[a]), model.get(a, ram0[a])) for a in sorted(bad)[:8]], dict(collections.Counter(P.PROJ_TRACE))))

if "synth" in sys.argv:
    import struct
    BASES = ["k5_00/k5_00_59", "k25_s3/k25_s3_90", "k60_s4/k60_s4_238", "k0_s3/k0_s3_150"]
    OBJ = P.OBJ

    def free_slot(m):
        for a in range(P.PROJ, P.PROJ_END, 16):
            if m.wu(a + 14) == 0:
                return a
        raise RuntimeError("no free effect slot")

    def men(m, owner=None):
        out = []
        for s_ in range(1, 512):
            a = OBJ + s_ * 50
            if m.bu(a + 6) == 0 and 0 < m.bu(a + 5) < 128 and (owner is None or m.bu(a + 5) == owner):
                out.append(a)
        return out

    def plant(m, T, shooter, typ, life, vx=0, vy=0, dx=0, dy=0):
        a = free_slot(m)
        for i in range(16):
            m.wb(a + i, 0)
        m.wb(a + 4, vx)
        m.wb(a + 5, vy)
        m.wb(a + 6, typ)
        m.ww(a + 8, m.wu(T + 8) - dx)
        m.ww(a + 10, m.wu(T + 10) - dy)
        m.ww(a + 12, (shooter - OBJ) & 0xffff)
        m.ww(a + 14, life)
        P.call_16808(m, P._cell_5bac(m, a), (a - OBJ) & 0xffff)
        return a

    def linked(m, cat, owner_pos=True):
        """Records of a category that sit in a bucket chain (buildings, trees and markers live below OBJ)."""
        out = []
        for cell in range(0x2000):
            d = m.wu(P.BUCKETS + 2 * cell)
            n = 0
            while d and n < 64:
                a = (OBJ + P.s16(d)) & 0xfffff
                if m.bu(a + 6) == cat and (not owner_pos or 0 < m.bu(a + 5) < 128):
                    out.append(a)
                d = m.wu(a)
                n += 1
        return out

    def pick_target(m, kind):
        """A target of the kind, with room in its cell for dx/dy, and a shooter of another side."""
        if kind == "man":
            c = men(m)
        else:
            c = linked(m, 0x14 if kind == "pigeon" else 0x16)
        c = [a for a in c if (m.wu(a + 8) & 0xff) >= 0x10 and (m.wu(a + 10) & 0xff) >= 0x16]
        T = c[0]
        S = next(a for a in men(m) if m.bu(a + 5) != m.bu(T + 5))
        return T, S

    cases = []
    for health in (0x60, 0x30, 0x90, 0x52, 0x53, 0x00, 0x7f, 0x80):
        cases.append((f"man_h{health:02x}", "man", lambda m, T, S, h_=health: (m.wb(T + 45, h_), plant(m, T, S, 0x28, 5))))
    for dx, dy, nm in ((15, 21, "edge_in"), (16, 0, "dx_out"), (0, 22, "dy_out")):
        cases.append((f"man_{nm}", "man", lambda m, T, S, dx_=dx, dy_=dy: (m.wb(T + 45, 0x60), plant(m, T, S, 0x28, 5, dx=dx_, dy=dy_))))
    cases.append(("man_same_side", "man", lambda m, T, S: plant(m, T, next(a for a in men(m, m.bu(T + 5)) if a != T), 0x28, 5)))
    cases.append(("man_dead", "man", lambda m, T, S: (m.wb(T + 5, 0xff), plant(m, T, S, 0x28, 5))))
    cases.append(("man_life1", "man", lambda m, T, S: (m.wb(T + 45, 0x60), plant(m, T, S, 0x28, 1))))
    cases.append(("man_shooter_cool", "man", lambda m, T, S: (m.wb(S + 31, 0x34), m.wb(S + 18, 9), m.wb(T + 45, 0x60), plant(m, T, S, 0x28, 1))))
    cases.append(("pigeon_hit", "pigeon", lambda m, T, S: plant(m, T, S, 0x28, 5)))
    cases.append(("pigeon_miss", "pigeon", lambda m, T, S: plant(m, T, S, 0x28, 5, dx=16)))
    cases.append(("pigeon_moving", "pigeon", lambda m, T, S: plant(m, T, S, 0x28, 5, vx=0x05, vy=0xfb, dx=5, dy=-5 & 0xffff)))
    def local_rider(m, T, S, count):
        """The pigeon's rider (word 20) is a man of the local side with a group: `$4624` decrements the group's pending counter."""
        # a group offset: word 42 of a farmer is its field cell, and an odd remainder is an address error on the real CPU
        rider = next(a for a in men(m, m.bu(P.LOCAL_SIDE + 1)) if m.wu(a + 42) != 0 and ((m.wu(a + 42) - 0x4c) & 0xffff) % 0x13c < 0x20
                     and (((m.wu(a + 42) - 0x4c) & 0xffff) % 0x13c) % 2 == 0)
        m.ww(T + 20, (rider - OBJ) & 0xffff)
        k2 = ((m.wu(rider + 42) - 0x4c) & 0xffff) % 0x13c
        m.ww(P.PENDING + k2, count)
        plant(m, T, next(a for a in men(m) if m.bu(a + 5) != m.bu(T + 5)), 0x28, 5)

    cases.append(("pigeon_local_rider", "pigeon", lambda m, T, S: local_rider(m, T, S, 3)))
    cases.append(("pigeon_local_rider_zero", "pigeon", lambda m, T, S: local_rider(m, T, S, 0)))
    cases.append(("pigeon_no_rider", "pigeon", lambda m, T, S: (m.ww(T + 20, 0), plant(m, T, S, 0x28, 5))))
    cases.append(("marker_hit", "marker", lambda m, T, S: plant(m, T, S, 0x28, 5)))
    cases.append(("marker_miss", "marker", lambda m, T, S: plant(m, T, S, 0x28, 5, dy=22)))
    cases.append(("arrow_walks_in", "man", lambda m, T, S: (m.wb(T + 45, 0x60), plant(m, T, S, 0x28, 5, vx=0x08, vy=0x04, dx=8, dy=4))))
    cases.append(("arrow_clamp_x", "man", lambda m, T, S: plant(m, T, S, 0x28, 5, vx=0x7f, vy=0x7f)))
    cases.append(("fade", "man", lambda m, T, S: plant(m, T, S, 0x12, 0xfffd)))
    cases.append(("fade_last", "man", lambda m, T, S: plant(m, T, S, 0x12, 0xffff)))
    cases.append(("area_flight", "man", lambda m, T, S: plant(m, T, S, 0x12, 3, vx=3, vy=3)))
    cases.append(("area_empty", "man", lambda m, T, S: plant(m, T, S, 0x12, 1, vx=0x7f, vy=0x7f)))
    cases.append(("area_man", "man", lambda m, T, S: plant(m, T, S, 0x12, 1)))
    for kind in (2, 0x10, 4):
        def mk(kind_):
            def f(m, T, S):
                R = linked(m, kind_, owner_pos=False)[0]
                return plant(m, R, S, 0x12, 1)
            return f
        cases.append((f"area_cat{kind:x}", "man", mk(kind)))
    sn = 0
    for base in BASES:
        sp = ROOT / C / f"{base}.snap"
        if not sp.exists():
            continue
        ram0 = sp.with_suffix(".ram").read_bytes()
        for cname, kind, build in cases:
            if only and only not in f"{base}/{cname}":
                continue
            P.init_tables(ram0)
            m1 = P.Mem(ram0)
            try:
                T, S = pick_target(m1, kind)
                build(m1, T, S)
            except (StopIteration, IndexError, RuntimeError) as e:
                print(f"  synth {base} {cname}: no such state ({type(e).__name__})")
                continue
            pairs = {a: m1.r[a] for a in range(len(ram0)) if m1.r[a] != ram0[a]}
            pokes = Harness.bytepokes(ram0, pairs)
            ram1 = Harness.poked_ram(ram0, pokes)
            tag = f"s_{base.replace('/', '_')}_{cname}"
            cmds = [f"w {a:x} {w:08x}" for a, w in pokes] + [f"callcap 596a 2000000 {OUT}/o_{tag}.json"]
            (ROOT / OUT / f"s_{tag}.cmds").write_text("\n".join(cmds) + "\nq\n")
            if not ((ROOT / OUT / f"o_{tag}.json").exists() and "reuse" in sys.argv):
                h.run_repl(cmds, str(sp.relative_to(ROOT)))
            j = json.load(open(ROOT / OUT / f"o_{tag}.json"))
            if j.get("outcome") != "returned":
                fails.append((tag, "outcome", j.get("outcome")))
                continue
            real = {a: b1 for a, b0, b1 in j["mem"] if not STACK[0] <= a < STACK[1]}
            m = P.Mem(ram1)
            P.PROJ_TRACE.clear()
            try:
                P.call_596a(m)
            except AssertionError as e:
                excluded.append((tag, str(e)[:60]))
                continue
            model = {a: m.r[a] for a in range(len(ram1)) if m.r[a] != ram1[a] and not STACK[0] <= a < STACK[1]}
            keys = set(real) | set(model)
            bad = [a for a in keys if real.get(a, ram1[a]) != model.get(a, ram1[a])]
            arms.update(P.PROJ_TRACE)
            tot += len(keys)
            ok += len(keys) - len(bad)
            n += 1
            sn += 1
            if bad:
                fails.append((tag, [(hex(a), real.get(a, ram1[a]), model.get(a, ram1[a])) for a in sorted(bad)[:8]], dict(collections.Counter(P.PROJ_TRACE))))
    print(f"synthetic states {sn}")
print(f"states {n} (excluded {len(excluded)}), changed bytes compared {ok}/{tot}, arms {dict(arms)}")
for e in excluded[:10]:
    print("  excluded", e)
for f in fails[:20]:
    print("  FAIL", f)
print("PASS" if not fails else "FAIL")
sys.exit(1 if fails else 0)
