"""141st: which order `$6762` (the follow-up table `$67d0`) issues in natural runs.  From each pm121/run snapshot `bp 67b4` (the `jsr $67ee` that
issues the table's order: D0 = the entry's order type, A1 = the group) up to 10 times in 60M steps each; the group's previous state (`268(A1)`,
written by `$3728` as `move.w 0(A3),192(A3)` when the group goes back to camp) and the order type are tallied.

    cd M68000 && .venv/bin/python reversing/powermonger/py/cmdai/campaign_census.py
"""
import collections
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[4]))
WORK_REL = "scratchpad/pm141/agents/cmdai"          # data (corpus/, g/, gx/, gw/, census/): scratchpad, not committed
WORK = ROOT / WORK_REL


def one(sn):
    cmds = "".join("bp 67b4 60000000\nm 51538 1580\n" for _ in range(10)) + "q\n"
    p = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", str(sn), "repl", "--disk-a", "scratchpad/powermonger.st"],
                       input=cmds, capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE="1"))
    out = p.stdout + p.stderr
    res = []
    for blk in re.split(r"(?=--- breakpoint)", out)[1:]:
        if not blk.startswith("--- breakpoint $000067b4"):
            continue
        regs = {k: int(v, 16) for k, v in re.findall(r"\b([DA][0-7]):([0-9a-f]{8})", blk)}
        hexs = "".join(re.findall(r"^((?:[0-9a-f]{2} ?)+)$", blk, flags=re.M)).replace(" ", "")
        a1 = regs["A1"] - 0x51538
        seg = hexs[2 * (a1 + 268):2 * (a1 + 270)]
        prev = int(seg, 16) if len(seg) == 4 else None
        res.append((sn.name, regs["D0"] & 0xffff, prev, regs["D7"] & 0xffff))
    return res


if __name__ == "__main__":
    snaps = [ROOT / "scratchpad/pm121/run" / f"{n}.snap" for n in ("k0_s1", "k25_s4", "k25_s2", "k0_s2")]
    tally = collections.Counter()
    with ThreadPoolExecutor(4) as ex:
        for res in ex.map(one, snaps):
            for name, d0, prev, d7 in res:
                tally[(prev, d0)] += 1
    print("(previous state 268(A1), order type issued by $6762):", {(hex(k[0]) if k[0] is not None else None, hex(k[1])): v for k, v in sorted(tally.items(), key=str)},
          "total", sum(tally.values()))
