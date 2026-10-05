"""writes.py <hits>: summarise the write-tap lines "<frame> W <addr> pc=<pc> val=<data> a6=<a6>" of a dm.lua run with DM_WPS on the state byte (+2) of the pool-4 records:
count per (writer PC, value written), the first frame, and whether any value written was 6 (state 6, $3ed30)."""
import sys, collections, re
c = collections.OrderedDict(); first = {}; six = 0
for l in open(sys.argv[1]):
    m = re.match(r'(\d+) W (\w+) pc=(\w+) val=(\w+)', l)
    if not m: continue
    f, a, pc, v = int(m.group(1)), m.group(2), int(m.group(3), 16), int(m.group(4), 16)
    k = (a, '%06x' % pc, v & 0xff, v)
    c[k] = c.get(k, 0) + 1; first.setdefault(k, f)
    if (v & 0xff) == 6 or (v >> 8) & 0xff == 6: six += 1
for k, n in c.items(): print('record+2 @%s pc=$%s val=%08x: %d writes, first at frame %d' % (k[0], k[1], k[3], n, first[k]))
print('writes: %d, with a 6 in either byte: %d' % (sum(c.values()), six))
