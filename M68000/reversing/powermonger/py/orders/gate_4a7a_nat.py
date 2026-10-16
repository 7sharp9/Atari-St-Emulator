"""$4a7a (march and engage: the cell resolver) on its natural entries only, against `callcap 4a7a`.

    cd M68000 && uv run python scratchpad/pm162/g4a7a/gate_4a7a_nat.py [reuse]

Reuses py/orders/gate_orders.py (run_base, judge: every byte the real call changed against every byte the model changed over
all RAM except the stack and the screen) and the model py/orders/orders_ref.py call_4a7a.  The entries are every
n4a7a*.json under ${PM_WORK:-scratchpad/pm162}/g4a7a/nat (capture_clicks.sh: the player's sword clicks; capture_ai.sh:
the AI's calls from the census runs) plus the one entry the orders gate already holds (pm141/agents/orders/nat/n4a7a.json).
Each entry is run at its own registers; the arm the model takes is the class distribution.  A mutant (animal class 8
written as $a, the class $4de2 gives categories $14/$16) is judged on the same callcaps as the negative control.
"""
import collections
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ["M68000_ROOT"]) if os.environ.get("M68000_ROOT") else next(
    p for p in HERE.parents if (p / "tools" / "rdis.py").exists())
PY = ROOT / "reversing" / "powermonger" / "py"
sys.path.insert(0, str(PY / "orders"))
sys.path.insert(0, str(PY))
reuse = "reuse" in sys.argv
sys.argv = sys.argv[:1]                 # gate_orders reads argv at import
import gate_orders as G                 # noqa: E402
O = G.O

WORK = ROOT / os.environ.get("PM_WORK", "scratchpad/pm162") / "g4a7a"
G.OUT = WORK / "g"
G.OUT.mkdir(parents=True, exist_ok=True)
G.REL = G.OUT.relative_to(ROOT).as_posix()
G.reuse = reuse

ARM = {"4a7a_bld": "2 foreign settlement", "4a7a_man": "6 foreign man", "4a7a_A4": "8 animal (8/$14/$16)",
       "4a7a_A5": "$c category 4", "4a7a_none": "none (records, no target)", "4a7a_empty": "empty cell"}


def mutant(m, D0, D1, D2):
    O.call_4a7a(m, D0, D1, D2)
    if "4a7a_A4" in O.TRACE:
        A3 = (G.GROUP + G.P.s16(D2)) & 0xfffff
        m.ww(A3 + 204, 0x0a)


def main():
    files = sorted((WORK / "nat").glob("n4a7a*.json")) + [ROOT / "scratchpad/pm141/agents/orders/nat/n4a7a.json"]
    cases = collections.defaultdict(list)
    for jf in files:
        for e in json.load(open(jf)):
            R = e["regs"]
            base = "nat_%s_%d" % (jf.stem, e["hit"])
            G.BASES[base] = e["snap"]
            pre = dict(D0=R["D0"], D1=R["D1"], D2=R["D2"])
            cases[base].append(G.Case(base, base, "4a7a", pre, lambda m: None,
                                      lambda m, R=R: O.call_4a7a(m, R["D0"], R["D1"], R["D2"])))
            cases[base].append((R, e.get("ret")))
    tot = ok = n = 0
    arms = collections.Counter()
    mut_fail = mut_n = 0
    fails = []
    for base, (c, (R, ret)) in cases.items():
        ram0, meta = G.run_base(base, [c])
        _, pk = meta[0]
        o, t, probs, tr = G.judge(c, ram0, pk)
        arm = next((x for x in tr if x.startswith("4a7a_")), "?")
        arms[arm] += 1
        tot += t; ok += o; n += 1
        print("%-34s ret=$%x D0=%d D1=%d %4d/%-4d %s %s" % (base, ret or 0, R["D0"] & 0xffff, R["D1"] & 0xffff, o, t,
                                                         "ok" if not probs else "FAIL", ARM.get(arm, arm)))
        for p in probs:
            print("      ", p)
        if probs:
            fails.append(base)
        if arm == "4a7a_A4":
            cm = G.Case(c.name, base, "4a7a", c.presets, lambda m: None, lambda m, R=R: mutant(m, R["D0"], R["D1"], R["D2"]))
            mo, mt, mprobs, _ = G.judge(cm, ram0, pk)
            mut_n += 1
            mut_fail += bool(mprobs)
    print("\nBYTES %d/%d over %d natural states; FAILED %s" % (ok, tot, n, fails))
    print("arms:", {ARM.get(k, k): v for k, v in arms.items()})
    print("mutant (animal class $a): fails %d of %d animal-arm states" % (mut_fail, mut_n))


if __name__ == "__main__":
    main()
