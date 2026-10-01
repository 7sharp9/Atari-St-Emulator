"""140th: the order pigeon launch `$4562` (`pm_fsm_ref.call_4562`, which calls `call_45ee`) against the real 68000 through `callcap 4562`
on its natural entries (`capture_hits.py <snap> 4562 1,2,... scratchpad/pm140/pigeon/<name>`, the REPL runs of lands 0, 5, 25, 60) and on
synthetic states (`synth`: the pool full, the group not the local side's, a pool with only the slot after the player's free).

Compared: every byte the real call changed against every byte the model changed, over the whole of RAM except the stack
(`$2c800..$2c930`).  The entry registers A0 (the order slot) and D2 (the group offset) come from the snapshot itself.

    cd M68000 && python reversing/powermonger/py/gate_pigeon_send.py [name-substring] [synth] [reuse]
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

C = "scratchpad/pm140/pigeon"
OUT = "scratchpad/pm140/pigeon/g"
STACK = (0x2c800, 0x2c930)
(ROOT / OUT).mkdir(parents=True, exist_ok=True)
args = [a for a in sys.argv[1:] if a not in ("synth", "reuse")]
only = args[0] if args else None
snaps = sorted(s for s in (ROOT / C).glob("*/*.snap") if s.with_suffix(".ram").exists())
h = Harness(str(snaps[0].relative_to(ROOT)), str(snaps[0].with_suffix(".ram").relative_to(ROOT)), disk="scratchpad/powermonger.st", out_dir=OUT)
tot = ok = n = 0
arms, fails = collections.Counter(), []


def compare(tag, snap_rel, ram0, pokes, entry_regs):
    """callcap 4562 from snap_rel (after the pokes) and compare with the model run on ram0 + pokes."""
    global tot, ok, n
    out = ROOT / OUT / f"o_{tag}.json"
    if not (out.exists() and "reuse" in sys.argv):
        out.unlink(missing_ok=True)
        h.run_repl([f"w {a:x} {w:08x}" for a, w in pokes] + [f"callcap 4562 2000000 {OUT}/o_{tag}.json"], snap_rel)
    j = json.load(open(out))
    if j.get("outcome") != "returned":
        fails.append((tag, "outcome", j.get("outcome")))
        return
    ram1 = Harness.poked_ram(ram0, pokes)
    real = {a: b1 for a, b0, b1 in j["mem"] if not STACK[0] <= a < STACK[1]}
    P.init_tables(ram1)
    m = P.Mem(ram1)
    P.call_4562(m, entry_regs["A0"], entry_regs["D2"] & 0xffff)
    model = {a: m.r[a] for a in range(len(ram1)) if m.r[a] != ram1[a] and not STACK[0] <= a < STACK[1]}
    keys = set(real) | set(model)
    bad = [a for a in keys if real.get(a, ram1[a]) != model.get(a, ram1[a])]
    launched = any(m.r[a + 6] == 0x14 and ram1[a + 6] == 0 for a in range(P.PIGEONS + 26, P.PIGEON_END, 26))
    arms["launched" if launched else "no_free_record"] += 1
    local = ram1[P.LOCAL_SIDE + 1] == ram1[0x51538 + P.s16(entry_regs["D2"]) - 48 + 1] and \
        int.from_bytes(ram1[P.LOCAL_SIDE:P.LOCAL_SIDE + 2], "big") == int.from_bytes(ram1[0x51538 + P.s16(entry_regs["D2"]) - 48:0x51538 + P.s16(entry_regs["D2"]) - 46], "big")
    arms["local_group" if local else "other_group"] += 1
    tot += len(keys)
    ok += len(keys) - len(bad)
    n += 1
    if bad:
        fails.append((tag, [(hex(a), real.get(a, ram1[a]), model.get(a, ram1[a])) for a in sorted(bad)[:8]]))


for sn in snaps:
    name = f"{sn.parent.name}/{sn.stem}"
    if only and only not in name:
        continue
    ram0 = sn.with_suffix(".ram").read_bytes()
    jl = json.load(open(sn.parent / f"{sn.parent.name}.json"))
    ent = next(e for e in jl if e["snap"].endswith(sn.name))
    compare(sn.stem, str(sn.relative_to(ROOT)), ram0, [], ent["regs"])

if "synth" in sys.argv:
    # a few natural entries as bases; poke the pigeon pool full / free only the last record / mark the group's side
    bases = [s for s in snaps if s.parent.name in ("k5_s1", "k25_s3", "k60_s2", "k0_s2")][:6]
    for sn in bases:
        ram0 = sn.with_suffix(".ram").read_bytes()
        jl = json.load(open(sn.parent / f"{sn.parent.name}.json"))
        ent = next(e for e in jl if e["snap"].endswith(sn.name))
        rel = str(sn.relative_to(ROOT))
        for cname in ("pool_full", "only_last_free", "first_free_only", "local_group", "local_group_pool_full"):
            m = P.Mem(ram0)
            if cname.startswith("local_group"):          # make the group's side the local side: the pending counter `$57fd8[k]` counts it
                m.ww(P.LOCAL_SIDE, m.wu(0x51538 + P.s16(ent["regs"]["D2"] & 0xffff) - 48))
            for a in range(P.PIGEONS + 26, P.PIGEON_END, 26):
                free = (cname == "only_last_free" and a == P.PIGEON_END - 26) or (cname == "first_free_only" and a == P.PIGEONS + 26)
                if cname in ("pool_full", "local_group_pool_full") or (not free and cname != "local_group"):
                    if m.bu(a + 6) == 0:
                        m.wb(a + 6, 0x14)
                        m.wb(a + 5, 0xfe)         # a dead pigeon the pool loop skips, nothing frees it (`$4624`)
                elif free:
                    m.wb(a + 6, 0)
            pairs = {a: m.r[a] for a in range(len(ram0)) if m.r[a] != ram0[a]}
            pokes = Harness.bytepokes(ram0, pairs)
            compare(f"s_{sn.stem}_{cname}", rel, ram0, pokes, ent["regs"])

print(f"states {n}, changed bytes compared {ok}/{tot}, arms {dict(arms)}")
for f in fails[:20]:
    print("  FAIL", f)
print("PASS" if not fails else "FAIL")
sys.exit(1 if fails else 0)
