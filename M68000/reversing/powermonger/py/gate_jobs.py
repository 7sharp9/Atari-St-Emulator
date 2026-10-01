"""139th: the world-build job pick `$2a98` (and its arms `$2b08` shepherd, `$2b68` fisherman, `$2c5a` farmer, merchant,
captain; `$2d0e` animal; `$16808` bucket link) vs the real 68000 through callcap 2a98.

Tracked: the man table, buckets, leaders, settlements (pm_fsm_ref.REGIONS), the four terrain planes `$3f86c..$4792f`,
both pools (`$4ccd6..$4d252`), the RNG seed, the retry counter at `$2b06`, the high-water `$57f66`; and the returned D0.
Natural corpus: the 70 entries of `$2a98` during land 0's build (`capture_hits.py`, below). Synthetic states poke the
RNG seed (so each arm is drawn), pool counters, the leader bit, and the caller's D1 (the stale bound in `$2c5a`).

    cd M68000
    python tools/capture_hits.py scratchpad/pm67_ok_pre.snap 2a98 1,2,...,70 scratchpad/pm139/corpus_2a98 --name l0 \
        --max 4000000 --pre 'w 2df92 001400b1' --pre 'w 2df8e 001400b1' --pre 'w 2df96 00010001' \
        --pre 'u 13b9a 80000000' --pre 'w 580a0 000003fb' --pre 'w 5809c 06720000'
    python reversing/powermonger/py/gate_jobs.py [name-substring]
"""
import collections
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import pm_fsm_ref as P
from pm_fsm_diff import Harness

D = "scratchpad/pm139/corpus_2a98"
OUT = "scratchpad/pm139/g"
P.REGIONS = P.REGIONS + [(0x3f86c, 0x4792f, "planes"), (P.ANIMALS, P.FISH_COUNT + 2, "pools"),
                         (P.RNG_SEED, P.RNG_SEED + 4, "rng"), (P.JOB_COUNTER, P.JOB_COUNTER + 2, "counter"),
                         (P.OBJ_HIGH, P.OBJ_HIGH + 2, "high")]
entries = json.load(open(ROOT / D / "l0.json"))
h = Harness(f"{D}/l0_1.snap", f"{D}/l0_1.ram", disk="scratchpad/powermonger.st", out_dir=OUT)
only = next((a for a in sys.argv[1:] if a != "reuse"), None)


def seeds_for(pred, n, start=1):
    """Seeds whose first LCG draw satisfies pred (the first draw of $2a98 picks the arm)."""
    out, s = [], start
    while len(out) < n:
        m = P.Mem(bytearray(0x300000))
        m.wl(P.RNG_SEED, s)
        if pred(P.rng_12c9a(m)):
            out.append(s)
        s += 0x10001
    return out


SHEP = seeds_for(lambda d: d & 0x1f != 0 and d & 7 == 0, 4)
FISH_ = seeds_for(lambda d: d & 7 in (1, 3, 5, 7), 6)
FARM = seeds_for(lambda d: d & 7 in (2, 4, 6), 6)
GIVEUP = seeds_for(lambda d: d & 0x1f == 0, 2)


def lw(addr, val):
    return (addr, val)


def states():
    S = []
    for e in entries:
        S.append((f"nat{e['hit']:02d}", "nat", e, [], {}))
    # one natural man per kind of cell neighbourhood is enough for the synthetic arms: spread over the 70
    for i, e in enumerate(entries[::5]):
        for tag, seeds in (("shep", SHEP), ("fish", FISH_), ("farm", FARM), ("giveup", GIVEUP)):
            s = seeds[i % len(seeds)]
            S.append((f"syn{e['hit']:02d}_{tag}", tag, e, [lw(P.RNG_SEED, s)], {}))
    for e in entries[2::17]:
        r = Harness.lw_at
        ram = (ROOT / e["ram"]).read_bytes()
        A1 = e["regs"]["A1"]
        s = SHEP[0]
        # animal pool already past $2f8: the shepherd arm returns 0 and the farmer arm follows
        S.append((f"syn{e['hit']:02d}_shepfull", "shepfull", e, [lw(P.RNG_SEED, s), Harness.lw_word(ram, P.ANIMAL_COUNT, 0x2f8)], {}))
        # one slot left in the pool (the loop's second call returns 0)
        S.append((f"syn{e['hit']:02d}_shep1", "shep1", e, [lw(P.RNG_SEED, s), Harness.lw_word(ram, P.ANIMAL_COUNT, 0x2f0)], {}))
        # fisherman with the marker pool full
        S.append((f"syn{e['hit']:02d}_fishfull", "fishfull", e, [lw(P.RNG_SEED, FISH_[0]), Harness.lw_word(ram, P.FISH_COUNT, 0x12c)], {}))
        # the caller's D1 over $80: the farmer arm's row bound fails everywhere
        S.append((f"syn{e['hit']:02d}_d1big", "d1big", e, [lw(P.RNG_SEED, FARM[0])], {"D1": 0x100}))
        # a leader
        S.append((f"syn{e['hit']:02d}_leader", "leader", e, [Harness.lw_at(ram, A1 + 7, ram[A1 + 7] | 0x10)], {}))
    return S


def main():
    tot = ok = n = 0
    fails, seen = [], collections.Counter()
    for name, tag, e, pokes, presets in states():
        if only and only not in name:
            continue
        ram0 = (ROOT / e["ram"]).read_bytes()
        pk = Harness.poked_ram(ram0, pokes)
        cmds = [f"w {a:x} {w:08x}" for a, w in pokes]
        pre = "".join(f" {k}={v:x}" for k, v in presets.items())
        cmds.append(f"callcap 2a98 2000000 {OUT}/o_{name}.json{pre}")
        h.run_repl(cmds, e["snap"])
        outp = ROOT / OUT / f"o_{name}.json"
        j = json.load(open(outp))
        if j.get("outcome") != "returned":
            fails.append((name, "outcome", j.get("outcome")))
            continue
        after = bytearray(pk)
        for a, b0, b1 in j["mem"]:
            after[a] = b1
        real = Harness.tracked_delta(pk, after)
        regs0, regsN = j["reg0"], j["regN"]
        A1, D1 = regs0[8 + 1], presets.get("D1", regs0[1]) & 0xffff      # reg0 is read before the presets apply
        m = P.Mem(pk)
        P.JOB_TRACE.clear()
        d0 = P.call_2a98(m, A1, D1)
        recon = Harness.tracked_delta(pk, m.r)
        keys = set(real) | set(recon)
        bad = [k for k in keys if real.get(k) != recon.get(k)]
        d0_real = regsN[0] & 0xffffffff
        d0_ok = (d0 & 0xffff) == (d0_real & 0xffff)
        tot += len(keys) + 1
        ok += len(keys) - len(bad) + (1 if d0_ok else 0)
        n += 1
        arm = "+".join(P.JOB_TRACE)
        seen[arm] += 1
        outside = Harness.outside_delta(j["mem"])
        status = "ok" if not bad and d0_ok else f"MISMATCH x{len(bad)} D0 {'ok' if d0_ok else 'BAD'}"
        print(f"{name:20} [{tag:8}] {arm:34} D0={d0_real & 0xffff:04x} real={len(real):3d} recon={len(recon):3d}"
              f"{' outside=%d' % len(outside) if outside else ''}  {status}")
        for k in sorted(bad)[:10]:
            fails.append((name, hex(k), real.get(k), recon.get(k)))
        if not d0_ok:
            fails.append((name, "D0", hex(d0_real & 0xffff), hex(d0 & 0xffff)))
    print(f"\nTRACKED BYTES + D0: {ok}/{tot} identical over {n} states")
    for arm, c in sorted(seen.items()):
        print(f"  {c:3d}  {arm}")
    if fails:
        print("FAILURES:")
        for f in fails[:40]:
            print("  ", f)
        sys.exit(1)
    print("PASS")


main()
