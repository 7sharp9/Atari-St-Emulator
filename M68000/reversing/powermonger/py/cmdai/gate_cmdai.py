"""141st: the commander AI `$6522` and its leaves against the real 68000.

  nat     `callcap 6522` on every natural entry of corpus/ (capture_corpus.py: 35 land snapshots x up to 9 ticks): every byte the real
          call changed against every byte the model (`cmdai_ref.call_6522`) changed, over the whole of RAM except the stack.
  fuzz    the same on synthetic states: the groups of the AI sides rewritten with random states / men / food / timers / campaign
          ids / targets / leads (valid record offsets), the slots of the sides set to 4, the cross-index `$58042` sometimes cleared,
          the queued-order flag sometimes set.  Seeded: the states are the same on every run.
  leaves  `callcap 69b4 / 68fe / 68ee / 66e8 / 6762 / 6822 / 67ee` with register presets: the returned registers (D0, D1, D3, A3) and
          every changed byte against the model.

    cd M68000 && .venv/bin/python reversing/powermonger/py/cmdai/gate_cmdai.py [nat] [fuzz] [leaves] [reuse] [-j N]
"""
import collections
import json
import os
import random
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[4]))
WORK_REL = "scratchpad/pm141/agents/cmdai"          # data (corpus/, g/, gx/, gw/, census/): scratchpad, not committed
WORK = ROOT / WORK_REL
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(HERE))
import cmdai_ref as C
import pm_fsm_ref as P
from pm_fsm_diff import Harness

REL = Path(WORK_REL)
OUT = REL / "g"
STACK = (0x2c800, 0x2c930)
(ROOT / OUT).mkdir(parents=True, exist_ok=True)
DISK = "scratchpad/powermonger.st"
args = sys.argv[1:]
JOBS = int(args[args.index("-j") + 1]) if "-j" in args else 4
modes = [a for a in args if a in ("nat", "fuzz", "leaves")] or ["nat", "fuzz", "leaves"]
reuse = "reuse" in args
only = next((a for a in args if a not in ("nat", "fuzz", "leaves", "reuse", "-j") and not a.isdigit()), None)


def run(snap, cmds):
    argv = ["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", str(snap), "repl", "--disk-a", DISK]
    p = subprocess.run(argv, input="".join(c + "\n" for c in cmds) + "q\n", capture_output=True, text=True, cwd=ROOT,
                       timeout=600, env=dict(os.environ, ATARI_NOTRACE="1"))
    return p.stdout + p.stderr


def real_delta(j):
    sp = j["entrySP"]
    return {a: b1 for a, b0, b1 in j["mem"] if not sp - 0x300 <= a < sp}


def model_delta(m, ram0, sp):
    return {a: m.r[a] for a in range(len(ram0)) if m.r[a] != ram0[a] and not sp - 0x300 <= a < sp}


stats = collections.Counter()
fails, excluded = [], []
arms = collections.Counter()


def compare(tag, real, model, ram0):
    keys = set(real) | set(model)
    bad = [a for a in keys if real.get(a, ram0[a]) != model.get(a, ram0[a])]
    stats["states"] += 1
    stats["bytes"] += len(keys)
    stats["bytes_ok"] += len(keys) - len(bad)
    if bad:
        fails.append((tag, [(hex(a), real.get(a, ram0[a]), model.get(a, ram0[a])) for a in sorted(bad)[:8]]))
    else:
        stats["states_ok"] += 1


# ---------------------------------------------------------------- nat
def job_nat(sn):
    tag = f"{sn.parent.name}/{sn.stem}"
    out = ROOT / OUT / f"o_nat_{sn.parent.name}_{sn.stem}.json"
    if not (reuse and out.exists()):
        out.unlink(missing_ok=True)
        run(sn.relative_to(ROOT), [f"callcap 6522 3000000 {OUT}/o_nat_{sn.parent.name}_{sn.stem}.json"])
    return tag, sn, out


def ram_of(sn):
    """The raw RAM of a snapshot: the .ram beside it, else made under g/ram/ (the pm122 `$661a` captures have none)."""
    r = sn.with_suffix(".ram")
    if r.exists():
        return r.read_bytes()
    from disassemble import ram_from_snap
    cache = ROOT / OUT / "ram" / f"{sn.parent.name}_{sn.stem}.ram"
    if not cache.exists():
        cache.parent.mkdir(exist_ok=True)
        cache.write_bytes(ram_from_snap(str(sn)))
    return cache.read_bytes()


def do_nat():
    snaps = sorted(s for s in (ROOT / REL / "corpus").glob("*.snap") if s.with_suffix(".ram").exists())
    # the 25 natural `$661a` captures of the 122nd pass: a call stopped at its first decision, whose memory is the entry state
    # (nothing before `$661a` writes memory: a group that issues returns), so `callcap 6522` from there is a natural entry
    snaps += sorted((ROOT / "scratchpad/pm122/dec").glob("*.snap"))
    if only:
        snaps = [s for s in snaps if only in s.stem]
    with ThreadPoolExecutor(JOBS) as ex:
        for tag, sn, out in ex.map(job_nat, snaps):
            j = json.load(open(out))
            if j.get("outcome") != "returned":
                fails.append((tag, "outcome", j.get("outcome")))
                continue
            ram0 = ram_of(sn)
            P.init_tables(ram0)
            m = P.Mem(ram0)
            C.TRACE.clear()
            C.call_6522(m)
            arms.update(set(C.TRACE))
            stats["nat"] += 1
            compare(tag, real_delta(j), model_delta(m, ram0, j["entrySP"]), ram0)


# ---------------------------------------------------------------- fuzz
def lords(m):
    return [a for a in range(C.LORDS, C.LORDS_END, 32) if m.bu(a) != 0]


def men(m):
    return [P.OBJ + s * 50 for s in range(1, 512) if m.bu(P.OBJ + s * 50 + 6) == 0 and 0 < m.bu(P.OBJ + s * 50 + 5) < 128]


def off(a):
    return (a - P.OBJ) & 0xffff


def fuzz_state(m, rng, variant=0):
    L, M = lords(m), men(m)
    for slot in range(1, 5):
        a = C.CMD + 6 * slot
        m.wb(a, slot)
        m.wb(a + 1, 0)
        m.ww(a + 2, 0)
        m.wb(a + 4, rng.choice((4, 4, 4, 4, 2, 0)) if slot > 1 else rng.choice((4, 4, 2)))
    for s in range(1, 5):
        base = C.GROUPS + s * 0x13c
        m.wl(base, rng.choice((0, 0, 0, 0, 0, 0x1000000)))
        if rng.random() < 0.05:
            m.wb(base + 1, rng.choice((6, 8, 0xc)))
            m.ww(base + 2, rng.randrange(0x2000))
        if rng.random() < 0.1:
            m.ww(C.GROUP_XREF + 2 * s, rng.choice((0, 0x4c + s * 0x13c + 2)))
        own = [a for a in M if m.bu(a + 5) == s] or M
        for k in range(6):
            g = base + 2 * k
            m.ww(g + 28, rng.choice((s, s, s, s, 0, 0xffff)) & 0xffff)
            m.ww(g + 4, rng.choice((0, 0, 0, 0, 0, 2 * k)))
            m.ww(g + 52, rng.choice((0, 1, 3, 4, 5, 6, 12, 21, 22, 23, 40, 80, 3000)))
            m.ww(g + 64, off(rng.choice(own)))
            m.ww(g + 76, rng.choice((6, 6, 6, 9, 9, 2, 3, 4, 5, 7, 8, 0xa, 0xb, 0xc, 0xd, 0xd, 0xe, 0xf, 0x10, 0)))
            m.ww(g + 100, rng.choice((0, off(rng.choice(L)), off(rng.choice(L)), off(rng.choice(L)), off(rng.choice(own)))))
            m.ww(g + 112, rng.choice((0, 1, 5, 30, 100, 400, 0x5fff, 0x7fff, 0xffff, 0x8000)))
            m.ww(g + 136, rng.choice((2, 3, 4)))
            m.ww(g + 40, rng.choice((0, off(rng.choice(own)))))
            m.ww(g + 256, (m.wu(C.TICK) - rng.choice((0, 10, 20, 21, 25, 100, -5 & 0xffff))) & 0xffff)
            m.ww(g + 268, rng.choice((0, 0, 0xd, 0xd, 2, 3, 0xa, 5, 7)))
            m.ww(g + 280, rng.choice((0, 2, 2, 4, 4)))
            m.ww(g + 292, off(rng.choice(M)))
    if variant:                                       # arms the plain fuzz rarely reaches: escort, men fetch behind an enemy, idle
        for s in range(2, 5):
            base = C.GROUPS + s * 0x13c
            for k in range(6):
                g = base + 2 * k
                m.ww(g + 4, 0)
                m.ww(g + 76, rng.choice((6, 9, 9)))
                m.ww(g + 28, s)
                m.ww(g + 256, (m.wu(C.TICK) - 30) & 0xffff)
                m.ww(g + 268, 0)
                if variant == 1:                      # group 0 supports (state d, phase 4) and the others have men
                    m.ww(g + 52, rng.choice((22, 30, 3000)) if k else rng.choice((22, 30)))
                    if k == 0:
                        m.ww(g + 76, 0xd)
                        m.ww(g + 280, 4)
                elif variant == 3:                    # 22 men, every lord holds 20 at home: no enemy below 18, one below 22 + 20
                    m.ww(g + 52, 22)
                else:                                 # few men, few lords with men at home
                    m.ww(g + 52, rng.choice((0, 1, 4, 5, 6, 9, 12)))
                    m.ww(g + 112, rng.choice((0x5fff, 0x7fff, 200)))
        for a in L:
            m.ww(a + 8, 20 if variant == 3 else rng.choice((0, 0, 1, 2, 3)) if variant == 2 else rng.choice((0, 1, 2)))
            if variant == 2 and rng.random() < 0.3:
                m.wb(a, 0)
    for a in ([] if variant else L):                  # the lords: men at home, food, and sometimes no nation
        m.ww(a + 8, rng.choice((0, 1, 2, 3, 10, 60, 500)))
        m.ww(a + 6, rng.choice((0, 1, 2, 5, 40, 1000)))
        if rng.random() < 0.1:
            m.wb(a, 0)
        if rng.random() < 0.05:                       # a lord on a man's cell
            m.ww(a + 4, ((m.wu(rng.choice(M) + 10) >> 8) << 6) | (m.wu(rng.choice(M) + 8) >> 8) & 0x3f)
    if rng.random() < 0.3:                            # the bias bytes of the side blocks
        for i in range(5 * 32):
            m.wb(C.ASSESS + 15 + i, rng.randrange(256))


def job_fuzz(args_):
    base, i, pokes = args_
    out = ROOT / OUT / f"o_fz_{base.stem}_{i}.json"
    if not (reuse and out.exists()):
        out.unlink(missing_ok=True)
        run(base.relative_to(ROOT), [f"w {a:x} {w:08x}" for a, w in pokes] + [f"callcap 6522 3000000 {OUT}/o_fz_{base.stem}_{i}.json"])
    return base, i, out


def do_fuzz(n_per_base=40):
    bases = [ROOT / REL / "corpus" / f"{b}.snap" for b in ("k0_1", "k5_8", "k25_16", "k60_4", "k105_2", "k142_1", "k40_8", "k15_4")]
    bases = [b for b in bases if b.exists()]
    jobs = []
    rams = {}
    for bi, base in enumerate(bases):
        ram0 = base.with_suffix(".ram").read_bytes()
        rams[base] = ram0
        for i in range(n_per_base):
            rng = random.Random(1000 * bi + i)
            P.init_tables(ram0)
            m = P.Mem(ram0)
            fuzz_state(m, rng, i % 4)
            pairs = {a: m.r[a] for a in range(len(ram0)) if m.r[a] != ram0[a]}
            jobs.append((base, i, Harness.bytepokes(ram0, pairs)))
    with ThreadPoolExecutor(JOBS) as ex:
        for base, i, out in ex.map(job_fuzz, jobs):
            tag = f"fz_{base.stem}_{i}"
            if only and only not in tag:
                continue
            j = json.load(open(out))
            ram0 = rams[base]
            pokes = jobs[[(b, k) for b, k, _ in jobs].index((base, i))][2]
            ram1 = Harness.poked_ram(ram0, pokes)
            if j.get("outcome") != "returned":
                fails.append((tag, "outcome", j.get("outcome")))
                continue
            m = P.Mem(ram1)
            C.TRACE.clear()
            try:
                C.call_6522(m)
            except (AssertionError, IndexError) as e:
                excluded.append((tag, repr(e)[:60]))
                continue
            arms.update(C.TRACE)
            stats["fuzz"] += 1
            compare(tag, real_delta(j), model_delta(m, ram1, j["entrySP"]), ram1)


# ---------------------------------------------------------------- leaves
def reg(j, name):
    i = ("D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 A7").split().index(name)
    return j["regN"][i]


def do_leaves():
    """One REPL per (snapshot, leaf): the presets are fuzzed, the memory is the natural one."""
    base = ROOT / REL / "corpus" / "k5_8.snap"
    ram0 = base.with_suffix(".ram").read_bytes()
    P.init_tables(ram0)
    m0 = P.Mem(ram0)
    L, M = lords(m0), men(m0)
    rng = random.Random(7)
    cases = []                                                    # (tag, cmd, check(j))
    # $68ee: pure arithmetic
    for i in range(40):
        d1 = rng.choice((0, 1, 7, 8, 9, 100, 0xffff, 0x8000, 0x7fff, rng.randrange(65536)))
        d3 = rng.choice((0, 1, 2, 0x7fff, 0xffff, rng.randrange(65536)))
        cases.append((f"68ee_{i}", f"callcap 68ee 1000 {{o}} D1={d1:x} D3={d3:x}",
                      lambda j, d1=d1, d3=d3: (reg(j, "D1") & 0xffff) == C.call_68ee(d1, d3)))
    # $69b4 / $68fe: the lead A2 and the selector D1
    for i in range(60):
        a2 = rng.choice(M)
        d1 = rng.choice((6, 8))
        cases.append((f"69b4_{i}", f"callcap 69b4 100000 {{o}} D0=0 A2={a2:x} D1={d1:x}",
                      lambda j, a2=a2, d1=d1: _chk69(m0, j, a2, d1)))
    for i in range(80):
        a2 = rng.choice(M)
        side = rng.randrange(1, 5)
        k = rng.randrange(6)
        a1 = C.GROUPS + side * 0x13c + 2 * k
        d1 = rng.choice((0, 1, 2, 4, 5, 10, 30, 40, 70, 0x7ffe, 0xffff))
        cases.append((f"68fe_{i}", f"callcap 68fe 100000 {{o}} A1={a1:x} A2={a2:x} D1={d1:x}",
                      lambda j, a1=a1, a2=a2, d1=d1: _chk68(m0, j, a1, a2, d1)))
    jobs = []
    for tag, cmd, chk in cases:
        out = f"{OUT}/o_lf_{tag}.json"
        jobs.append((tag, cmd.format(o=out), out, chk))

    def go(job):
        tag, cmd, out, chk = job
        if not (reuse and (ROOT / out).exists()):
            (ROOT / out).unlink(missing_ok=True)
            run(base.relative_to(ROOT), [cmd])
        return tag, out, chk

    with ThreadPoolExecutor(JOBS) as ex:
        for tag, out, chk in ex.map(go, jobs):
            if only and only not in tag:
                continue
            j = json.load(open(ROOT / out))
            stats["leaf"] += 1
            if j.get("outcome") != "returned":
                fails.append((tag, "outcome", j.get("outcome")))
                continue
            ok, why = (chk(j), None)
            stats["leaf_ok"] += 1 if ok else 0
            if not ok:
                fails.append((tag, "regs", why))
            if real_delta(j):
                fails.append((tag, "unexpected memory change", sorted(real_delta(j))[:4]))


def do_leaves2(n=160):
    """`$6822`, `$67ee`, `$66e8`, `$6762` on fuzzed memory with fuzzed presets: the returned D0 and every changed byte."""
    base = ROOT / REL / "corpus" / "k5_8.snap"
    ram0 = base.with_suffix(".ram").read_bytes()
    P.init_tables(ram0)
    jobs = []
    for i in range(n):
        rng = random.Random(5000 + i)
        m = P.Mem(ram0)
        fuzz_state(m, rng, i % 4)
        side = rng.randrange(2, 5)
        k = rng.randrange(6)
        A0 = C.CMD + 6 * side
        A1 = C.GROUPS + side * 0x13c + 2 * k
        if i % 4 == 3:                                # `$6762`: a campaign id the table knows, a target lord of the group's own side
            own = [a for a in lords(m) if m.bu(a) == side] or lords(m)
            m.ww(A1 + 268, rng.choice((0xd, 0xd, 2, 3, 0xa, 0xb)))
            m.ww(A1 + 280, rng.choice((2, 2, 4)))
            m.ww(A1 + 100, off(rng.choice(own) if rng.random() < 0.8 else rng.choice(lords(m))))
            m.ww(A1 + 28, side)
            m.ww(C.RNG_BITS, rng.randrange(65536))
        pairs = {a: m.r[a] for a in range(len(ram0)) if m.r[a] != ram0[a]}
        pokes = Harness.bytepokes(ram0, pairs)
        ram1 = Harness.poked_ram(ram0, pokes)
        D7 = 2 * k
        which = ("6822", "67ee", "66e8", "6762")[i % 4]
        L = lords(P.Mem(ram1))
        d0 = rng.choice((2, 4, 6, 8, 0xa, 0xc, 0xe, 0x10))
        d1 = rng.randrange(65536)
        A3 = rng.choice(L)
        A2 = P.OBJ + sx16(m.wu(A1 + 64))
        pre = {"6822": f"D0={d0:x} D1={d1:x}", "67ee": f"D0={d0:x} A3={A3:x}", "66e8": f"A2={A2:x} D2={side:x}", "6762": ""}[which]
        cmd = f"callcap {which} 100000 {{o}} A0={A0:x} A1={A1:x} D7={D7:x} {pre}".strip()
        jobs.append((f"{which}_{i}", which, cmd, pokes, ram1, (A0, A1, D7, d0, d1, A3, A2, side)))

    def go(job):
        tag, which, cmd, pokes, ram1, _ = job
        out = f"{OUT}/o_l2_{tag}.json"
        if not (reuse and (ROOT / out).exists()):
            (ROOT / out).unlink(missing_ok=True)
            run(base.relative_to(ROOT), [f"w {a:x} {w:08x}" for a, w in pokes] + [cmd.format(o=out)])
        return job, out

    with ThreadPoolExecutor(JOBS) as ex:
        for job, out in ex.map(go, jobs):
            tag, which, cmd, pokes, ram1, (A0, A1, D7, d0, d1, A3, A2, side) = job
            if only and only not in tag:
                continue
            j = json.load(open(ROOT / out))
            if j.get("outcome") != "returned":
                fails.append((tag, "outcome", j.get("outcome")))
                continue
            m = P.Mem(ram1)
            C.TRACE.clear()
            if which == "6822":
                r = C.call_6822(m, A0, A1, D7, d0, d1)
            elif which == "67ee":
                r = C.call_67ee(m, A0, A1, A3, D7, d0)
            elif which == "66e8":
                r = C.call_66e8(m, A0, A1, A2, side, D7)
            else:
                r = C.call_6762(m, A0, A1, D7)
            stats["leaf2"] += 1
            sp = j["entrySP"]
            real = real_delta(j)
            model = model_delta(m, ram1, sp)
            keys = set(real) | set(model)
            bad = [a for a in keys if real.get(a, ram1[a]) != model.get(a, ram1[a])]
            stats["leaf2_bytes"] += len(keys)
            d0r = reg(j, "D0")
            d0_ok = which in ("67ee",) or (d0r & 0xffff) == r
            if bad or not d0_ok:
                fails.append((tag, "mem/D0", [hex(a) for a in sorted(bad)[:4]], hex(d0r), r))
            else:
                stats["leaf2_ok"] += 1
            stats["leaf2_" + which] += 1
            if real or r:
                stats["leaf2_active_" + which] += 1


def sx16(v):
    return P.s16(v)


def _chk69(m0, j, a2, d1):
    D3, A3, z = C.call_69b4(m0, a2, d1)
    return (reg(j, "D3") & 0xffff) == D3 and ((reg(j, "A3") == A3) if A3 is not None else True) and \
        ((reg(j, "D3") & 0xffff) == 0xffff) == z


def _chk68(m0, j, a1, a2, d1):
    D3, A3, z = C.call_68fe(m0, a1, a2, d1)
    return (reg(j, "D3") & 0xffff) == D3 and ((reg(j, "A3") == A3) if A3 is not None else True)


if "nat" in modes:
    do_nat()
if "fuzz" in modes:
    do_fuzz()
if "leaves" in modes:
    do_leaves()
    do_leaves2()
print(dict(stats))
print("arms", dict(arms))
for e in excluded[:10]:
    print("  excluded", e)
for f in fails[:25]:
    print("  FAIL", f)
print("PASS" if not fails else "FAIL")
sys.exit(1 if fails else 0)
