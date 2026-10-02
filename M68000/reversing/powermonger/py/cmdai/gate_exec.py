"""141st: the order executor `$6a3a` (with `$6ac6`, and `$4562` through `pm_fsm_ref.call_4562`) against the real 68000.

  nat    natural `$6a3a` entries: from each corpus snapshot (a `$6522` entry) `bpc 6a3a 1`, snapshot, `callcap 6a3a`.  A state in which an
         order runs a handler (`$6b38` -> `$3888`, `$4a7a`, ...) is not modelled (those belong to the orders area): it is counted
         as `exec` and not compared.
  synth  `callcap 6a3a` on synthetic slots: random states 0/2/4/`$a`, sides, types and parameters, the sender word 48 of the groups
         poked so that the orders go by pigeon, to a side with no group, or nowhere; states whose model route would run a handler
         are not generated.

Compared: every changed byte of the real call against the model, over RAM except the stack.

    cd M68000 && .venv/bin/python reversing/powermonger/py/cmdai/gate_exec.py [nat] [synth] [reuse]
"""
import collections
import json
import os
import random
import re
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
from disassemble import ram_from_snap
from pm_fsm_diff import Harness

REL = Path(WORK_REL)
OUT = REL / "gx"
(ROOT / OUT).mkdir(parents=True, exist_ok=True)
reuse = "reuse" in sys.argv
modes = [a for a in sys.argv[1:] if a in ("nat", "synth")] or ["nat", "synth"]
stats = collections.Counter()
fails = []
routes = collections.Counter()


def run(snap, cmds):
    p = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", str(snap), "repl", "--disk-a", "scratchpad/powermonger.st"],
                       input="".join(c + "\n" for c in cmds) + "q\n", capture_output=True, text=True, cwd=ROOT, timeout=600,
                       env=dict(os.environ, ATARI_NOTRACE="1"))
    return p.stdout + p.stderr


def deltas(j, ram0, m):
    sp = j["entrySP"]
    real = {a: b1 for a, b0, b1 in j["mem"] if not sp - 0x300 <= a < sp}
    model = {a: m.r[a] for a in range(len(ram0)) if m.r[a] != ram0[a] and not sp - 0x300 <= a < sp}
    return real, model


class Exec(Exception):
    pass


def hook(m, a0, d2):
    raise Exec()


def compare(tag, j, ram0):
    P.init_tables(ram0)
    m = P.Mem(ram0)
    try:
        r = C.call_6a3a(m, hook)
    except Exec:
        stats["exec_not_compared"] += 1
        return
    except AssertionError as e:
        stats["asserted"] += 1
        fails.append((tag, "asserted", str(e)))
        return
    routes.update(r)
    real, model = deltas(j, ram0, m)
    keys = set(real) | set(model)
    bad = [a for a in keys if real.get(a, ram0[a]) != model.get(a, ram0[a])]
    stats["states"] += 1
    stats["bytes"] += len(keys)
    stats["bytes_ok"] += len(keys) - len(bad)
    if bad:
        fails.append((tag, [(hex(a), real.get(a, ram0[a]), model.get(a, ram0[a])) for a in sorted(bad)[:6]]))
    else:
        stats["states_ok"] += 1


def job_nat(sn):
    tag = f"{sn.parent.name}_{sn.stem}"
    out = ROOT / OUT / f"o_{tag}.json"
    snp = ROOT / OUT / f"s_{tag}.snap"
    if not (reuse and out.exists() and snp.exists()):
        out.unlink(missing_ok=True)
        run(sn.relative_to(ROOT), ["bpc 6a3a 1 3000000", f"snap {OUT}/s_{tag}.snap", f"callcap 6a3a 3000000 {OUT}/o_{tag}.json"])
    return tag, out, snp


def do_nat():
    snaps = sorted(s for s in (ROOT / REL / "corpus").glob("*.snap") if s.with_suffix(".ram").exists())
    snaps += sorted((ROOT / "scratchpad/pm122/dec").glob("*.snap"))
    with ThreadPoolExecutor(4) as ex:
        for tag, out, snp in ex.map(job_nat, snaps):
            if not out.exists() or not snp.exists():
                fails.append((tag, "no output"))
                continue
            j = json.load(open(out))
            if j.get("outcome") != "returned":
                fails.append((tag, "outcome", j.get("outcome")))
                continue
            stats["nat"] += 1
            compare(tag, j, ram_from_snap(str(snp)))


def men(m):
    return [P.OBJ + s * 50 for s in range(1, 512) if m.bu(P.OBJ + s * 50 + 6) == 0 and 0 < m.bu(P.OBJ + s * 50 + 5) < 128]


def do_synth(n=80):
    base = ROOT / REL / "corpus" / "k5_8.snap"
    ram0 = base.with_suffix(".ram").read_bytes()
    jobs = []
    seed = 0
    while len(jobs) < n:
        seed += 1
        rng = random.Random(9000 + seed)
        P.init_tables(ram0)
        m = P.Mem(ram0)
        M = men(m)
        for s in range(1, 5):                              # the senders of each side's groups: none, or a man (a pigeon goes out)
            for k in range(6):
                m.ww(C.GROUPS + s * 0x13c + 0x4c + 2 * k + 48, 0)          # 48(group): the group's sender
                if rng.random() < 0.6:
                    m.ww(C.GROUPS + s * 0x13c + 0x4c + 2 * k + 48, (rng.choice(M) - P.OBJ) & 0xffff)
        if rng.random() < 0.3:
            m.ww(C.GROUP_XREF + 2 * rng.randrange(1, 5), 0)
        for s in range(1, 5):
            a = C.CMD + 6 * s
            m.wb(a, rng.choice((s, s, s, rng.randrange(0, 6))))
            m.wb(a + 1, rng.choice((0, 0, 2, 4, 6, 8, 0xa, 0xc, 0x10, 0x16, 0x20)))
            m.ww(a + 2, rng.randrange(65536))
            m.wb(a + 4, rng.choice((0, 2, 4, 4, 0xa)))
        m1 = P.Mem(bytes(m.r))
        try:
            C.call_6a3a(m1, hook)
        except Exec:
            continue
        pairs = {a: m.r[a] for a in range(len(ram0)) if m.r[a] != ram0[a]}
        jobs.append((seed, Harness.bytepokes(ram0, pairs)))

    def go(job):
        seed, pokes = job
        out = f"{OUT}/o_sy_{seed}.json"
        if not (reuse and (ROOT / out).exists()):
            (ROOT / out).unlink(missing_ok=True)
            run(base.relative_to(ROOT), [f"w {a:x} {w:08x}" for a, w in pokes] + [f"callcap 6a3a 3000000 {out}"])
        return job, out

    with ThreadPoolExecutor(4) as ex:
        for (seed, pokes), out in ex.map(go, jobs):
            j = json.load(open(ROOT / out))
            tag = f"sy_{seed}"
            if j.get("outcome") != "returned":
                fails.append((tag, "outcome", j.get("outcome")))
                continue
            stats["synth"] += 1
            compare(tag, j, bytes(Harness.poked_ram(ram0, pokes)))


if "nat" in modes:
    do_nat()
if "synth" in modes:
    do_synth()
print(dict(stats))
print("routes", dict(routes))
for f in fails[:20]:
    print("  FAIL", f)
print("PASS" if not fails else "FAIL")
sys.exit(1 if fails else 0)
