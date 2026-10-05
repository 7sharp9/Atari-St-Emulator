"""fieldscan.py lo hi : for the linear listing lines with addresses in [lo,hi), count uses of each N(A6) offset, split read/write guess."""
import re, sys, os, collections
lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
lst = os.path.join(os.environ["M68000_ROOT"], "scratchpad/crudebuster/all_lin.txt")
pat = re.compile(r"\$([0-9a-f]+): (\S+) (.*)")
uses = collections.defaultdict(list)
for ln in open(lst):
    m = pat.match(ln.strip())
    if not m: continue
    a = int(m.group(1), 16)
    if not (lo <= a < hi): continue
    op, args = m.group(2), m.group(3)
    for mm in re.finditer(r"(\d+)\(A6\)", args):
        off = int(mm.group(1))
        parts = args.split(",")
        dst = len(parts) > 1 and mm.group(0) in parts[-1]
        uses[off].append((a, op, "W" if dst or op in ("clr.b","clr.w","clr.l","bset","bclr","bchg","addq.b","subq.b","addq.w","subq.w","addq.l") else "R"))
for off in sorted(uses):
    u = uses[off]
    print("%3d $%02x  n=%3d  W=%3d  e.g. %s" % (off, off, len(u), sum(1 for x in u if x[2] == "W"), " ".join("%x:%s" % (x[0], x[1]) for x in u[:4])))
