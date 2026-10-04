from reach import *
# for each B-only root (an instruction address not in A that is a literal target), list literal locations
onlyB = B - A
import collections
locs = collections.defaultdict(list)
for lo in range(0xc470, 0x1f274):
    v = struct.unpack(">I", bytes(mem[lo:lo+4]))[0]
    if v in onlyB and v in roots: locs[v].append(lo)
# only report roots that are the START of a B-only walk, i.e. not reachable from other onlyB targets
for v in sorted(locs):
    print("%06x <- literal at %s" % (v, " ".join("%06x"%x for x in locs[v][:6])))
