"""Which routines are documented but no differential gate names? (the companion of `doc_coverage.py`)

`doc_coverage.py` asks whether a routine's address appears in a doc. This asks whether it appears in a *gate*: a script that diffs a
model against the real 68000 (`py/gate_*.py`, `py/diff_*.py`, `py/*/gate_*.py`, `py/*/*gate.py`, `tools/pm_*.py`, and the
scratchpad gates `pm98`/`pm99`/`pm113`/`pm115`). A routine whose address a gate cites is "gated" (the gate may call it, or model it
inline; the cite is the cheap test, read the gate before trusting it for one routine). A routine in a doc but in no gate is a code read
or a live observation only, which is the least-known code left once `doc_coverage.py` is near zero.

    cd M68000 && python reversing/powermonger/py/gate_coverage.py [--min 60] [--out ungated.txt] [--page]

Output: totals, ungated bytes per 4 KB page (`--page`), and the ungated routines by size. Data tables that the symbol file lists as text
(`arrows`, `cunt`, `modedat`, `corners`, ...) are dropped by name (`--skip`); `the_temp`, `scale_da`, `rfont`, `text` and `fileio` are data too and
still head the list. A cite is not an execution: a gate can run a routine through a mode table without naming it, so confirm with a `hits` census
before calling a routine unproven.

Before the commander-AI, order, world-build and `$15000` gates (`py/cmdai|orders|worldbuild|fsm15/`): 693 of 964 routines (56777 of 105180 bytes) named by
no gate; after: 657 routines, 49106 bytes (42630 of them in a doc). The cite undercounts: `$15c46` is run by the fsm15 gate through mode `$5a` and still lists
as ungated. What is left is data tables, the menu/disk/serial UI (`$b000..$d000`), the input and scroll page (`$13000`: `$1394c`, `$134f4`, `$133ba`,
`$1373c`), the click handlers (`$a46c..$a738`), the season code `$1abaa`, the conquest animation `$1a648` and the land-capture helpers `$10458`.
"""
import argparse
import collections
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PM = ROOT / "reversing" / "powermonger"
ap = argparse.ArgumentParser()
ap.add_argument("--min", type=int, default=60)
ap.add_argument("--out")
ap.add_argument("--page", action="store_true")
ap.add_argument("--skip", default="arrows,cunt,modedat,corners,forest_l,done_str,done2_st,wank,ymax,xmax,x0,y0,label6,not_pres")
a = ap.parse_args()
skip = set(a.skip.split(","))

gate_files = []
for pat in ("py/gate_*.py", "py/diff_*.py", "py/*/gate_*.py", "py/*/*gate*.py"):
    gate_files += list(PM.glob(pat))
gate_files += list((ROOT / "tools").glob("pm_*.py"))
for d in ("pm98", "pm99", "pm113", "pm115"):
    gate_files += list((ROOT / "scratchpad" / d).glob("*.py"))
gate_files = [p for p in gate_files if p.resolve() != Path(__file__).resolve()]
gates = "".join(p.read_text(errors="replace") for p in gate_files)
doc = "".join((PM / f).read_text() for f in ("README.md", "ai.md", "economy.md", "strategy.md", "graphics.md", "system.md"))

def addrs_in(text):
    return {int(x, 16) for x in re.findall(r"(?:\$|0x|\b)0*([0-9a-fA-F]{3,6})(?![0-9a-fA-F])", text)}

gated = addrs_in(gates)
documented = {int(x, 16) for x in re.findall(r"\$0*([0-9a-fA-F]{3,6})(?![0-9a-fA-F])", doc)}

starts = {}
for line in open(PM / "powermonger_orig.sym"):
    if line.startswith("#") or not line.strip():
        continue
    p = line.rstrip("\n").split("\t")
    if len(p) >= 3 and p[2].strip().endswith("T"):
        starts.setdefault(int(p[0], 16), p[1])
order = sorted(starts)
END = 0x1c48e
rows = []
for i, lo in enumerate(order):
    hi = order[i + 1] if i + 1 < len(order) else END
    rng = range(lo, hi, 2)
    rows.append((lo, hi - lo, starts[lo], any(t in gated for t in rng), any(t in documented for t in rng)))
code = [r for r in rows if r[2] not in skip]
ung = [r for r in code if not r[3]]
print(f"{len(gate_files)} gate files; routines {len(code)} bytes {sum(r[1] for r in code)}; gated {len(code) - len(ung)} routines, "
      f"ungated {len(ung)} routines {sum(r[1] for r in ung)} bytes (of which documented {sum(r[1] for r in ung if r[4])})")
if a.page:
    pages = collections.Counter()
    for r in ung:
        pages[r[0] >> 12] += r[1]
    print("ungated bytes per 4 KB page:", {hex(k << 12): v for k, v in sorted(pages.items())})
for r in sorted((r for r in ung if r[1] >= a.min), key=lambda r: -r[1])[:60]:
    print(f"  ${r[0]:06x} {r[1]:5d} {r[2]:10s} {'doc' if r[4] else 'NODOC'}")
if a.out:
    Path(a.out).write_text("\n".join(f"{r[0]:06x} {r[1]:5d} {r[2]} {'doc' if r[4] else 'nodoc'}" for r in sorted(ung)))
