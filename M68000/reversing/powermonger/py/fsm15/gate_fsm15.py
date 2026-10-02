"""141st pass: differential gate of the `$15000`-page entity-mode handlers (`fsm15_ref.MODES`) against the real 68000.

Each state: one snapshot RAM, every other live entity record disabled (owner byte zeroed, `Harness.disable_others`), the one
record under test in its mode (natural, or poked: a "syn" state), `callcap 14b62` (the whole entity iterator), and the real
changed-memory delta compared byte for byte with `pm_fsm_ref.reconstruct` (which dispatches the new handlers through its
`SHEP_MODES` table, `fsm15_ref.install()`).  Tracked: the entity table, buckets, leaders, settlements, the group table
`$51538..$51b66`, the tree array `$4d252..$4e514`, the stat counters `$12a24/$12a32`, the RNG seed, `$57ff4`.

    cd M68000
    .venv/bin/python scratchpad/pm141/agents/fsm15/gate_fsm15.py [name-substring] [reuse]

The RAM images are `ram_from_snap` of the snapshots listed in SNAPS (`prep_rams()` writes them under
`scratchpad/pm141/agents/fsm15/ram/`).  Output: one line per state, then `TRACKED BYTES: ok/total` and the per-mode table.
"""
import collections
import concurrent.futures as cf
import glob
import json
import os
import struct
import sys
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pm_fsm_ref as P
from pm_fsm_diff import Harness
import fsm15_ref as F

WORK = "scratchpad/pm141/agents/fsm15"     # data (ram/, out/) lives here, not beside the promoted script
AG = WORK
OUT = f"{AG}/out"
OBJ, REC, SETTL, GROUP, LEADER = P.OBJ, P.REC, P.SETTL, P.GROUP, P.LEADER
SNAP_GLOBS = ["scratchpad/pm121/k*.snap", "scratchpad/pm121/run/k5_s4.snap", "scratchpad/pm121/run/k25_s*.snap",
              "scratchpad/pm123/win/m1_s0.snap", "scratchpad/pm123/win/m1_ready.snap", "scratchpad/pm123/win/m1_atk.snap",
              "scratchpad/pm139/jobs/pop_done.snap"]

P.REGIONS = P.REGIONS + [(GROUP, OBJ, "groups"), (0x4d252, 0x4e514, "trees"), (0x12a24, 0x12a34, "stats"),
                         (P.RNG_SEED, P.RNG_SEED + 4, "rng"), (0x57ff4, 0x57ff6, "pigeon")]


def snap_of(ramname):
    parent, stem = ramname.split("_", 1)
    for g in SNAP_GLOBS:
        for s in glob.glob(str(ROOT / g)):
            p = Path(s)
            if p.parent.name == parent and p.stem == stem:
                return str(p.relative_to(ROOT))
    raise KeyError(ramname)


def prep_rams():
    from pm_export import ram_from_snap
    out = ROOT / AG / "ram"
    out.mkdir(parents=True, exist_ok=True)
    for g in SNAP_GLOBS:
        for s in sorted(glob.glob(str(ROOT / g))):
            p = Path(s)
            (out / f"{p.parent.name}_{p.stem}.ram").write_bytes(ram_from_snap(p))


RAMS = {}


def ram(name):
    if name not in RAMS:
        RAMS[name] = (ROOT / AG / "ram" / f"{name}.ram").read_bytes()
    return RAMS[name]


def all_rams():
    return sorted(Path(p).stem for p in glob.glob(str(ROOT / AG / "ram" / "*.ram")))


def rec(slot): return OBJ + slot * REC


def live_pos(r, slot):
    return r[rec(slot) + 5] != 0 and r[rec(slot) + 5] < 0x80


def w16(r, a): return struct.unpack_from(">H", r, a)[0]


def expand(items):
    """[(addr, nbytes, value)] -> {addr: byte}."""
    d = {}
    for a, n, v in items:
        for i in range(n):
            d[a + i] = (v >> (8 * (n - 1 - i))) & 0xff
    return d


def mk(name, ramname, slot, tag, edits=(), mode=None, nat=False, keep=(), force=None):
    """keep: further slots left live; force: {slot: mode} poked into the kept slots (so only modelled modes run)."""
    r = ram(ramname)
    items = list(edits)
    if mode is not None:
        items.append((rec(slot) + 31, 1, mode))
    for k, md in (force or {}).items():
        items.append((rec(k) + 31, 1, md))
    pokes = Harness.disable_others(r, keep=[slot, *keep])
    pokes_e = Harness.bytepokes(r, expand(items)) if items else []
    return dict(name=name, ram=ramname, slot=slot, tag=tag, pokes=pokes + pokes_e, nat=nat)


# ---------------------------------------------------------------------------------------- carriers
def carriers(pred, n, rams=None, skip=0):
    out = []
    for rn in (rams or all_rams()):
        r = ram(rn)
        for s in range(1, 512):
            if live_pos(r, s) and pred(r, s):
                out.append((rn, s))
    step = max(1, len(out) // n)
    return out[skip::step][:n]


def has_settl(r, s): return r[rec(s) + 7] & 0x40 == 0 and w16(r, rec(s) + 34) < 0x200 and r[SETTL + w16(r, rec(s) + 34) + 5] != 0


def has_group(r, s):
    g = w16(r, rec(s) + 42)
    return g != 0 and g < 0x1000 and GROUP + g + 60 < OBJ and w16(r, GROUP + g + 24) != 0 and has_settl(r, s)


def natural_states(per_mode=5):
    S = []
    by_mode = collections.defaultdict(list)
    for rn in all_rams():
        r = ram(rn)
        for s in range(1, 512):
            if live_pos(r, s) and r[rec(s) + 31] in F.MODES:
                by_mode[r[rec(s) + 31]].append((rn, s))
    for md, lst in sorted(by_mode.items()):
        step = max(1, len(lst) // per_mode)
        for rn, s in lst[::step][:per_mode]:
            S.append(mk(f"nat_{md:02x}_{rn}_{s}", rn, s, f"{md:02x}", nat=True))
    return S


def syn_states():
    S = []
    base = carriers(lambda r, s: has_settl(r, s) and r[rec(s) + 7] & 0x90 == 0, 8)
    grp = carriers(has_group, 8)

    def add(md, tag, who, extra=lambda r, s: [], n=None):
        for i, (rn, s) in enumerate(who[:n] if n else who):
            r = ram(rn)
            S.append(mk(f"syn_{md:02x}_{tag}_{i}", rn, s, f"{md:02x}", extra(r, s) + [], mode=md))

    def E(s, off, n, v): return (rec(s) + off, n, v)

    # $14 / $16 / $18 / $24 : settlement-only handlers
    add(0x14, "plain", base, n=4)
    add(0x14, "bit7", base, lambda r, s: [(SETTL + w16(r, rec(s) + 34) + 7, 1, r[SETTL + w16(r, rec(s) + 34) + 7] | 0x80)], n=3)
    add(0x16, "summer", base, lambda r, s: [(0x57fd0, 2, 0)], n=3)
    add(0x16, "winter", base, lambda r, s: [(0x57fd0, 2, 1), E(s, 33, 1, 0)], n=3)
    add(0x16, "winter_plough", base, lambda r, s: [(0x57fd0, 2, 1), E(s, 33, 1, 8)], n=3)
    add(0x18, "plain", base, n=3)
    add(0x24, "plain", base, n=3)
    add(0x20, "bit5", base, lambda r, s: [E(s, 7, 1, r[rec(s) + 7] | 0x20)], n=2)
    add(0x20, "nobit5", base, lambda r, s: [E(s, 7, 1, r[rec(s) + 7] & ~0x20)], n=2)
    # group modes
    for st in (0xc, 3, 6):
        add(0x1a, f"st{st:x}", grp, lambda r, s, st=st: [(GROUP + w16(r, rec(s) + 42), 2, st)], n=4)
    for st in (3, 6, 0xc):
        add(0x1c, f"st{st:x}", grp, lambda r, s, st=st: [(GROUP + w16(r, rec(s) + 42), 2, st)], n=4)
    add(0x1e, "plain", grp, n=4)
    for st in (0xc, 3):
        add(0x26, f"st{st:x}_d1", grp, lambda r, s, st=st: [(GROUP + w16(r, rec(s) + 42), 2, st), E(s, 18, 2, 1), E(s, 36, 2, 0x0a35)], n=3)
    add(0x26, "d5", grp, lambda r, s: [E(s, 18, 2, 5)], n=2)
    add(0x28, "d1", grp, lambda r, s: [E(s, 18, 2, 1)], n=3)
    add(0x28, "d5", grp, lambda r, s: [E(s, 18, 2, 5)], n=2)
    add(0x30, "plain", grp, n=4)
    # $2a recruit joins: lead = another carrier with a group in state 3 and a quota
    leads = carriers(has_group, 40)
    for i, (rn, s) in enumerate(carriers(has_settl, 12)):
        r = ram(rn)
        cand = [L for (n2, L) in leads if n2 == rn and L != s]
        if not cand:
            continue
        L = cand[i % len(cand)]
        gl = w16(r, rec(L) + 42)
        for tag, quota, side_ok, d18 in (("join", 3, True, 0x32), ("quota0", 0, True, 0x32), ("negq", 0xffff, True, 0x32),
                                         ("side", 3, False, 0x32), ("tick", 3, True, 5), ("tick1", 3, True, 1),
                                         ("nolead", 3, True, 0x32)):
            ed = [E(s, 18, 2, d18), E(s, 46, 2, (rec(L) - OBJ) & 0xffff), (GROUP + gl, 2, 3), E(L, 46, 2, quota)]
            if tag == "nolead":
                ed[1] = E(s, 46, 2, 0)
            if side_ok:
                ed.append(E(s, 5, 1, r[rec(L) + 5]))
                ed.append((SETTL + w16(r, rec(s) + 34) + 5, 1, r[rec(L) + 5]))
            else:
                ed.append(E(s, 5, 1, (r[rec(L) + 5] % 5) + 1 if (r[rec(L) + 5] % 5) + 1 != r[rec(L) + 5] else 3))
            ed.append(E(L, 31, 1, 0x68))
            S.append(mk(f"syn_2a_{tag}_{i}", rn, s, "2a", ed, mode=0x2a, keep=[L]))
    # $2e reached target / $36 chase / $66 contact: a target = another live man
    tg = carriers(lambda r, s: True, 30)
    for i, (rn, s) in enumerate(carriers(has_settl, 10)):
        r = ram(rn)
        others = [t for (n2, t) in tg if n2 == rn and t != s]
        if not others:
            continue
        t = others[i % len(others)]
        for md_t, p_t in ((0x10, 0x10), (0x68, 0x68), (0x2c, 0x2c), (0x32, 0x32), (0x12, 0x3c), (0x2c, 0x10), (0x10, 0x68)):
            ed = [E(s, 48, 2, (rec(t) - OBJ) & 0xffff), E(t, 31, 1, md_t), E(t, 30, 1, p_t),
                  E(s, 7, 1, r[rec(s) + 7] & ~0x50), E(t, 7, 1, r[rec(t) + 7] & ~0x50), E(s, 42, 2, 0), E(t, 42, 2, 0)]
            S.append(mk(f"syn_2e_{md_t:02x}_{p_t:02x}_{i}", rn, s, "2e", ed, mode=0x2e, keep=[t]))
        for tag, hp in (("alive", 5), ("dead", 0)):
            ed = [E(s, 48, 2, (rec(t) - OBJ) & 0xffff), E(t, 5, 1, hp if hp else 0x80 | r[rec(t) + 5])]
            if tag == "dead":
                ed = [E(s, 48, 2, (rec(t) - OBJ) & 0xffff), E(t, 5, 1, 0xff)]    # negative owner: bs <= 0
            S.append(mk(f"syn_36_{tag}_{i}", rn, s, "36", ed, mode=0x36))
        S.append(mk(f"syn_66_{i}", rn, s, "66", [E(s, 48, 2, (rec(t) - OBJ) & 0xffff)], mode=0x66))
        for tag, fl in (("plain", r[rec(s) + 7] & ~0x50),):
            ed = [E(s, 48, 2, (rec(t) - OBJ) & 0xffff), E(s, 18, 2, 1), E(s, 7, 1, fl), E(t, 5, 1, 4)]
            S.append(mk(f"syn_38_{tag}_{i}", rn, s, "38", ed, mode=0x38))
    for i, (rn, s) in enumerate(grp):
        r = ram(rn)
        others = [t for (n2, t) in tg if n2 == rn and t != s and r[rec(t) + 7] & 0x40 == 0]
        if not others:
            continue
        t = others[i % len(others)]
        for tag, fl, l28 in (("b4", r[rec(s) + 7] | 0x10, 0), ("b6", r[rec(s) + 7] | 0x40, (rec(s) - OBJ) & 0xffff),
                             ("b6z", r[rec(s) + 7] | 0x40, 0)):
            ed = [E(s, 48, 2, (rec(t) - OBJ) & 0xffff), E(s, 18, 2, 1), E(s, 7, 1, fl), E(s, 28, 2, l28), E(t, 5, 1, 4)]
            S.append(mk(f"syn_38_{tag}_{i}", rn, s, "38", ed, mode=0x38))
    add(0x38, "wait", base, lambda r, s: [E(s, 18, 2, 7), E(s, 48, 2, 0)], n=2)
    # $34 shot cool-down
    add(0x34, "run", base, lambda r, s: [E(s, 18, 1, 9)], n=2)
    add(0x34, "end", base, lambda r, s: [E(s, 18, 1, 0)], n=2)
    # $3c run away, $3e/$40/$44/$46/$6a, $4a, $4c
    add(0x3c, "plain", base, n=4)
    add(0x40, "plain", base, lambda r, s: [E(s, 36, 2, w16(r, rec(s) + 34))], n=3)
    add(0x46, "d1", base, lambda r, s: [E(s, 18, 2, 1)], n=2)
    add(0x46, "d5", base, lambda r, s: [E(s, 18, 2, 5)], n=2)
    add(0x4a, "none", base, lambda r, s: [E(s, 28, 2, 0)], n=2)
    add(0x4a, "link", base, lambda r, s: [E(s, 28, 2, (rec(1) - OBJ) & 0xffff), E(s, 17, 1, 0x57)], n=2)
    add(0x4c, "same", base, n=3)
    add(0x4c, "grp", grp, n=3)
    add(0x50, "plain", base, lambda r, s: [E(s, 46, 2, (w16(r, SETTL + w16(r, rec(s) + 34) + 14)))], n=3)
    # merchants / fishers
    add(0x4e, "summer", base, lambda r, s: [(0x57fd0, 2, 0), E(s, 33, 1, 4), E(s, 44, 1, 6)], n=3)
    add(0x4e, "winter", base, lambda r, s: [(0x57fd0, 2, 1), E(s, 33, 1, 2)], n=3)
    add(0x5e, "summer", base, lambda r, s: [(0x57fd0, 2, 0)], n=3)
    add(0x5e, "winter", base, lambda r, s: [(0x57fd0, 2, 1)], n=3)
    for d in (1, 0x14):
        add(0x54, f"d{d}", base, lambda r, s, d=d: [E(s, 18, 2, 0 if d == 1 else 0x14)], n=3)
    for k in (0, 1, 2, 3, 5, 7):
        add(0x54, f"walk{k}", base, lambda r, s, k=k: [E(s, 18, 2, 0), E(s, 14, 1, k)], n=2)
    add(0x52, "end", base, lambda r, s: [E(s, 18, 2, 0), E(s, 46, 2, w16(r, SETTL + w16(r, rec(s) + 34) + 14)),
                                         (0x57fec, 2, 1)], n=4)
    for tick in (0, 1, 2, 3, 4, 5):
        add(0x52, f"tick{tick}", base, lambda r, s, tick=tick: [E(s, 18, 2, 0), E(s, 46, 2, w16(r, SETTL + w16(r, rec(s) + 34) + 14)),
                                                                (0x57fec, 2, tick)], n=2)
    add(0x6a, "plain", base, lambda r, s: [E(s, 46, 2, (rec(1) - OBJ) & 0xffff)], n=3)
    add(0x44, "tick", base, lambda r, s: [E(s, 39, 1, 1), E(s, 36, 2, 0)], n=2)
    add(0x44, "keep", base, lambda r, s: [E(s, 39, 1, 3), E(s, 36, 2, 0)], n=2)
    add(0x64, "plain", base, n=2)
    add(0x70, "plain", base, n=1)
    add(0x7e, "winter", base, lambda r, s: [(0x57fd0, 2, 1)], n=2)
    add(0x90, "plain", base, n=3)
    add(0x8e, "plain", base, n=3)
    for tag, d in (("w1", 0x1), ("w5", 0x5)):
        add(0x5a, tag, base, lambda r, s, d=d: [E(s, 18, 2, d)], n=2)

    # ---- $1a / $1c with the town's chain men kept live (so $34f2 really sends them): force them into mode $68 / $5c
    def chain_slots(r, s):
        g = w16(r, rec(s) + 42)
        lord = (OBJ + ((w16(r, GROUP + g + 24) ^ 0x8000) - 0x8000)) & 0xfffff
        out, d0 = [], w16(r, lord + 2)
        guard = 0
        while d0 and guard < 30:
            a0 = SETTL + ((d0 ^ 0x8000) - 0x8000)
            h = w16(r, a0 + 10)
            while h and guard < 30:
                guard += 1
                sl = (OBJ + ((h ^ 0x8000) - 0x8000) - OBJ) // REC if True else 0
                out.append(((h ^ 0x8000) - 0x8000) // REC)
                h = w16(r, OBJ + ((h ^ 0x8000) - 0x8000) + 24)
            d0 = w16(r, a0 + 8)
        return [x for x in out if 0 < x < 512]

    for md in (0x1a, 0x1c):
        for st in (3, 0xc, 6):
            for i, (rn, s) in enumerate(grp[:6]):
                r = ram(rn)
                cs = [c for c in chain_slots(r, s) if c != s][:5]
                if not cs:
                    continue
                force = {c: (0x68 if j != 1 else 0x5c) for j, c in enumerate(cs)}
                ed = [(GROUP + w16(r, rec(s) + 42), 2, st)]
                for c in cs:                                  # able men: positive owner, bits 4/6/7 clear
                    ed.append((rec(c) + 5, 1, r[rec(s) + 5] or 1))
                    ed.append((rec(c) + 7, 1, r[rec(c) + 7] & ~0xd0))
                S.append(mk(f"syn_{md:02x}_chain_st{st:x}_{i}", rn, s, f"{md:02x}", ed, mode=md, keep=cs, force=force))

    # ---- RNG seeds for the fishing-catch search ($5a) and the other seeded arms
    fishers = carriers(lambda r, s: r[rec(s) + 31] in (0x5a, 0x56, 0x58, 0x5c, 0x60, 0x62), 12)
    seeds = [0x12345678, 0x9abcdef1, 0x0badf00d, 0xdeadbeef, 0x31415926, 0x27182818]
    for i, (rn, s) in enumerate(fishers):
        r = ram(rn)
        for j, sd in enumerate(seeds):
            S.append(mk(f"syn_5a_seed{j}_{i}", rn, s, "5a", [E(s, 18, 2, 0), (P.RNG_SEED, 4, sd)], mode=0x5a))
    for i, (rn, s) in enumerate(fishers[:8]):
        r = ram(rn)
        for d in (0, 1):
            S.append(mk(f"syn_5c_d{d}_{i}", rn, s, "5c", [E(s, 18, 2, d)], mode=0x5c))
            S.append(mk(f"syn_62_d{d}_{i}", rn, s, "62", [E(s, 18, 2, 0)], mode=0x62))
        S.append(mk(f"syn_56_d0_{i}", rn, s, "56", [E(s, 18, 2, 0)], mode=0x56))
        S.append(mk(f"syn_60_far_{i}", rn, s, "60", [E(s, 18, 2, 0), E(s, 20, 2, 0x1234), E(s, 22, 2, 0x2345)], mode=0x60))
        S.append(mk(f"syn_60_here_{i}", rn, s, "60", [E(s, 18, 2, 0), E(s, 20, 2, w16(r, rec(s) + 8)), E(s, 22, 2, w16(r, rec(s) + 10))], mode=0x60))
        S.append(mk(f"syn_60_near_{i}", rn, s, "60", [E(s, 18, 2, 0), E(s, 20, 2, (w16(r, rec(s) + 8) + 3) & 0xffff), E(s, 22, 2, (w16(r, rec(s) + 10) + 2) & 0xffff)], mode=0x60))

    # ---- $48 obstacle sweep: speed, heading, dwell and the sweep word
    sweepers = carriers(lambda r, s: r[rec(s) + 31] in (0x48, 0x4a, 0x10, 0x68, 0x8a) and r[rec(s) + 16] > 0, 10)
    for i, (rn, s) in enumerate(sweepers):
        r = ram(rn)
        for j, (sp, hd, dw, sw) in enumerate(((4, 0x10, 40, 8), (4, 0x30, 40, 0xfffc), (4, 0x50, 9, 0x80), (8, 0x90, 300, 0xfff8),
                                             (4, 0xd0, 5, 0x7c), (2, 0xf0, 0x40, 0xff80), (6, 0x70, 0x200, 0xffe0), (4, 0xb0, 12, 0xfffc))):
            S.append(mk(f"syn_48_{j}_{i}", rn, s, "48", [E(s, 16, 1, sp), E(s, 17, 1, hd), E(s, 18, 2, dw), E(s, 40, 2, sw)], mode=0x48))
    # ---- $3e woodcutter head_for: carriers in tree modes, tree link word 36 either 0 or a valid tree
    cutters = carriers(lambda r, s: r[rec(s) + 31] in (0x46, 0x44, 0x3e, 0x42, 0x6a, 0x40) and w16(r, rec(s) + 46) != 0, 6)
    for i, (rn, s) in enumerate(cutters):
        r = ram(rn)
        for j, an in enumerate((0, 1, 2, 3)):
            for t36 in (0, 1):
                S.append(mk(f"syn_3e_a{an}_t{t36}_{i}", rn, s, "3e", [E(s, 14, 1, an), E(s, 36, 2, 0 if t36 == 0 else 0x2a)], mode=0x3e))
    # ---- $3a / $72 / $36-reached: pairs of live records from one RAM
    def sgn(w): return (w ^ 0x8000) - 0x8000

    def chain_addrs(r, idx):
        out, d0 = [], w16(r, P.BUCKETS + 2 * idx)
        while d0 and len(out) < 60:
            a = OBJ + sgn(d0)
            out.append(a)
            d0 = w16(r, a)
        return out

    pairs = []
    for rn in all_rams()[::5]:
        r = ram(rn)
        live = [x for x in range(1, 512) if live_pos(r, x)]
        gl = [x for x in live if has_group(r, x)]
        if len(live) >= 2 and gl:
            pairs.append((rn, gl[len(gl) // 2], live[2 * len(live) // 3] if live[2 * len(live) // 3] != gl[len(gl) // 2] else live[1]))
    for i, (rn, s, t) in enumerate(pairs):
        r = ram(rn)
        k = next((k for k in range(0x2000) if w16(r, P.BUCKETS + 2 * k)), 5)
        for tag, fl in (("plain", 0), ("b4", 0x10), ("b6", 0x40)):
            ed = [E(s, 48, 2, (rec(t) - OBJ) & 0xffff), E(t, 10, 2, k), E(s, 7, 1, (r[rec(s) + 7] & ~0x50) | fl)]
            if tag == "b6":
                ed.append(E(s, 28, 2, (rec(t) - OBJ) & 0xffff))
            S.append(mk(f"syn_3a_{tag}_{i}", rn, s, "3a", ed, mode=0x3a))
        # $36 reached: the target stands on the chaser
        ed = [E(s, 48, 2, (rec(t) - OBJ) & 0xffff), E(t, 8, 2, w16(r, rec(s) + 8)), E(t, 10, 2, w16(r, rec(s) + 10))]
        S.append(mk(f"syn_36_reached_{i}", rn, s, "36", ed, mode=0x36, keep=[t], force={t: 0x68}))
    # ---- $72 pickup: a pile (category $2c) in the man's own cell chain, with items in words 10..$1a
    for i, (rn, s, t) in enumerate(pairs):
        r = ram(rn)
        cell = ((w16(r, rec(s) + 10) >> 2) & 0x1fc0) + r[rec(s) + 8]
        ch = [a for a in chain_addrs(r, cell) if a != rec(s)]
        g = grp[i % len(grp)] if grp else None
        for tag in ("pile",):
            if not ch:
                continue
            R = ch[0]
            ed = [(R + 6, 1, 0x2c), (R + 10, 2, 0x0005), (R + 12, 2, 0x0003)]
            S.append(mk(f"syn_72_{tag}_{i}", rn, s, "72", ed, mode=0x72))
    # ---- merchant goods, wrap of the leader walk, fishing markers
    for i, (rn, s) in enumerate(base[:6]):
        r = ram(rn)
        lord = w16(r, SETTL + w16(r, rec(s) + 34) + 14)
        goods = [(LEADER + lord + 24 + k, 1, 3 + k) for k in range(6)]
        for tick in range(6):
            S.append(mk(f"syn_52_goods{tick}_{i}", rn, s, "52", [E(s, 18, 2, 0), E(s, 46, 2, lord), (0x57fec, 2, tick)] + goods, mode=0x52))
        last = w16(r, 0x4f914)
        for an in (0, 2, 5, 7):
            S.append(mk(f"syn_54_wrap{an}_{i}", rn, s, "54", [E(s, 18, 2, 0), E(s, 14, 1, an), (SETTL + w16(r, rec(s) + 34) + 14, 2, last)] + goods, mode=0x54))
        # goods only on the leader record AFTER the home lord (A3 + 32): the stale-A0 pickup of $54
        nxt = [(LEADER + lord + 32 + 24 + k, 1, 3 + k) for k in range(6)]
        homeonly = [(LEADER + lord + 24 + k, 1, 0) for k in range(6)]
        for an in (0, 1, 2, 3, 5, 7):
            for tick in (1, 4):
                S.append(mk(f"syn_54_nxt{an}_t{tick}_{i}", rn, s, "54", [E(s, 18, 2, 0), E(s, 14, 1, an), (0x57fec, 2, tick)] + homeonly + nxt, mode=0x54))
        S.append(mk(f"syn_4e_goods_{i}", rn, s, "4e", [(0x57fd0, 2, 0), E(s, 33, 1, 4), E(s, 44, 1, 0xa)] + goods, mode=0x4e))
    # ---- $3e: every tree of the lord's list already taken ($0d): the full-circle, no-tree exit (bit 6 -> $35f4, else $3c08)
    for i, (rn, s) in enumerate(cutters[:4]):
        r = ram(rn)
        if not has_group(r, s):
            grp_ok = False
        else:
            grp_ok = True
        lordrec = OBJ + sgn(w16(r, LEADER + w16(r, OBJ + sgn(w16(r, rec(s) + 46)) + 14) + 20)) if False else None
        A3 = LEADER + w16(r, OBJ + sgn(w16(r, rec(s) + 46)) + 14)
        ent = OBJ + sgn(w16(r, A3 + 20))
        d0 = w16(r, ent + 4)
        trees, seen_ = [], set()
        while d0 and d0 not in seen_ and len(trees) < 100:
            seen_.add(d0)
            trees.append(0x4d252 + sgn(d0))
            d0 = w16(r, 0x4d252 + sgn(d0) + 8)
        for tag, bit6 in (("b6", True), ("nob6", False)):
            if bit6 and not grp_ok:
                continue
            ed = [(a + 7, 1, 0x0d) for a in trees] + [E(s, 14, 1, 1), E(s, 36, 2, 0)]
            if bit6:
                ed += [E(s, 7, 1, r[rec(s) + 7] | 0x40), E(s, 28, 2, 0), E(s, 42, 2, w16(r, rec(g[1]) + 42) if False else w16(r, rec(s) + 42))]
            else:
                ed += [E(s, 7, 1, r[rec(s) + 7] & ~0x40)]
            S.append(mk(f"syn_3e_none_{tag}_{i}", rn, s, "3e", ed, mode=0x3e))
    # ---- fishing markers: poke the first record of the fisher's cell chain into a catch marker ($18/$10) or a taken one ($20)
    for i, (rn, s) in enumerate(fishers):
        r = ram(rn)
        ch = [a for a in chain_addrs(r, w16(r, rec(s) + 42)) if a != rec(s)]
        if not ch:
            continue
        S.append(mk(f"syn_62_marker_{i}", rn, s, "62", [E(s, 18, 2, 0), (ch[0] + 6, 1, 0x20)], mode=0x62))
        for j, sd in enumerate(seeds + [0x55aa55aa, 0x13572468, 0x7777abcd, 0x01020304, 0xf0f0f0f0, 0x2468ace1, 0x1f2e3d4c, 0x99999999]):
            S.append(mk(f"syn_5a_found{j}_{i}", rn, s, "5a", [E(s, 18, 2, 0), (ch[0] + 6, 1, 0x18), (ch[0] + 7, 1, 0x10), (P.RNG_SEED, 4, sd)], mode=0x5a))

    # ---- more arms
    # $1a/$1c chain men with the able-by-bit-7 arm ($34f2 sends a bit-7 man even when bit 4 is set)
    for md in (0x1a, 0x1c):
        for i, (rn, s) in enumerate(grp[:4]):
            r = ram(rn)
            cs = [c for c in chain_slots(r, s) if c != s][:4]
            if not cs:
                continue
            force = {c: 0x68 for c in cs}
            ed = [(GROUP + w16(r, rec(s) + 42), 2, 3)]
            for c in cs:
                ed += [(rec(c) + 5, 1, r[rec(s) + 5] or 1), (rec(c) + 7, 1, (r[rec(c) + 7] | 0x80 | 0x10) & ~0x40)]
            S.append(mk(f"syn_{md:02x}_chain_b7_{i}", rn, s, f"{md:02x}", ed, mode=md, keep=cs, force=force))
    # $2a with the lead's group not in state 3
    for i, (rn, s) in enumerate(carriers(has_settl, 12)):
        r = ram(rn)
        cand = [L for (n2, L) in leads if n2 == rn and L != s]
        if not cand:
            continue
        L = cand[i % len(cand)]
        gl = w16(r, rec(L) + 42)
        ed = [E(s, 18, 2, 0x32), E(s, 46, 2, (rec(L) - OBJ) & 0xffff), (GROUP + gl, 2, 6), E(L, 46, 2, 3), E(L, 31, 1, 0x68)]
        S.append(mk(f"syn_2a_state6_{i}", rn, s, "2a", ed, mode=0x2a, keep=[L]))
    # $36 reached: fast chaser one unit from the target
    for i, (rn, s, t) in enumerate(pairs):
        r = ram(rn)
        for dx, dy in ((1, 0), (0, 1), (2, 2), (0, 0)):
            ed = [E(s, 48, 2, (rec(t) - OBJ) & 0xffff), E(s, 16, 1, 200), E(t, 8, 2, (w16(r, rec(s) + 8) + dx) & 0xffff),
                  E(t, 10, 2, (w16(r, rec(s) + 10) + dy) & 0xffff)]
            S.append(mk(f"syn_36_reach{dx}{dy}_{i}", rn, s, "36", ed, mode=0x36, keep=[t], force={t: 0x68}))
        S.append(mk(f"syn_3a_b4z_{i}", rn, s, "3a", [E(s, 48, 2, (rec(t) - OBJ) & 0xffff), E(t, 10, 2, 5), E(s, 7, 1, (r[rec(s) + 7] & ~0x40) | 0x10), E(s, 42, 2, 0)], mode=0x3a))
        S.append(mk(f"syn_72_nopile_{i}", rn, s, "72", [], mode=0x72))
    # $3e bit-6 no-tree exit: a group carrier takes the 46 house link of a woodcutter of the same RAM, all of that lord's trees taken
    for i, (rn, c) in enumerate(cutters):
        r = ram(rn)
        gs = next((x for x in range(1, 512) if live_pos(r, x) and has_group(r, x) and x != c), None)
        if gs is None:
            continue
        A3 = LEADER + w16(r, OBJ + sgn(w16(r, rec(c) + 46)) + 14)
        ent = OBJ + sgn(w16(r, A3 + 20))
        d0 = w16(r, ent + 4)
        trees, seen_ = [], set()
        while d0 and d0 not in seen_ and len(trees) < 100:
            seen_.add(d0)
            trees.append(0x4d252 + sgn(d0))
            d0 = w16(r, 0x4d252 + sgn(d0) + 8)
        for z28 in (0, 1):
            ed = [(a_ + 7, 1, 0x0d) for a_ in trees] + [E(gs, 46, 2, w16(r, rec(c) + 46)), E(gs, 14, 1, 1), E(gs, 36, 2, 0),
                                                       E(gs, 7, 1, r[rec(gs) + 7] | 0x40), E(gs, 28, 2, 0 if z28 == 0 else (rec(gs) - OBJ) & 0xffff)]
            S.append(mk(f"syn_3e_none_b6g{z28}_{i}", rn, gs, "3e", ed, mode=0x3e))
    # $48 map-edge arms
    for i, (rn, s) in enumerate(sweepers[:4]):
        for (px, py) in ((0x0008, 0x2000), (0x3ff8, 0x2000), (0x2000, 0x0008), (0x2000, 0x7ff8)):
            for hd in (0x00, 0x40, 0x80, 0xc0):
                S.append(mk(f"syn_48_edge_{px:x}_{py:x}_{hd:x}_{i}", rn, s, "48",
                            [E(s, 8, 2, px), E(s, 10, 2, py), E(s, 16, 1, 8), E(s, 17, 1, hd), E(s, 18, 2, 300), E(s, 40, 2, 8)], mode=0x48))
    # $62 / $5a: put a marker record at the head of the fisher's cell bucket
    for i, (rn, s) in enumerate(fishers):
        r = ram(rn)
        R = next((x for x in range(1, 512) if x != s and not live_pos(r, x) and r[rec(x) + 5] == 0), 400)
        head = P.BUCKETS + 2 * w16(r, rec(s) + 42)
        base_ed = [(head, 2, (rec(R) - OBJ) & 0xffff), (rec(R) + 0, 2, 0)]
        S.append(mk(f"syn_62_head_{i}", rn, s, "62", [E(s, 18, 2, 0), (rec(R) + 6, 1, 0x20)] + base_ed, mode=0x62))
        for j, sd in enumerate(seeds + [0x55aa55aa, 0x13572468, 0x7777abcd, 0x01020304, 0xf0f0f0f0, 0x2468ace1]):
            S.append(mk(f"syn_5a_head{j}_{i}", rn, s, "5a", [E(s, 18, 2, 0), (rec(R) + 6, 1, 0x18), (rec(R) + 7, 1, 0x10), (P.RNG_SEED, 4, sd)] + base_ed, mode=0x5a))
    # $5a at the map edges: every fail arm of the random-offset search; $48 sweep word $80 with dwell < 8
    for i, (rn, s) in enumerate(fishers[:4]):
        r = ram(rn)
        Rr = next((x for x in range(1, 512) if x != s and not live_pos(r, x) and r[rec(x) + 5] == 0), 400)
        head = P.BUCKETS + 2 * w16(r, rec(s) + 42)
        for (px, py) in ((0x3fe8, 0x2000), (0x2000, 0x7ff0), (0x0008, 0x2000), (0x2000, 0x0008), (0x3fe8, 0x7ff0), (0x0008, 0x0008)):
            for j, sd in enumerate(seeds + [0x55aa55aa, 0x13572468, 0x7777abcd, 0x01020304]):
                S.append(mk(f"syn_5a_edge_{px:x}_{py:x}_{j}_{i}", rn, s, "5a",
                            [E(s, 18, 2, 0), E(s, 8, 2, px), E(s, 10, 2, py), (rec(Rr) + 6, 1, 0x18), (rec(Rr) + 7, 1, 0x10), (rec(Rr), 2, 0),
                             (head, 2, (rec(Rr) - OBJ) & 0xffff), (P.RNG_SEED, 4, sd)], mode=0x5a))
    for i, (rn, s) in enumerate(sweepers[:4]):
        for (px, py) in ((0x0008, 0x2000), (0x3ff8, 0x2000), (0x2000, 0x0008), (0x2000, 0x7ff8)):
            for hd in (0x00, 0x40, 0x80, 0xc0):
                for dw in (3, 0x40):
                    S.append(mk(f"syn_48_edge80_{px:x}_{py:x}_{hd:x}_{dw:x}_{i}", rn, s, "48",
                                [E(s, 8, 2, px), E(s, 10, 2, py), E(s, 16, 1, 8), E(s, 17, 1, hd), E(s, 18, 2, dw), E(s, 40, 2, 0x80)], mode=0x48))
    # $5c at the map edges (the clamps of $15fa8)
    for i, (rn, s) in enumerate(fishers[:3]):
        for (px, py, sx, sy) in ((4, 0x2000, 0xf8, 0), (0x3ffc, 0x2000, 8, 0), (0x2000, 4, 0, 0xf8), (0x2000, 0x7ffc, 0, 8), (4, 4, 0xf8, 0xf8),
                                 (0x3ffc, 0x7ffc, 8, 8), (0x2000, 0x1f00, 0, 0xf0), (0x2000, 0x0100, 0, 0x90)):
            S.append(mk(f"syn_5c_edge_{px:x}_{py:x}_{i}", rn, s, "5c", [E(s, 8, 2, px), E(s, 10, 2, py), E(s, 12, 1, sx), E(s, 13, 1, sy), E(s, 18, 2, 5)], mode=0x5c))
    # $5c: all 16 corner combinations of the altitude-plane cell under the fisher, three sub-cell offsets
    for i, (rn, s) in enumerate(fishers[:3]):
        r = ram(rn)
        for lo6, lo7 in ((0x10, 0x20), (0xf0, 0x80), (0x80, 0xf0), (0xc0, 0xc0)):
            px, py = 0x1000 | lo6, 0x2000 | lo7
            idx = ((py >> 8) << 6) + (px >> 8)
            for combo in range(16):
                ed = [E(s, 8, 2, px), E(s, 10, 2, py), E(s, 12, 2, 0), E(s, 18, 2, 5)]
                ed += [(F.PLANES + idx + off, 1, 1 if combo >> k & 1 else 0) for k, off in enumerate((0, 1, 64, 65))]
                S.append(mk(f"syn_5c_corner{combo:x}_{lo6:x}_{lo7:x}_{i}", rn, s, "5c", ed, mode=0x5c))
    # ---- $4c with a side mismatch: poke the sound flag the callcap would otherwise wait on forever
    for i, (rn, s) in enumerate(base[:6]):
        r = ram(rn)
        side = r[rec(s) + 5]
        S.append(mk(f"syn_4c_side2_{i}", rn, s, "4c", [E(s, 5, 1, 1 if side != 1 else 2), E(s, 42, 2, 0), (0x2c993, 1, 0)], mode=0x4c))
    return S


def run_state(h, st):
    outp = ROOT / OUT / f"o_{st['name']}.json"
    snap = snap_of(st["ram"])
    if not (REUSE and outp.exists()):
        if outp.exists():
            outp.unlink()
        cmds = [f"w {a:x} {w:08x}" for a, w in st["pokes"]]
        cmds.append(f"callcap 14b62 2000000 {OUT}/o_{st['name']}.json")
        h.run_repl(cmds, snap)
    return outp


def evaluate(st, outp):
    r0 = ram(st["ram"])
    pk = Harness.poked_ram(r0, st["pokes"])
    if not outp.exists():
        return st["name"], "NO OUTPUT", None
    j = json.load(open(outp))
    if j.get("outcome") != "returned":
        return st["name"], f"outcome={j.get('outcome')}", None
    after = bytearray(pk)
    for a, b0, b1 in j["mem"]:
        after[a] = b1
    real = Harness.tracked_delta(pk, after)
    outside = {a: v for a, v in Harness.outside_delta(j["mem"]).items() if not 0x2c000 <= a < 0x2d000}   # the callcap stack
    m = P.Mem(pk)
    try:
        sys.settrace(_tracer)
        try:
            P.reconstruct(m)
        finally:
            sys.settrace(None)
    except AssertionError as e:
        return st["name"], f"ASSERT {e}", None
    recon = Harness.tracked_delta(pk, m.r)
    keys = set(real) | set(recon)
    bad = [k for k in keys if real.get(k) != recon.get(k)]
    return st["name"], "ok" if not bad else f"MISMATCH x{len(bad)}", dict(keys=len(keys), bad=sorted(bad), real=real, recon=recon,
                                                                         outside=outside, steps=j["steps"], raw=len(j["mem"]))


REUSE = "reuse" in sys.argv
COVER = collections.defaultdict(set)         # function name -> executed line numbers in fsm15_ref.py
_REF = str(Path(F.__file__).resolve())


def _tracer(frame, event, arg):
    if frame.f_code.co_filename != _REF:
        return None

    def local(fr, ev, a):
        if ev == "line":
            COVER[fr.f_code.co_name].add(fr.f_lineno)
        return local
    COVER[frame.f_code.co_name].add(frame.f_lineno)
    return local


def report_coverage():
    """Lines of the handler bodies (`h*` functions and the new leaves) that no state executed."""
    import ast
    src = Path(_REF).read_text()
    tree = ast.parse(src)
    lines = src.splitlines()
    print("\nUNCOVERED LINES of the model (a branch no state exercised):")
    nunc = ntot = 0
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or not (node.name.startswith("h") or node.name.startswith("call_") or node.name in ("_fish_target", "_contact_38")):
            continue
        body_lines = set()
        for n in ast.walk(node):
            if isinstance(n, ast.stmt) and not isinstance(n, (ast.FunctionDef,)) and not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)):
                body_lines.add(n.lineno)
        miss = sorted(body_lines - COVER[node.name])
        ntot += len(body_lines)
        nunc += len(miss)
        if miss:
            print(f"  {node.name:18} {len(miss):3d}/{len(body_lines):3d}: " + ", ".join(f"{l}" for l in miss))
    print(f"covered statements: {ntot - nunc}/{ntot}")


def main():
    F.install()
    only = next((a for a in sys.argv[1:] if a != "reuse"), None)
    anchor = all_rams()[0]
    h = Harness(snap_of(anchor), f"{AG}/ram/{anchor}.ram", disk="scratchpad/powermonger.st", out_dir=OUT)
    (ROOT / OUT).mkdir(parents=True, exist_ok=True)
    states = natural_states() + syn_states()
    if only:
        states = [s for s in states if only in s["name"]]
    seen = set()
    uniq = []
    for s in states:
        if s["name"] in seen:
            continue
        seen.add(s["name"])
        uniq.append(s)
    states = uniq
    with cf.ThreadPoolExecutor(max_workers=10) as ex:
        paths = list(ex.map(lambda s: run_state(h, s), states))
    tot = ok = n = 0
    bymode = collections.defaultdict(lambda: [0, 0, 0, 0])
    fails = []
    for st, outp in zip(states, paths):
        name, status, info = evaluate(st, outp)
        md = st["tag"]
        if info is None:
            print(f"{name:34} {status}")
            fails.append((name, status))
            bymode[md][3] += 1
            continue
        n += 1
        tot += info["keys"]
        ok += info["keys"] - len(info["bad"])
        b = bymode[md]
        b[0] += 1
        b[1] += info["keys"]
        b[2] += info["keys"] - len(info["bad"])
        out_note = f" outside={len(info['outside'])}" if info["outside"] else ""
        print(f"{name:34} steps={info['steps']:6d} raw={info['raw']:3d} keys={info['keys']:3d}{out_note}  {status}")
        if info["bad"]:
            for k in info["bad"][:6]:
                fails.append((name, hex(k), info["real"].get(k), info["recon"].get(k)))
        if info["outside"]:
            print(f"   outside bytes: {sorted(hex(a) for a in info['outside'])[:8]}")
    print(f"\nTRACKED BYTES: {ok}/{tot} identical over {n} states ({len(fails)} failures/unrun)")
    report_coverage()
    print("mode  states tracked ok  unrun")
    for md, (c, t, o, u) in sorted(bymode.items()):
        print(f"${md:3}  {c:5d} {t:6d} {o:6d} {u:3d}")
    unrun = [f_ for f_ in fails if len(f_) == 2]
    mism = [f_ for f_ in fails if len(f_) != 2]
    if unrun:
        print("UNRUN (a model assertion for an arm out of scope, or a synthetic state the emulator itself cannot run):")
        for f_ in unrun[:80]:
            print("  ", f_)
    if mism:
        print("MISMATCHES:")
        for f_ in mism[:80]:
            print("  ", f_)
        sys.exit(1)
    print(f"PASS: {ok}/{tot} tracked bytes over {n} states, {len(unrun)} unrun")


if __name__ == "__main__":
    main()
