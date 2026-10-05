"""d7callers.py <helperhex...>: every call with the immediate loaded into D7 within the 4 preceding instructions."""
import re, sys, os
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
lines = open(os.path.join(root, "scratchpad/crudebuster/all_lin.txt")).read().split("\n")
for tgt in sys.argv[1:]:
    print("== calls to", tgt)
    for i, l in enumerate(lines):
        m = re.match(r"\s+\$([0-9a-f]+):\s+(jsr|bsr)\s+(\$?[0-9a-f]+)(\.[lw])?", l)
        t = None
        if m:
            t = m.group(3).lstrip("$").lstrip("0")
            mm = re.search(r"== \$([0-9a-f]+)", l)
            if mm: t = mm.group(1).lstrip("0")
        if t == tgt.lstrip("0"):
            d7 = None
            for c in lines[max(0, i-4):i]:
                mm = re.search(r"(?:moveq|move\.[wbl]) #(\$?-?[0-9a-f]+),D7\b", c)
                if mm: d7 = mm.group(1)
            print(m.group(1), d7)
