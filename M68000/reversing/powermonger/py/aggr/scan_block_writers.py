"""scan_block_writers.py [listing]: routines that write through an auto-increment/decrement address register that was loaded (within 30 instructions
before) with a constant base in [$3f000, $51b66): candidates for a block clear/copy that covers the group table $51538..$51b64 without naming it.
The end bound is not tracked here; read each hit (the one that mattered: `_clear_a` $10768, `clr.l (A0)+` from $3f364 to $57ff8)."""
import os, re, subprocess, sys
from pathlib import Path
ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[4]))
WORK = (ROOT / os.environ.get("PM_WORK", "scratchpad/pmwork")) / "aggr"
SNAP = ROOT / "scratchpad" / "pm123" / "win" / "m1_ready.snap"


def listing(arg=None):
    """The whole-image listing: the argument if given, else $PM_WORK/aggr/pm_all.asm, regenerated (about a second) from m1_ready.snap when missing.
    The text segment ends at $1c488 (`_set_ser` $1c3e6 and its table); the listing runs to $1c600."""
    if arg:
        return arg
    out = WORK / "pm_all.asm"
    if not out.exists():
        WORK.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            subprocess.run([sys.executable, str(ROOT / "tools" / "disassemble.py"), "--snap", str(SNAP), "--all", "1000", "1c600"], stdout=f, check=True, cwd=ROOT)
    return str(out)
LST = listing(sys.argv[1] if len(sys.argv) > 1 else None)
ins = []
for line in open(LST):
    m = re.match(r"\s+\$([0-9a-f]+): (.*)$", line)
    if m: ins.append((int(m.group(1), 16), m.group(2).strip()))
LO, HI = 0x3f000, 0x51b66
for i, (a, t) in enumerate(ins):
    m = re.search(r"\((A[0-7])\)\+|-\((A[0-7])\)", t)
    if not m or t.startswith(("lea", "movem.l (A7)")): continue
    reg = m.group(1) or m.group(2)
    if reg == "A7": continue
    for j in range(i - 1, max(0, i - 30), -1):
        b = ins[j][1]
        mm = re.match(r"(lea|movea\.l|move\.l) #?\$([0-9a-f]+)(\.l)?,%s$" % reg, b)
        if mm:
            v = int(mm.group(2), 16)
            if LO <= v < HI: print("$%06x %-28s base $%x loaded at $%06x (%s)" % (a, t, v, ins[j][0], b))
            break
        if re.search(r",%s$" % reg, b) and not b.startswith("cmp"): break
