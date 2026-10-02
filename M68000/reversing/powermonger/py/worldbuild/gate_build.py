"""141st, `build`: differential gate of build_ref.py against the real 68000 (`callcap <routine>` from a snapshot stopped at the
routine's natural entry in a land build, with labelled synthetic pokes for the arms no natural build reaches).

    cd M68000 && .venv/bin/python reversing/powermonger/py/worldbuild/gate_build.py [d1e|forest|kings|water|town|addrank|derank|towns|townnat|all] [substr] [reuse]

Entry snapshots (written to WORK/cap, WORK = scratchpad/pm141/agents/build, override with PM_WORK): `cap_land.sh <k>` (pm67_ok_pre + the build_land.sh pokes for land k, `bpc` at the routine's first hit).
Compared: every RAM byte the real call changed against every byte the model changed, except the stack ($2c800..$2c930) and the
terrain planes $3f86c..$47970 in the d1e gate only ($ffa6/$10410 write them; `maps_ref`/`gate_maps.py` own those); every other gate
compares the planes too (the flag bits `$2eac` sets, the levelling `$10638` does through `maps_ref`).  A byte missing on either side
is a mismatch.  Prints matched/total bytes and the arms exercised.
"""
import collections
import json
import os
import struct
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT") or Path(__file__).resolve().parents[4])
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools"))
from disassemble import ram_from_snap
import build_ref as B
from build_ref import Mem

WORK = ROOT / os.environ.get("PM_WORK", "scratchpad/pm141/agents/build")   # captures and callcap outputs: gitignored scratchpad
DATA = WORK
CAP = DATA / "cap"
OUT = DATA / "gate"
OUT.mkdir(exist_ok=True)
DISK = "scratchpad/powermonger.st"
ENV = dict(os.environ, ATARI_NOTRACE="1")
LANDS = [0, 1, 2, 3, 5, 7, 10, 12, 15, 25, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 135, 140, 142]
MASK = [(0x2c800, 0x2c930)]                      # the stack
PLANES = [(0x3f86c, 0x47970)]                    # altitude, colour, flag planes: $ffa6/$10410 write them (d1e gate masks them)
args = [a for a in sys.argv[1:] if a != "reuse"]
REUSE = "reuse" in sys.argv


# the panel redraw `$187d8` (its tracked part, the group selection, is modelled): screen, the icon buffer and a few UI/sound words
UI_MASK = [(0x78000, 0x80000), (0x1c000, 0x24000), (0xe100, 0xe200), (0x1af00, 0x1b000), (0x1ff00, 0x20000),
           (0x2c000, 0x2c930), (0x2c990, 0x2c9a0), (0x2cba0, 0x2cbb0)]
MASK_ON = [MASK]


def masked(a):
    return any(lo <= a < hi for lo, hi in MASK_ON[0])


def bytepokes(ram, edits):
    """{addr: byte} -> longword pokes at aligned bases (the REPL `w` writes 4 bytes)."""
    buf = bytearray(ram)
    bases = set()
    for a, v in edits.items():
        buf[a] = v & 0xff
        bases.add(a & ~3)
    return [(b, struct.unpack_from(">I", buf, b)[0]) for b in sorted(bases)]


def real_delta(snap, pokes, target, out, steps=6_000_000, presets=""):
    if not (REUSE and out.exists()):
        out.unlink(missing_ok=True)
        cmds = [f"w {a:x} {w:08x}" for a, w in pokes] + [f"callcap {target} {steps} {out.relative_to(ROOT).as_posix()}{presets}", "q"]
        subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", str(snap.relative_to(ROOT)), "repl", "--disk-a", DISK],
                       input="\n".join(cmds) + "\n", capture_output=True, text=True, cwd=ROOT, env=ENV, timeout=900)
    return json.load(open(out))


def poked(ram, pokes):
    r = bytearray(ram)
    for a, w in pokes:
        struct.pack_into(">I", r, a, w)
    return r


class Case:
    def __init__(self, name, snap, edits=None, model=None, target=None, tag="", presets=""):
        self.name, self.snap, self.edits, self.model, self.target, self.tag, self.presets = name, snap, edits or {}, model, target, tag, presets


def run_cases(cases, trace_lists, steps=6_000_000):
    """Run every case (emulator calls in parallel), diff with the model, return (ok, total, n, fails, arms)."""
    rams = {}

    def prep(c):
        if c.snap not in rams:
            rams[c.snap] = bytes(ram_from_snap(str(c.snap)))
        ram0 = rams[c.snap]
        c.pokes = bytepokes(ram0, c.edits)
        c.ram0 = poked(ram0, c.pokes)
        c.out = OUT / f"o_{c.name}.json"
        return c

    for c in cases:
        prep(c)
    with ThreadPoolExecutor(max_workers=4) as ex:
        res = list(ex.map(lambda c: real_delta(c.snap, c.pokes, c.target, c.out, steps, c.presets), cases))
    tot = ok = n = 0
    fails, arms = [], collections.Counter()
    for c, j in zip(cases, res):
        if j.get("outcome") != "returned":
            fails.append((c.name, "outcome", j.get("outcome"), j.get("steps")))
            continue
        sp = j["entrySP"]
        real = {a: b1 for a, b0, b1 in j["mem"] if not masked(a) and not sp - 0x600 <= a < sp + 0x20}   # the callee stack
        m = Mem(c.ram0)
        for t in trace_lists:
            t.clear()
        try:
            ret = c.model(m)
        except AssertionError as e:
            fails.append((c.name, "assert", str(e)[:80]))
            continue
        model = {a: m.r[a] for a in range(len(c.ram0)) if m.r[a] != c.ram0[a] and not masked(a) and not sp - 0x600 <= a < sp + 0x20}
        keys = set(real) | set(model)
        bad = [a for a in keys if real.get(a, c.ram0[a]) != model.get(a, c.ram0[a])]
        tot += len(keys)
        ok += len(keys) - len(bad)
        if isinstance(ret, dict):                  # returned registers: "D0w" = low word of D0, "A0" = whole register
            regs = j["regN"]
            for nm, v in ret.items():
                got = regs[int(nm[1])] if nm[0] == "D" else regs[8 + int(nm[1])]
                if nm.endswith("w"):
                    got &= 0xffff
                tot += 1
                if got == v:
                    ok += 1
                else:
                    bad.append(nm)
                    model[nm] = v
                    real[nm] = got
        n += 1
        tr = collections.Counter(x for t in trace_lists for x in t)
        arms.update(tr.keys())
        status = "ok" if not bad else f"MISMATCH x{len(bad)}"
        print(f"{c.name:28} [{c.tag:10}] steps={j['steps']:8d} real={len(real):5d} model={len(model):5d} {status}")
        if bad:
            fails.append((c.name, [(hex(a) if isinstance(a, int) else a, real.get(a, c.ram0[a] if isinstance(a, int) else None), model.get(a, c.ram0[a] if isinstance(a, int) else None)) for a in sorted(bad, key=str)[:10]], dict(tr)))
    return ok, tot, n, fails, arms


def report(title, ok, tot, n, fails, arms):
    print(f"\n{title}: {ok}/{tot} tracked bytes identical over {n} states; arms {dict(arms)}")
    for f in fails[:20]:
        print("  FAIL", f)


# ------------------------------------------------------------ $10d1e
def gate_d1e():
    MASK_ON[0] = MASK + PLANES
    cases = []
    for k in LANDS:
        snap = CAP / f"k{k}_10d1e.snap"
        if not snap.exists():
            continue
        cases.append(Case(f"d1e_k{k}", snap, model=B.make_world, target="10d1e", tag="C"))
        # path A: $5809c == 0 (the campaign-style roll), side 1 state non-zero or zero by the pm67 snapshot
        cases.append(Case(f"d1e_k{k}_A", snap, {0x5809c: 0, 0x5809d: 0}, B.make_world, "10d1e", "A"))
        # path B: a side in state 6 / 8 and another in some other state (poked on side 2 and 3)
        cases.append(Case(f"d1e_k{k}_B6", snap, {0x5801c + 6 + 4: 6}, B.make_world, "10d1e", "B"))
        cases.append(Case(f"d1e_k{k}_B8", snap, {0x5801c + 12 + 4: 8, 0x5801c + 4: 4}, B.make_world, "10d1e", "B"))
    # a spread of seeds on one land (the roll is a pure function of $580a0/$5809c)
    snap = CAP / "k5_10d1e.snap"
    for i, seed in enumerate((0x1, 0x45e, 0x7777, 0x12345678, 0xdeadbeef, 0x1fff, 0x80000001, 0x0000ffff)):
        e = {0x580a0: seed >> 24, 0x580a1: (seed >> 16) & 0xff, 0x580a2: (seed >> 8) & 0xff, 0x580a3: seed & 0xff}
        cases.append(Case(f"d1e_seed{i}", snap, e, B.make_world, "10d1e", "C"))
        e2 = dict(e)
        e2.update({0x5809c: 0, 0x5809d: 0})
        cases.append(Case(f"d1e_seed{i}_A", snap, e2, B.make_world, "10d1e", "A"))
        e3 = dict(e2)
        e3.update({0x5801c + 4: 6, 0x5801c + 10: 2})
        cases.append(Case(f"d1e_seed{i}_B", snap, e3, B.make_world, "10d1e", "B"))
        e4 = dict(e)
        e4[0x5809d] = 0x10 + i            # small map ($58148 < $2000 is a $5809c override of $0010..)
        e4[0x5809c] = 0
        cases.append(Case(f"d1e_seed{i}_big", snap, e4, B.make_world, "10d1e", "C"))
    # random side-state combinations (0 / 2 / 4 / 6 / 8 per side) over the three paths; and the $110d0 quirk: side 1's state
    # alone decides the start groups of all four sides in path A (state of side 1 zero, the others not, and the reverse)
    rnd = __import__("random").Random(1411)
    for i in range(48):
        st = [rnd.choice((0, 2, 4, 6, 8)) for _ in range(4)]
        e = {0x5801c + 6 * j + 4: st[j] for j in range(4)}
        if i % 3 == 0:
            e.update({0x5809c: 0, 0x5809d: 0})
        sd = rnd.getrandbits(32)
        e.update({0x580a0: sd >> 24, 0x580a1: (sd >> 16) & 255, 0x580a2: (sd >> 8) & 255, 0x580a3: sd & 255})
        cases.append(Case(f"d1e_rs{i}_{''.join(map(str, st))}", CAP / f"k{LANDS[i % len(LANDS)]}_10d1e.snap", e, B.make_world, "10d1e", "rand"))
    for i in range(6):
        for nm, st in (("q1zero", [0, 4, 4, 4]), ("q1set", [2, 0, 0, 0]), ("qnone", [0, 0, 0, 0]), ("all68", [6, 8, 6, 8])):
            e = {0x5801c + 6 * j + 4: st[j] for j in range(4)}
            e.update({0x5809c: 0, 0x5809d: 0, 0x580a3: 0x30 + i, 0x580a2: i})
            cases.append(Case(f"d1e_{nm}_{i}", CAP / "k5_10d1e.snap", e, B.make_world, "10d1e", nm))
    sel = [c for c in cases if not args[1:] or args[1] in c.name]
    return run_cases(sel, [B.MAKE_WORLD_TRACE])


# ------------------------------------------------------------ $4672
def gate_forest():
    cases = []
    for k in LANDS:
        snap = CAP / f"k{k}_4672.snap"
        if snap.exists():
            cases.append(Case(f"forest_k{k}", snap, model=B.setup_forests, target="4672", tag="random"))
            # the OK-path build runs with $5809c == 0: $4788 then makes two tries per cell (D7 = 1)
            cases.append(Case(f"forest_k{k}_z", snap, {0x5809c: 0, 0x5809d: 0}, B.setup_forests, "4672", "5809c=0"))
    snap = CAP / "k5_4672.snap"
    # synthetic arms: the tree pool nearly full ($4e512), a full operation table ($57fb8 = $50), every cell refused (plane A zeroed)
    cases.append(Case("forest_k5_treepool", snap, {0x4e512: 0x12, 0x4e513: 0x40 - 0x0}, B.setup_forests, "4672", "syn"))
    cases.append(Case("forest_k5_treepool_z", snap, {0x4e512: 0x12, 0x4e513: 0x40, 0x5809c: 0, 0x5809d: 0}, B.setup_forests, "4672", "syn"))
    cases.append(Case("forest_k5_oplimit", snap, {0x57fb8: 0x00, 0x57fb9: 0x48}, B.setup_forests, "4672", "syn"))
    cases.append(Case("forest_k5_nocell", snap, {0x438ee - 8257 + i: 0 for i in range(0x2000)}, B.setup_forests, "4672", "syn"))
    sel = [c for c in cases if not args[1:] or args[1] in c.name]
    return run_cases(sel, [B.FOREST_TRACE])


def gate_kings():
    MASK_ON[0] = MASK + UI_MASK
    cases = []
    for k in LANDS:
        snap = CAP / f"k{k}_238c.snap"
        if snap.exists():
            cases.append(Case(f"kings_k{k}", snap, model=B.setup_kings, target="238c", tag="natural"))
    # synthetic arms (labelled pokes on the entry snapshot of lands 5, 25, 100)
    import pm_fsm_ref as P
    for k in (5, 25, 100):
        snap = CAP / f"k{k}_238c.snap"
        ram = _ram(snap)
        starts = {side: ram[0x51538 + side * 0x13c + 100] << 8 | ram[0x51538 + side * 0x13c + 101] for side in range(8)}
        sides = [sd for sd, c in starts.items() if c]
        loc = ram[0x57ffe] << 8 | ram[0x57fff]
        # command-slot states: every side AI (4), every side human (2), the zero state (the code arms it to 4)
        for nm, st in (("allai", 4), ("allhuman", 2), ("zerostate", 0)):
            cases.append(Case(f"kings_k{k}_{nm}", snap, {0x58016 + 6 * sd + 4: st for sd in range(1, 5)}, B.setup_kings, "238c", nm))
        # another local side
        for lc in (2, 3):
            cases.append(Case(f"kings_k{k}_local{lc}", snap, {0x57ffe: 0, 0x57fff: lc}, B.setup_kings, "238c", "local"))
        # a Base on the sea: the 2 x 2 corners of one side's start cell zeroed (the lord slot is consumed, `$2eac` fails, `$238c` goes on with stale A0)
        for sd in sides[:2]:
            c = starts[sd]
            e = {0x3f86c + c + o: 0 for o in (0, 1, 64, 65)}
            cases.append(Case(f"kings_k{k}_sea_s{sd}", snap, e, B.setup_kings, "238c", "sea"))
        # man table full / nearly full
        full = {P.OBJ + sl * 50 + 5: 1 for sl in range(1, 512) if P.OBJ + sl * 50 + 5 < P.END and ram[P.OBJ + sl * 50 + 5] == 0}
        cases.append(Case(f"kings_k{k}_nomen", snap, full, B.setup_kings, "238c", "noman"))
        free = sorted(full)
        left = {a: v for a, v in full.items() if a not in free[:4]}
        cases.append(Case(f"kings_k{k}_fewmen", snap, left, B.setup_kings, "238c", "fewmen"))
        # every side's group slots 1..5 taken: $25d6 refuses each captain
        e = {0x51538 + sd * 0x13c + 28 + 2 * i + 1: 1 for sd in range(1, 5) for i in range(1, 6)}
        cases.append(Case(f"kings_k{k}_slotsfull", snap, e, B.setup_kings, "238c", "capfull"))
    sel = [c for c in cases if not args[1:] or args[1] in c.name]
    return run_cases(sel, [B.KINGS_TRACE, B.TOWN_TRACE], steps=20_000_000)


def gate_water():
    cases = []
    for k in LANDS:
        snap = CAP / f"k{k}_2906.snap"
        if snap.exists():
            cases.append(Case(f"water_k{k}", snap, model=B.setup_water, target="2906", tag="natural"))
    sel = [c for c in cases if not args[1:] or args[1] in c.name]
    return run_cases(sel, [])


def _ram(snap):
    return bytes(ram_from_snap(str(snap)))


def gate_town():
    """$2eac: kinds 1..6 at land cells, sea cells, map edges and occupied cells of three built lands (post-build snapshots,
    synthetic entries by `callcap 2eac` with D1..D4 preset), plus the natural entries of $238c (kings gate)."""
    import random
    rnd = random.Random(141)
    MASK_ON[0] = MASK
    cases = []
    for k in (5, 25, 100):
        snap = CAP / f"k{k}_2906.snap"
        ram = _ram(snap)
        alt = lambda c: sum(ram[0x3f86c + c + o] for o in (0, 1, 64, 65)) & 0xff
        land = [c for c in range(64 * 120) if alt(c) != 0 and 3 <= (c & 63) <= 58 and c > 64 * 3]
        sea = [c for c in range(0x2000) if alt(c) == 0 and 3 <= (c & 63) <= 58 and c > 64 * 3]
        # occupied: a cell holding an entity of category 2 / $10 (a settlement) in its bucket chain
        occ = []
        for c in land:
            d = ram[0x47970 + 2 * c] << 8 | ram[0x47970 + 2 * c + 1]
            if d and ram[(0x51b66 + (d - 0x10000 if d & 0x8000 else d)) + 6] in (2, 0x10):
                occ.append(c)
        edge = [0x3d, 0x3e, 0x3f, 0, 1, 2, 64 * 127 + 5, 64 * 126 + 62, 64 * 2 + 40, 64 * 1 + 10, 64 * 120 + 30]
        picks = [("land", c) for c in rnd.sample(land, 5)] + [("sea", c) for c in rnd.sample(sea, 2)] + \
                [("occ", c) for c in rnd.sample(occ, min(4, len(occ)))] + [("edge", c) for c in edge]
        for kind in range(1, 7):
            for nm, c in picks:
                side = rnd.randint(1, 4)
                x, y = c & 63, c >> 6
                cases.append(Case(f"town_k{k}_{kind}_{nm}_{c:04x}", snap, model=(lambda m, s_=side, x_=x, y_=y, k_=kind: (lambda r: {"D0w": r[0], "A0": r[1]})(B.place_town(m, s_, x_, y_, k_))),
                                  target="2eac", tag=nm, presets=f" D1={side:x} D2={x:x} D3={y:x} D4={kind:x}"))
        # no free lord slot: every owner byte set
        e = {B.LORDS + 0x20 * i + 5: 1 for i in range(160)}
        cases.append(Case(f"town_k{k}_nolord", snap, e, lambda m: (lambda r: {"D0w": r[0], "A0": r[1]})(B.place_town(m, 2, 20, 30, 3)),
                          "2eac", "nolord", presets=" D1=2 D2=14 D3=1e D4=3"))
        # settlement table full
        e = {B.SETTL + 0x12 * i + 5: 1 for i in range(1, 0x400)}
        cases.append(Case(f"town_k{k}_nosettl", snap, e, lambda m: (lambda r: {"D0w": r[0], "A0": r[1]})(B.place_town(m, 2, 20, 30, 3)),
                          "2eac", "nosettl", presets=" D1=2 D2=14 D3=1e D4=3"))
    sel = [c for c in cases if not args[1:] or args[1] in c.name]
    return run_cases(sel, [B.TOWN_TRACE])


def _men(ram, side=None):
    out = []
    for sl in range(1, 512):
        a = 0x51b66 + sl * 50
        if ram[a + 6] == 0 and 0 < ram[a + 5] < 128 and (side is None or ram[a + 5] == side):
            out.append(a)
    return out


def gate_addrank():
    """$1b2a: a man joins a group.  Same side; another side whose home settlement the lead's side owns (he changes side);
    another side whose home settlement it does not (refused)."""
    MASK_ON[0] = MASK
    cases = []
    for k in (5, 60):
        snap = CAP / f"k{k}_2906.snap"
        ram = _ram(snap)
        leads = {}
        for side in range(1, 5):
            g = 0x51538 + side * 0x13c
            lead = (ram[g + 64] << 8 | ram[g + 65])
            if lead:
                leads[side] = 0x51b66 + lead
        for side, lead in leads.items():
            for other in (side, side % 4 + 1, (side + 1) % 4 + 1):
                men = [a for a in _men(ram, other) if a != lead]
                for a in men[:3] + men[-2:]:
                    for flip in (0, 1):
                        e = {}
                        if other != side and flip:        # make the man's home settlement the lead's side's
                            home = 0x4f916 + (ram[a + 34] << 8 | ram[a + 35])
                            e[home + 5] = side
                        nm = f"addrank_k{k}_s{side}_o{other}_{a:05x}_{flip}"
                        cases.append(Case(nm, snap, e, (lambda m, l=lead, a_=a: {"A0": 0} if False else (B.add_ranker(m, l, a_) and None)),
                                          "1b2a", "same" if other == side else ("join" if flip else "refuse"),
                                          presets=f" A0={lead:x} A1={a:x}"))
    sel = [c for c in cases if not args[1:] or args[1] in c.name]
    return run_cases(sel, [])


def gate_derank():
    """$1cc4: dismiss `count >> (posture - 2)` men, least equipped first.  Synthetic: every posture 0..5 on the groups of two
    built lands and of mission 1 (pm123/win/m1_s0), with the roster's equipment bytes (44, 33) varied."""
    MASK_ON[0] = MASK
    cases = []
    for nm, snap in (("k5", CAP / "k5_2906.snap"), ("k60", CAP / "k60_2906.snap"), ("m1", ROOT / "scratchpad/pm123/win/m1_s0.snap")):
        ram = _ram(snap)
        for side in range(1, 5):
            g = 0x51538 + side * 0x13c
            for i in range(6):
                d2 = side * 0x13c + 0x4c + 2 * i
                cnt = ram[0x51538 + d2 - 24] << 8 | ram[0x51538 + d2 - 23]
                lead = ram[0x51538 + d2 - 12] << 8 | ram[0x51538 + d2 - 11]
                if not lead or cnt < 2:
                    continue
                for posture in (0, 2, 3, 4, 5):
                    e = {0x51538 + d2 + 61: posture, 0x51538 + d2 + 60: 0}
                    cases.append(Case(f"derank_{nm}_s{side}_g{i}_p{posture}", snap, e, (lambda m, d=d2: B.derank(m, d)), "1cc4", f"p{posture}",
                                      presets=f" D2={d2:x}"))
                # equipment spread: walk the roster and poke distinct bytes 44 / 33
                e, d0, n = {}, ram[0x51538 + d2 - 36] << 8 | ram[0x51538 + d2 - 35], 0
                while d0 and n < 40:
                    a = 0x51b66 + (d0 - 0x10000 if d0 & 0x8000 else d0)
                    e[a + 44] = 2 * ((n * 5 + 1) % 4)      # tier 0,2,4,6: $1d70 indexes the word table $1e8c with this byte
                    e[a + 33] = (n * 3) % 11
                    d0 = ram[a + 26] << 8 | ram[a + 27]
                    n += 1
                e[0x51538 + d2 + 61] = 3
                e[0x51538 + d2 + 60] = 0
                cases.append(Case(f"derank_{nm}_s{side}_g{i}_equip", snap, e, (lambda m, d=d2: B.derank(m, d)), "1cc4", "equip",
                                  presets=f" D2={d2:x}"))
    sel = [c for c in cases if not args[1:] or args[1] in c.name]
    return run_cases(sel, [])


def gate_towns():
    """$1073c: the world build's town placement (natural entries of 24 built lands), and the natural $2eac entries inside it."""
    MASK_ON[0] = MASK
    cases = []
    for k in LANDS:
        snap = CAP / f"k{k}_1073c.snap"
        if snap.exists():
            cases.append(Case(f"towns_k{k}", snap, model=B.build_towns, target="1073c", tag="natural"))
    sel = [c for c in cases if not args[1:] or args[1] in c.name]
    return run_cases(sel, [B.TOWN_TRACE], steps=20_000_000)


def gate_town_natural():
    """$2eac at its first seven natural entries of lands 5 and 25 (the snapshot is stopped at the entry: D1..D4 are the caller's)."""
    MASK_ON[0] = MASK
    cases = []
    for k in (5, 25):
        for n in range(1, 8):
            snap = CAP / f"nat{k}_2eac_{n}.snap"
            if snap.exists():
                def mdl(m, snap=snap):
                    import struct as st
                    regs = _regs(snap)
                    r = B.place_town(m, regs["D1"] & 0xffff, regs["D2"] & 0xffff, regs["D3"] & 0xffff, regs["D4"] & 0xffff)
                    return {"D0w": r[0], "A0": r[1]}
                cases.append(Case(f"townnat_k{k}_{n}", snap, model=mdl, target="2eac", tag="natural"))
    sel = [c for c in cases if not args[1:] or args[1] in c.name]
    return run_cases(sel, [B.TOWN_TRACE])


def _regs(snap):
    """the entry registers of a snapshot (the REPL prints them at the stop; we read them from the log next to it)"""
    import re
    k = re.search(r"nat(\d+)_2eac_(\d+)", snap.name)
    log = (CAP / f"nat{k.group(1)}.txt").read_text()
    blocks = re.split(r"(?=--- breakpoint)", log)[1:]
    b = blocks[int(k.group(2)) - 1]
    return {n: int(v, 16) for n, v in re.findall(r"\b([DA][0-7]):([0-9a-f]{8})", b)}


GATES = {"d1e": gate_d1e, "forest": gate_forest, "kings": gate_kings, "water": gate_water, "town": gate_town, "addrank": gate_addrank, "derank": gate_derank, "towns": gate_towns, "townnat": gate_town_natural}

if __name__ == "__main__":
    which = args[0] if args else None
    for name, fn in GATES.items():
        if which and which != name and which != "all":
            continue
        report(name, *fn())
