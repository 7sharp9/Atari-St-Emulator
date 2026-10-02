"""141st: the tail `$6e6e` of the executor's handlers: `jsr $17a46` and the word counter at `$12abe` happen only when the order's commander (byte 0 of the
slot) is the local side (`$57ffe`).  Slot 3 / slot 1 get the order `$0a` (a handler that returns quietly); `hits` counts `$6e6e`, `$6e7e` (the local branch)
and `$17a46` over 600000 steps, for the commander being the local side and not.

    cd M68000 && .venv/bin/python reversing/powermonger/py/cmdai/tail_check.py
"""
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[4]))
WORK_REL = "scratchpad/pm141/agents/cmdai"          # data (corpus/, g/, gx/, gw/, census/): scratchpad, not committed
WORK = ROOT / WORK_REL
sys.path.insert(0, str(ROOT / "tools"))
import pm_fsm_ref as P
from pm_fsm_diff import Harness

BASE = Path(WORK_REL) / "corpus" / "k5_8.snap"
ram0 = (ROOT / BASE).with_suffix(".ram").read_bytes()
print("local side word $57ffe =", P.Mem(ram0).wu(0x57ffe))
for side in (1, 3):
    m = P.Mem(ram0)
    a = 0x58016 + 6 * side
    m.wb(a + 1, 0xa)
    m.wb(a + 4, 2)
    m.ww(0x51538 + side * 0x13c + 0x4c + 48, 0)
    pokes = Harness.bytepokes(ram0, {x: m.r[x] for x in range(len(ram0)) if m.r[x] != ram0[x]})
    base_pokes = []
    for tag, pk in (("order $0a", pokes), ("no order", base_pokes)):
        cmds = "".join(f"w {x:x} {w:08x}\n" for x, w in pk) + "hits 600000 6e6e 6e7e 17a46 6b38\nq\n"
        p = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", str(BASE), "repl", "--disk-a", "scratchpad/powermonger.st"],
                           input=cmds, capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE="1"))
        cnt = {a_: int(n) for a_, n in re.findall(r"\$0*([0-9a-f]+)\s+(\d+)\s+first", p.stdout + p.stderr)}
        print(f"commander side {side} {tag:9s}: $6b38 {cnt.get('6b38')} $6e6e {cnt.get('6e6e')} $6e7e {cnt.get('6e7e')} $17a46 {cnt.get('17a46')}")
