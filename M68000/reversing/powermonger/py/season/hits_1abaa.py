"""Branch coverage of a `$1abaa` corpus arm by `hits`, from the arm's own start snapshot and pokes.

Runs `hits <budget> <addrs>` from the arm's snapshot with the same `--pre` pokes capture_1abaa.py used
(index.json), budget = the step of the arm's last captured call + 60,000 (that call's body), interrupts
live (the wrap call's `$1ae40` wait is cleared by the sample interrupt, so no `$2c993` poke).  Prints
each address with its count next to the count the model predicts from the gate's branch census of the
same arm, so the corpus is shown to have run each branch.  `hits` can count one more than ran when an
interrupt is taken at the counted address (the entry `$1abaa` shows this as re-entry captures).

    cd M68000 && uv run python <this> <arm>
Output: $PM_WORK/corpus/<arm>/hits.{cmds,txt}
"""
import collections
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from capture_1abaa import ROOT, WORK  # noqa: E402
import gate_1abaa as G  # noqa: E402

ADDRS = [
    (0x1abaa, "entry", "calls"),
    (0x1abbe, "entry gate rts (dead)", "gate_return"),
    (0x1abc0, "body", "calls"),
    (0x1ac0a, "pixel copy (x>>4 < $120)", "pix_copy"),
    (0x1ac3c, "LCG wrap", "wrap"),
    (0x1ac92, "tree record test", "tree_pick"),
    (0x1ac9a, "felled tree regrows", "tree_regrow"),
    (0x1acc8, "sound 1 (id 0)", "wrap"),
    (0x1acec, "sound 2 (id season/2+1)", "wrap"),
    (0x1ad06, "sound 3 (id 0)", "wrap"),
    (0x1ad20, "sound 4 (id $a)", "wrap"),
    (0x1ad2a, "weather entry", "calls"),
    (0x1ad3a, "overlay draw call", "draws"),
    (0x1a886, "rain row", "rain_rows"),
    (0x1a9a4, "snow row", "snow_rows"),
    (0x1ad4a, "spell end", "spell_end"),
    (0x1ad74, "start test ($a0 bits set)", "start_test"),
    (0x1ad8c, "spell started", "spell_start"),
]


def main():
    arm = sys.argv[1]
    d = WORK / "corpus" / arm
    idx = json.load(open(ROOT / d / "index.json"))
    budget = idx["calls"][-1]["step"] + 60_000
    cmds = ["disk scratchpad/powermonger.st", *idx["pre"],
            f"hits {budget} " + " ".join(f"{a:x}" for a, _, _ in ADDRS), "q"]
    (ROOT / d / "hits.cmds").write_text("\n".join(cmds) + "\n")
    env = dict(os.environ, ATARI_NOTRACE="1")
    p = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", idx["snap"], "repl"],
                       input="\n".join(cmds) + "\n", capture_output=True, text=True, cwd=ROOT, env=env)
    log = p.stdout + p.stderr
    (ROOT / d / "hits.txt").write_text(log)
    got = {}
    for a, _, _ in ADDRS:
        m = re.search(rf"\$0*{a:x}\b\D*?(\d+)", log, re.I)
        got[a] = int(m.group(1)) if m else None
    # the model's prediction over the distinct calls
    brs, prev, n = collections.Counter(), 0, 0
    for e in idx["calls"]:
        dup = e["step"] - prev < G.REENTRY
        prev = e["step"]
        if dup:
            continue
        n += 1
        brs.update(G.gate_call(d, e)[4])
    brs["calls"] = n
    brs["draws"] = brs["rain_draw"] + brs["snow_draw"]
    brs["rain_rows"] = 0xc2 * brs["rain_draw"]
    brs["snow_rows"] = 0xc2 * brs["snow_draw"]
    print(f"{arm}: hits over {budget} steps from {idx['snap']} ({len(idx['pre'])} pokes)")
    for a, what, key in ADDRS:
        print(f"  ${a:05x}  {what:28s} hits {got[a]!s:>7}  model {brs[key]:>7}")


if __name__ == "__main__":
    main()
