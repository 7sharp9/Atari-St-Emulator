"""List callers of a spawn helper with the D6/D7 immediates seen in the 6 preceding instructions.
usage: callers.py <helperhex> [pool]"""
import re, sys, os
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
lines = open(os.path.join(root, "scratchpad/crudebuster/all_lin.txt")).read().split("\n")
tgt = sys.argv[1].lower()
for i, l in enumerate(lines):
    if re.search(r"(jsr|bsr)\s+\$?0*%s(\.l|\.w)?\b" % tgt, l) or ("== $%s" % tgt) in l and ("jsr" in l or "bsr" in l):
        ctx = lines[max(0, i-8):i]
        d6 = d7 = None
        for c in ctx:
            m = re.search(r"(?:moveq|move\.w|move\.b|move\.l) #\$?(-?[0-9a-f]+),D6\b", c)
            if m: d6 = c.split(":")[0].strip() + " " + c.split(None,1)[1].strip()
            m = re.search(r"(?:moveq|move\.w|move\.b|move\.l) #\$?(-?[0-9a-f]+),D7\b", c)
            if m: d7 = c.split(None,1)[1].strip()
        print(l.split(":")[0].strip(), "|", d6, "|", d7)
