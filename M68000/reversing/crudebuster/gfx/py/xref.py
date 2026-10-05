"""Callers of a 68000 address in the linear listing of the program ROM (scratchpad/crudebuster/all_lin.txt, one instruction per line).
usage: xref.py <hex addr> ...   -> callers (bsr/jsr/jmp/bra/bcc to it) and instructions naming it as an operand."""
import os, re, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "..", "scratchpad", "crudebuster"))
LIST = os.path.join(ROOT, "all_lin.txt")
rows = [l.rstrip("\n") for l in open(LIST)]
for a in sys.argv[1:]:
    a = a.lower().lstrip("$")
    pat = re.compile(r"(?:\$|== \$)0*%s\b" % a)
    hits = []
    for l in rows:
        m = re.match(r"\s+\$([0-9a-f]+): (\S+)\s*(.*)", l)
        if not m: continue
        if pat.search(m.group(3)):
            hits.append("%s %s %s" % (m.group(1), m.group(2), m.group(3)))
    print("== $%s: %d refs" % (a, len(hits)))
    for h in hits[:400]: print("  ", h)
