"""trans.py <type hex> <probe.txt>...: state transition counts (from -> to) of a pool A type over the logs (consecutive-frame state changes of one record)."""
import sys, collections
ty = int(sys.argv[1], 16)
c = collections.Counter()
for path in sys.argv[2:]:
    prev = {}
    for line in open(path):
        p = line.split()
        if p[0] != "A": continue
        f, slot, b = int(p[1]), int(p[2]), bytes.fromhex(p[3])
        if b[2] != ty: continue
        k = prev.get(slot)
        if k and k[0] == f - 1 and k[1] != b[3]: c[(k[1], b[3])] += 1
        prev[slot] = (f, b[3])
by = collections.defaultdict(list)
for (a, b), n in sorted(c.items()): by[a].append((b, n))
for a in sorted(by): print(f"  from {a:x}: " + ", ".join(f"->{b:x} x{n}" for b, n in by[a]))
