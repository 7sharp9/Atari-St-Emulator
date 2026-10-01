"""Which developer-named routines does no doc, script or port file mention by address?

A routine is a symbol start of `powermonger_orig.sym` (the developers' own text symbols, runtime addresses). It counts as
mentioned when any hex address inside it (even offsets) appears as `$xxxx` in `README.md`, `ai.md`, `economy.md`, `strategy.md`,
`graphics.md`, `port/**/*.md|*.fs`, `py/*.py`, `tools/pm_*.py` or the handoff. Output: totals, the unmentioned routines by size, and
the bytes per 4 KB page. Many large entries are data tables (the symbol table has no sizes and the text section holds data), so read the
first lines of a hit with `tools/disassemble.py --snap <snap> --all <lo> <hi>` before calling it code.

    cd M68000 && python reversing/powermonger/py/doc_coverage.py [--min 40] [--out unmentioned.txt]

139th pass: 29498 bytes (472 of 978 routines) were unmentioned before the world-build population, the shepherd modes and the animal and
pigeon loops were documented, 28632 (464) after; what is left is mostly data (`scale_da`, `arrows`, `text`, `modedat`, `eyes`) and the UI click
handlers (`$9000..$b000`), the map and road drawing (`$10000`), the sound code (`$1a000..$1c000`) and the serial link (`$ba74`).
"""
import argparse
import collections
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PM = ROOT / "reversing" / "powermonger"
ap = argparse.ArgumentParser()
ap.add_argument("--min", type=int, default=40)
ap.add_argument("--out")
a = ap.parse_args()

docs = ""
for f in ("README.md", "ai.md", "economy.md", "strategy.md", "graphics.md"):
    docs += (PM / f).read_text()
docs += (ROOT / "sessions/powermonger.md").read_text()
for pat in ("py/*.py", "port/**/*.md", "port/**/*.fs"):
    for p in PM.glob(pat):
        docs += p.read_text(errors="replace")
for p in (ROOT / "tools").glob("pm_*.py"):
    docs += p.read_text()
mentioned = {int(x, 16) for x in re.findall(r"\$0*([0-9a-fA-F]{3,6})(?![0-9a-fA-F])", docs)}

starts = {}
for line in open(PM / "powermonger_orig.sym"):
    if line.startswith("#") or not line.strip():
        continue
    p = line.rstrip("\n").split("\t")
    if len(p) >= 3 and p[2].strip().endswith("T"):
        starts.setdefault(int(p[0], 16), p[1])
addrs = sorted(starts)
END = 0x1c48e
rows = []
for i, lo in enumerate(addrs):
    hi = addrs[i + 1] if i + 1 < len(addrs) else END
    rows.append((lo, hi - lo, starts[lo], any(t in mentioned for t in range(lo, hi, 2))))
tot = sum(r[1] for r in rows)
und = [r for r in rows if not r[3]]
print(f"routines {len(rows)}, bytes {tot}; unmentioned routines {len(und)}, bytes {sum(r[1] for r in und)}")
pages = collections.Counter()
for r in und:
    pages[r[0] >> 12] += r[1]
print("unmentioned bytes per 4 KB page:", {hex(k << 12): v for k, v in sorted(pages.items())})
big = sorted((r for r in und if r[1] >= a.min), key=lambda r: -r[1])
for r in big[:40]:
    print(f"  ${r[0]:06x} {r[1]:5d} {r[2]}")
if a.out:
    Path(a.out).write_text("\n".join(f"{r[0]:06x} {r[1]:5d} {r[2]}" for r in sorted(und)))
