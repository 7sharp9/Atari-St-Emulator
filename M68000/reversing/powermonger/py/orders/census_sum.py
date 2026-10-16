"""census_sum.py [dir]: totals of census.sh's hits files (default ${PM_WORK:-scratchpad/pm162}/g4a7a/census/*.txt).
A run with 0 hits of $6522 (the commander tick) is post-game RAM and is listed and left out of the totals."""
import collections
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ["M68000_ROOT"]) if os.environ.get("M68000_ROOT") else next(
    p for p in HERE.parents if (p / "tools" / "rdis.py").exists())
D = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / os.environ.get("PM_WORK", "scratchpad/pm162") / "g4a7a" / "census"
NAME = {"4a7a": "$4a7a calls", "4a9a": "  non-empty cell", "4b62": "  -> 2 foreign settlement", "4b12": "  -> 6 foreign man",
        "4b30": "  -> 8 animal 8/$14/$16", "4b46": "  no man/animal", "4b4e": "  -> $c category 4", "4b96": "  commit",
        "4de2": "$4de2 calls", "4df2": "  2 lord", "4e62": "  6 lone man away", "4e9e": "  4 group", "4eb6": "  8 category 8",
        "4eca": "  $a category $14/$16", "4ed8": "  $c category 4", "4ee0": "  0 other", "4bc8": "$4bc8", "1519e": "  from $1519e",
        "6c32": "$6c32", "6522": "$6522 ticks"}
tot = collections.Counter()
live = frozen = 0
steps = 0
for f in sorted(D.glob("*.txt")):
    t = f.read_text(errors="replace")
    c = {a.lstrip("0"): int(n) for a, n in re.findall(r"^\s+\$([0-9a-f]{6})\s+(\d+)", t, re.M)}
    st = re.search(r"hits over (\d+) step", t)
    if not c.get("6522"):
        frozen += 1
        print("frozen (no $6522):", f.stem)
        continue
    live += 1
    steps += int(st.group(1)) if st else 0
    tot.update(c)
    if c.get("4eca") or c.get("4b12") or c.get("4b4e") or c.get("4b30"):
        print("%-16s" % f.stem, " ".join("%s=%d" % (k, c.get(k, 0)) for k in ("4a7a", "4b30", "4b12", "4b4e", "4eca", "4eb6")))
print("\n%d live runs, %d frozen, %.2fG live steps" % (live, frozen, steps / 1e9))
for k, v in NAME.items():
    print("%-30s %d" % (v, tot.get(k, 0)))
