"""Differential gate of `$4de2` (the party classifier used by `$4bc8`, the developers' `_setup_f`) against the real 68000.

`$4de2` takes a party record in A0 and returns its class in D7.w and its nation in D3.b, with A0 moved to the record that
stands for the party:
   2  a lord (A0 inside the leader table $4e514..$4f914), or a man with no group standing within 8 cells (Chebyshev) of his
      home settlement: A0 := his lord, D3 := the lord's nation
   4  a man in a group: a lead (flag bit 4) with word 42 set, or a follower (flag bit 6) resolved to his lead (28(A0)); a group
      whose state is neither 8 nor $d is first broken out of camp (`jsr $37c2`, D2 = the group offset)
   6  a man with no group away from home
   8  category 8 (D3 := 0), $a categories $14/$16 (D3 := 0), $c category 4 (D3 := 0), 0 anything else (D3 := byte 5)
The model is `call_4de2` below; the `$37c2` path uses the proven `pm_fsm_ref.call_37c2`.

States: natural memory from several snapshots with A0 preset to every lord with a nation, every lead, a sample of followers,
lone men, animals, trees and other records; plus synthetic states (field pokes) for the paths natural memory rarely holds:
a follower with lead word 0, a lead flag without a group, a group in each state, a lone man moved next to / away from home,
the animal categories. Compared: D7.w, D3.b, A0, and every RAM byte the call changed (stack excluded).

Usage: python3 gate_party_class.py [reuse] [substr]
Data under $PM_WORK (default scratchpad/pmwork)/gate4de2/.
"""
import collections
import json
import os
import random
import struct
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def root():
    for d in Path(__file__).resolve().parents:
        if (d / "tools" / "rdis.py").exists():
            return d
    sys.exit("repo root not found")


ROOT = Path(os.environ.get("M68000_ROOT", root()))
WORK_REL = Path(os.environ.get("PM_WORK", "scratchpad/pmwork")) / "gate4de2"
WORK = ROOT / WORK_REL
WORK.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "tools"))
import pm_fsm_ref as P  # noqa: E402
from gfxview import load_ram  # noqa: E402
from pm_fsm_diff import Harness  # noqa: E402

OBJ, LORDS, LORDS_HI, SETTL, GROUPS = 0x51b66, 0x4e514, 0x4f914, 0x4f916, 0x51538
SNAPS = ["scratchpad/pm121/run/k5_s4.snap", "scratchpad/pm143/run/rand1_s1.snap", "scratchpad/pm148/arms/long/L2G_k0_c1.snap",
         "scratchpad/pm148/arms/long/L2G_k76_c1.snap", "scratchpad/pm148/arms/long/L2G_k108_c1.snap",
         "scratchpad/pm143/run/p0k60_s3.snap"]
args = sys.argv[1:]
reuse = "reuse" in args
only = next((a for a in args if a != "reuse"), None)


def s16(v):
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v


# ------------------------------------------------------------------ model
def call_4de2(m, A0):
    """Returns (A0, D3 low byte, D7 low word); memory effects only through $37c2."""
    if LORDS <= A0 <= LORDS_HI:                                   # cmpa.l #$4e514 / blt ; cmpa.l #$4f914 / bgt
        return A0, m.bu(A0), 2                                    # $4df2: move.b 0(A0),D3 ; move.w #2,D7
    D3 = m.bu(A0 + 5)                                             # $4dfc
    cat = m.bu(A0 + 6)
    if cat not in (0, 0xe):                                       # $4ea8
        if cat == 8:
            return A0, 0, 8
        if cat in (0x14, 0x16):
            return A0, 0, 0xa
        if cat == 4:
            return A0, 0, 0xc
        return A0, D3, 0
    # $4e0c: a man
    if not (m.bu(A0 + 7) & 0x10):
        if m.bu(A0 + 7) & 0x40:                                   # $4e6c: a follower -> his lead (28(A0); 0 -> record 0)
            A0 = (OBJ + s16(m.wu(A0 + 28))) & 0xffffff
        else:
            return _home(m, A0)
    D2 = m.wu(A0 + 42)                                            # $4e7c
    if D2 == 0:
        return _home(m, A0)
    st = m.wu(GROUPS + s16(D2))
    if st not in (8, 0xd):
        P.call_37c2(m, D2)                                        # saves and restores D0/D1/A0/A1/A3
    return A0, m.bu(A0 + 5), 4


def _home(m, A0):                                                 # $4e1c
    A2 = (SETTL + s16(m.wu(A0 + 34))) & 0xffffff
    cell = m.wu(A2 + 12)
    dx = abs((cell & 0x3f) - m.bu(A0 + 8))
    dy = abs((cell >> 6) - m.bu(A0 + 10))
    if max(dx, dy) < 9:                                           # cmp.w #9,D0 ; bge $4e62 (both are small positives)
        L = (LORDS + s16(m.wu(A2 + 14))) & 0xffffff
        return L, m.bu(L), 2
    return A0, m.bu(A0 + 5), 6


# ------------------------------------------------------------------ states
def natural_cases(ram, rng):
    m = P.Mem(ram)
    out = []
    for a in range(LORDS, LORDS_HI, 32):
        if m.bu(a):
            out.append(("lord", a))
    men = collections.defaultdict(list)
    for i in range(1, 512):
        a = OBJ + 50 * i
        if m.bs(a + 5) == 0 and m.bu(a + 6) == 0:
            continue
        cat, fl = m.bu(a + 6), m.bu(a + 7)
        if cat in (0, 0xe):
            kind = "lead" if fl & 0x10 else "follower" if fl & 0x40 else "lone"
        else:
            kind = f"cat{cat:x}"
        men[kind].append(a)
    for kind, lst in men.items():
        rng.shuffle(lst)
        out += [(kind, a) for a in lst[: (40 if kind == "lead" else 12)]]
    return out


def synthetic_cases(ram, rng):
    """(tag, A0, {addr: byte}) field edits on natural records."""
    m = P.Mem(ram)
    recs = [OBJ + 50 * i for i in range(1, 512)]
    men_ = [a for a in recs if m.bs(a + 5) > 0 and m.bu(a + 6) == 0]
    leads = [a for a in men_ if m.bu(a + 7) & 0x10 and m.wu(a + 42)]
    lone = [a for a in men_ if not m.bu(a + 7) & 0x50]
    fol = [a for a in men_ if m.bu(a + 7) & 0x40]
    out = []
    for st in (2, 3, 5, 6, 7, 8, 9, 0xd):                          # each group state on a real lead
        a = rng.choice(leads)
        g = GROUPS + s16(m.wu(a + 42))
        out.append((f"lead_state{st:x}", a, {g: st >> 8, g + 1: st & 0xff}))
    for i in range(3):                                            # a lead flag without a group
        a = rng.choice(leads)
        out.append((f"lead_nogroup{i}", a, {a + 42: 0, a + 43: 0}))
    for i in range(2):                                            # a follower whose lead word is 0 (the nop at $4e72)
        a = rng.choice(fol)
        out.append((f"follower_lead0_{i}", a, {a + 28: 0, a + 29: 0}))
    for i, d in enumerate((0, 1, 7, 8, 9, 10, 30)):                # a lone man at distance d from his home cell
        a = rng.choice(lone)
        A2 = SETTL + s16(m.wu(a + 34))
        cell = m.wu(A2 + 12)
        x, y = cell & 0x3f, cell >> 6
        nx = x + d if x + d < 64 else x - d
        ny = y + (d // 2 if i % 2 else d)
        ny = ny if ny < 128 else y - d
        out.append((f"lone_d{d}", a, {a + 8: nx & 0xff, a + 10: ny & 0xff}))
    for cat in (0xe, 8, 0x14, 0x16, 4, 2, 0x10, 0x18, 0xc, 0x20):    # categories on a lone man's record
        a = rng.choice(lone)
        out.append((f"cat{cat:x}", a, {a + 6: cat}))
    for cat in (0xe,):                                            # category $e on a lead
        a = rng.choice(leads)
        out.append(("lead_cate", a, {a + 6: cat}))
    return out


# ------------------------------------------------------------------ runs
def repl(snap, cmds):
    p = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", snap, "repl"],
                       input="\n".join(["disk scratchpad/powermonger.st"] + cmds + ["q"]) + "\n",
                       capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE="1"), timeout=1200)
    return p.stdout + p.stderr


stats = collections.Counter()
classes = collections.Counter()
fails = []


def check(tag, ram0, A0, j):
    if j.get("outcome") != "returned":
        fails.append((tag, "outcome", j.get("outcome")))
        return
    P.init_tables(ram0)
    m = P.Mem(ram0)
    a0, d3, d7 = call_4de2(m, A0)
    rn = j["regN"]
    got = (rn[8] & 0xffffff, rn[3] & 0xff, rn[7] & 0xffff)
    sp = j["entrySP"]
    real = {a: b1 for a, b0, b1 in j["mem"] if not sp - 0x300 <= a < sp + 8}
    model = {a: m.r[a] for a in range(len(ram0)) if m.r[a] != ram0[a]}
    keys = set(real) | set(model)
    bad = [a for a in keys if real.get(a, ram0[a]) != model.get(a, ram0[a])]
    stats["states"] += 1
    stats["bytes"] += len(keys)
    stats["bytes_ok"] += len(keys) - len(bad)
    classes[d7] += 1
    if got != (a0, d3, d7) or bad:
        fails.append((tag, f"real A0/D3/D7 {got[0]:x}/{got[1]:x}/{got[2]:x} model {a0:x}/{d3:x}/{d7:x}",
                       [(hex(a), real.get(a, ram0[a]), model.get(a, ram0[a])) for a in sorted(bad)[:6]]))
    else:
        stats["states_ok"] += 1
        if model:
            stats["with_memory"] += 1


def job_nat(snap):
    rng = random.Random(snap)
    ram0, _ = load_ram(str(ROOT / snap))
    cases = natural_cases(ram0, rng)
    stem = Path(snap).stem
    outs = [(f"{stem}_{kind}_{a:x}", a, WORK / f"n_{stem}_{a:x}.json") for kind, a in cases]
    todo = [(t, a, o) for t, a, o in outs if not (reuse and o.exists())]
    if todo:
        repl(snap, [f"callcap 4de2 200000 {o.relative_to(ROOT)} A0={a:x}" for t, a, o in todo])
    return ram0, outs


def job_syn(item):
    snap, tag, A0, pairs, ram0 = item
    pokes = Harness.bytepokes(ram0, pairs)
    o = WORK / f"s_{tag}.json"
    if not (reuse and o.exists()):
        o.unlink(missing_ok=True)
        repl(snap, [f"w {a:x} {v:08x}" for a, v in pokes] + [f"callcap 4de2 200000 {o.relative_to(ROOT)} A0={A0:x}"])
    return tag, A0, Harness.poked_ram(ram0, pokes), o


def main():
    snaps = [s for s in SNAPS if (ROOT / s).exists()]
    with ThreadPoolExecutor(2) as ex:
        for ram0, outs in ex.map(job_nat, snaps):
            for tag, a, o in outs:
                if only and only not in tag:
                    continue
                stats["natural"] += 1
                check(tag, ram0, a, json.load(open(o)) if o.exists() else {"outcome": "missing"})
    syn = []
    for snap in snaps[:2]:
        ram0, _ = load_ram(str(ROOT / snap))
        for tag, A0, pairs in synthetic_cases(ram0, random.Random(snap + "syn")):
            syn.append((snap, f"{Path(snap).stem}_{tag}", A0, pairs, ram0))
    with ThreadPoolExecutor(2) as ex:
        for tag, A0, ram1, o in ex.map(job_syn, syn):
            if only and only not in tag:
                continue
            stats["synthetic"] += 1
            check(tag, ram1, A0, json.load(open(o)) if o.exists() else {"outcome": "missing"})
    print(f"$4de2 gate: {stats['states_ok']}/{stats['states']} states "
          f"({stats['natural']} natural, {stats['synthetic']} synthetic; {stats['with_memory']} with a $37c2 memory delta), "
          f"{stats['bytes_ok']}/{stats['bytes']} changed bytes")
    print("classes returned:", dict(sorted(classes.items())))
    for f in fails[:20]:
        print("FAIL", f)


if __name__ == "__main__":
    main()
