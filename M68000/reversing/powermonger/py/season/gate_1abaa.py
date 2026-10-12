"""Gate: `model_1abaa.call_1abaa` against the 68000's `callcap 1abaa` over every captured call.

For each call in $PM_WORK/corpus/<arm>/index.json (written by capture_1abaa.py): the pre-state is
cNNNN.ram.gz, the real post-state is that RAM with the callcap delta cNNNN.json applied, and the
model runs on a copy of the pre-state.  Compared: every byte either side changed, over the whole
1 MB RAM except the dead stack below the entry SP ([entrySP - $100, entrySP): pushed sound arguments,
`movem` saves, the sentinel return slot).  A byte one side changed and the other did not is a
mismatch.  A capture taken less than 1000 steps after the previous one is the same
call again (an interrupt taken at $1abaa returns there): it is gated (its pre-state differs by the ISR's
writes) but not counted as a distinct call.  Reports calls matched / total and bytes matched / total per arm, the model's branch
census per arm, and the sound events of every wrap call.

    cd M68000 && uv run python <this> [arm...]        (default: every arm under corpus/)
"""
import collections
import gzip
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model_1abaa as M  # noqa: E402
from capture_1abaa import ROOT, WORK  # noqa: E402

STACK_SPAN = 0x100
REENTRY = 1000   # an MFP level-6 interrupt taken at $1abaa returns to it ~20 steps later: bpc stops again


def gate_call(d, e):
    k = e["k"]
    pre = gzip.open(ROOT / d / f"c{k:04d}.ram.gz").read()
    j = json.load(open(ROOT / d / f"c{k:04d}.json"))
    assert j["outcome"] == "returned", (d, k, j["outcome"])
    sp = j["entrySP"]
    real = bytearray(pre)
    for a, x0, x1 in j["mem"]:
        real[a] = x1
    m = bytearray(pre)
    ev, br = M.call_1abaa(m)
    stack = lambda a: sp - STACK_SPAN <= a < sp  # noqa: E731
    addrs = {a for a, _, _ in j["mem"] if not stack(a)}
    pa, ma = np.frombuffer(pre, np.uint8), np.frombuffer(bytes(m), np.uint8)
    diff_model = set(np.nonzero(pa != ma)[0].tolist())
    nstack = sum(1 for a, _, _ in j["mem"] if stack(a))
    addrs |= {a for a in diff_model if not stack(a)}
    bad = sorted(a for a in addrs if m[a] != real[a])
    return len(addrs), len(addrs) - len(bad), bad, ev, br, nstack


def main():
    arms = sys.argv[1:] or sorted(p.name for p in (ROOT / WORK / "corpus").iterdir() if (p / "index.json").exists())
    tot_c = tot_ok = tot_b = tot_bok = 0
    for arm in arms:
        d = WORK / "corpus" / arm
        idx = json.load(open(ROOT / d / "index.json"))
        calls = idx["calls"]
        c_ok = b_tot = b_ok = st = 0
        brs = collections.Counter()
        fails = []
        prev, reent = 0, []
        for e in calls:
            dup = e["step"] - prev < REENTRY
            if dup:
                reent.append(e["k"])
            prev = e["step"]
            n, ok, bad, ev, br, nstack = gate_call(d, e)
            b_tot += n
            b_ok += ok
            st += nstack
            if not dup:
                brs.update(br)
            if not bad:
                c_ok += 1
            else:
                fails.append((e["k"], len(bad), [hex(a) for a in bad[:8]]))
            if br["wrap"]:
                print(f"  {arm} c{e['k']:04d} wrap (step {e['step']}, poke2c993={e['poke2c993']}): "
                      + "; ".join(f"${x['site']:x} id {x['id']} n {x['n']} seq "
                                  + (f"${x['seq']:x}" if x['seq'] is not None else "-") for x in ev))
        pre = idx["pre"] if len(idx["pre"]) < 4 else idx["pre"][:2] + [f"... {len(idx['pre'])} pokes"]
        print(f"{arm}: calls {c_ok}/{len(calls)}  bytes {b_ok}/{b_tot}  (stack bytes excluded {st})  pre {pre}")
        print(f"  {len(calls) - len(reent)} distinct calls; {len(reent)} capture(s) of the same call after an "
              f"interrupt re-entry at $1abaa (< {REENTRY} steps after the previous stop): {reent}")
        print(f"  model branches over the distinct calls: {dict(sorted(brs.items()))}")
        for f in fails[:10]:
            print(f"  MISMATCH c{f[0]:04d}: {f[1]} bytes, first {f[2]}")
        tot_c += len(calls)
        tot_ok += c_ok
        tot_b += b_tot
        tot_bok += b_ok
    print(f"TOTAL: calls {tot_ok}/{tot_c}  bytes {tot_bok}/{tot_b}")


if __name__ == "__main__":
    main()
