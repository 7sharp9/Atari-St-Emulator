"""arm_pokes.py: the three arms of `$65b4` that no natural run reaches (`$66a4` food fallback, `$664c`/`$668c` transfer, `$6884` refusal), driven live.

Start snapshot `scratchpad/pm143/run/p0k0_s1.snap` (a Play Random Land run; `PAGES0=1 build_land.sh 0` then `runland.sh`).  Each experiment is REPL pokes
followed by `hits` on the real 68000; the control has no pokes.  Group records are at `$51538 + side * $13c`, the word fields interleaved with
stride 2 (field F of group D7 is `base + F + D7`).

    food      side 4 group 1 (D7 2, state 6 at its decision, the attack of 17.7M steps in): `bp 661a` then food (`112(A1)`) := 0
              expect `$66a4`, `$66b0`, `$67ee`, `$6822` instead of the control's `$6638` (attack)
    xfer      side 3 group 2 (D7 4): state `76(A1)` := 9 (decided every tick), men `52(A1)` := 3, home troops (word 8) of every side 3 lord := 0
              expect `$661a`, `$664c`, `$6680`, `$668c`, `$6822` with the slot left holding order `$22`, parameter 4 (the pending-record route)
    getmen    the same without zeroing the lords: `$65c8` (arm 1), not `$668c`

    cd M68000 && .venv/bin/python reversing/powermonger/py/cmdai/arm_pokes.py
"""
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(ROOT / "tools"))
from disassemble import ram_from_snap  # noqa: E402

SNAP = "scratchpad/pm143/run/p0k0_s1.snap"
DISK = "scratchpad/powermonger.st"
ADDRS = "6522 65b4 65c8 661a 6638 664c 6680 66a4 66b0 668c 6884 6822 67ee"
FOOD = 0x51538 + 4 * 0x13c + 2 + 112        # side 4, D7 2
STATE3 = 0x51538 + 3 * 0x13c + 4 + 76       # side 3, D7 4
MEN3 = 0x51538 + 3 * 0x13c + 4 + 52


def repl(cmds):
    argv = ["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", SNAP, "repl", "--disk-a", DISK]
    p = subprocess.run(argv, input="".join(c + "\n" for c in cmds) + "q\n", capture_output=True, text=True, cwd=ROOT, timeout=900,
                       env=dict(os.environ, ATARI_NOTRACE="1"))
    return p.stdout + p.stderr


def counts(out):
    return {a: int(n) for a, n in re.findall(r"\$00([0-9a-f]{4})\s+(\d+)\s+first", out)}


def lord_pokes(side):
    r = ram_from_snap(ROOT / SNAP)
    return ["w %x 0000%04x" % (a + 8, int.from_bytes(r[a + 10:a + 12], "big")) for a in range(0x4e514, 0x4f914, 32) if r[a] == side]


def show(name, hits, want):
    got = {a: hits.get(a, 0) for a in want}
    print("%-9s %s  %s" % (name, " ".join("$%s %d" % (a, n) for a, n in sorted(hits.items()) if n), "ok" if all((n > 0) == w for (a, n), w in zip(got.items(), want.values())) else "UNEXPECTED"))


if __name__ == "__main__":
    # food: run to the decision of that group, poke, count
    for name, poke in (("food-ctl", "m %x 2" % FOOD), ("food", "w %x 00000000" % FOOD)):
        out = repl(["bp 661a 20000000", poke, "hits 20000 " + ADDRS])
        show(name, counts(out), {"6638": name == "food-ctl", "66a4": name == "food", "66b0": name == "food", "6822": True, "6884": False})
    base = ["w %x 00090000" % STATE3, "w %x 00030000" % MEN3]
    out = repl(base + ["hits 200000 " + ADDRS])
    show("getmen", counts(out), {"65c8": True, "668c": False, "6884": False})
    out = repl(lord_pokes(3) + base + ["hits 200000 " + ADDRS, "m 58016 30"])
    show("xfer", counts(out), {"664c": True, "6680": True, "668c": True, "6822": True, "6884": False, "65c8": False})
