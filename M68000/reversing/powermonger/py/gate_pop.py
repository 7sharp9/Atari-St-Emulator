"""139th: the whole world-build population `$2984` (per lord, per settlement, per man: `$2e1e` allocate, `$2a98` job, health
byte) vs the real 68000 through callcap 2984, on the build of eight lands (k = 0, 1, 5, 10, 25, 60, 100, 142; the land
poke of `build_land.sh`).  Same tracked regions as gate_jobs.py plus every lord and settlement record.

    cd M68000
    for k in 0 1 5 10 25 60 100 142; do
      python tools/capture_hits.py scratchpad/pm67_ok_pre.snap 2984 1 scratchpad/pm139/corpus_2984 --name k$k --max 4000000 \
        --pre 'w 2df92 001400b1' --pre 'w 2df8e 001400b1' --pre 'w 2df96 00010001' --pre 'u 13b9a 80000000' \
        --pre "w 580a0 $(printf '%08x' $((k*0xb+0x3fb)))" --pre "w 5809c $(printf '%04x0000' $((k*0x96+0x672)))"
    done
    python reversing/powermonger/py/gate_pop.py
"""
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import pm_fsm_ref as P
from pm_fsm_diff import Harness

D = "scratchpad/pm139/corpus_2984"
OUT = "scratchpad/pm139/g2"
LANDS = [0, 1, 5, 10, 25, 60, 100, 142]
P.REGIONS = [(P.OBJ + P.REC, P.END, "obj"), (P.BUCKETS, P.BUCKETS + 0x4000, "bucket"),
             (0x4e514, 0x4f914, "leader"), (0x4f916, 0x4f916 + 18 * 240, "settlement"),
             (0x3f86c, 0x4792f, "planes"), (P.ANIMALS, P.FISH_COUNT + 2, "pools"),
             (P.RNG_SEED, P.RNG_SEED + 4, "rng"), (P.JOB_COUNTER, P.JOB_COUNTER + 2, "counter"),
             (P.OBJ_HIGH, P.OBJ_HIGH + 2, "high")]
h = Harness(f"{D}/k0_1.snap", f"{D}/k0_1.ram", disk="scratchpad/powermonger.st", out_dir=OUT)
only = next((a for a in sys.argv[1:] if a != "reuse"), None)

tot = ok = 0
fails = []
arms = collections.Counter()
for k in LANDS:
    name = f"k{k}"
    if only and only not in name:
        continue
    ram0 = (ROOT / D / f"{name}_1.ram").read_bytes()
    h.run_repl([f"callcap 2984 60000000 {OUT}/o_{name}.json"], f"{D}/{name}_1.snap")
    j = json.load(open(ROOT / OUT / f"o_{name}.json"))
    if j.get("outcome") != "returned":
        fails.append((name, "outcome", j.get("outcome")))
        continue
    after = bytearray(ram0)
    for a, b0, b1 in j["mem"]:
        after[a] = b1
    real = Harness.tracked_delta(ram0, after)
    m = P.Mem(ram0)
    P.JOB_TRACE.clear()
    P.call_2984(m)
    recon = Harness.tracked_delta(ram0, m.r)
    keys = set(real) | set(recon)
    bad = [a for a in keys if real.get(a) != recon.get(a)]
    men = sum(1 for s in range(1, 512) if ram0[P.OBJ + s * P.REC + 5] == 0 and m.r[P.OBJ + s * P.REC + 5] != 0)
    tot += len(keys)
    ok += len(keys) - len(bad)
    c = collections.Counter(t for t in P.JOB_TRACE if not t.endswith("_fail") and t != "giveup" and t != "farmer_fail_stale")
    # a merchant is either a 1-in-32 give-up or a man whose five rounds all failed (counted per call: a call's trace ends at its job)
    calls, cur = [], []
    for t in P.JOB_TRACE:
        cur.append(t)
        if t in ("captain", "shepherd", "fisher", "farmer", "merchant"):
            calls.append(cur)
            cur = []
    c["merchant_giveup"] = sum(1 for x in calls if x[-1] == "merchant" and "giveup" in x)
    c["merchant_exhausted"] = sum(1 for x in calls if x[-1] == "merchant" and "giveup" not in x)
    c["farmer_fail_stale"] = P.JOB_TRACE.count("farmer_fail_stale")
    c["farmer_fail_genuine"] = P.JOB_TRACE.count("farmer_fail")
    del c["merchant"]
    arms.update(c)
    print(f"{name:6} steps={j['steps']:7d} men={men:3d} real={len(real):5d} recon={len(recon):5d} "
          f"{dict(c)}  {'ok' if not bad else 'MISMATCH x%d' % len(bad)}")
    for a in sorted(bad)[:12]:
        fails.append((name, hex(a), real.get(a), recon.get(a)))
print(f"\nTRACKED BYTES: {ok}/{tot} identical over {len(LANDS)} builds; jobs {dict(arms)}")
if fails:
    print("FAILURES:")
    for f in fails[:40]:
        print("  ", f)
    sys.exit(1)
print("PASS")
