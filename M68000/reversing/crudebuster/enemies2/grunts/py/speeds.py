"""speeds.py <probe.txt>...: per (type, state) the horizontal and vertical step per frame (16.16 position longs at +8 and +12) between consecutive logged frames
of the same record in the same state (excluding the first frame of a state), as the most common values (value in pixels/frame, count)."""
import sys, collections
def s32(v): return v - (1 << 32) if v >= 1 << 31 else v
res = collections.defaultdict(collections.Counter)
resy = collections.defaultdict(collections.Counter)
for path in sys.argv[1:]:
    prev = {}
    for line in open(path):
        p = line.split()
        if p[0] != "A": continue
        f, slot, b = int(p[1]), int(p[2]), bytes.fromhex(p[3])
        k = prev.get(slot)
        x = int.from_bytes(b[8:12], "big"); y = int.from_bytes(b[12:16], "big")
        if k and k[0] == f - 1 and k[1][2] == b[2] and k[1][3] == b[3] and k[2] == b[3] and k[4] == b[4]:
            dx = s32((x - k[3][0]) & 0xffffffff); dy = s32((y - k[3][1]) & 0xffffffff)
            res[(b[2], b[3])][dx / 65536.0] += 1
            resy[(b[2], b[3])][dy / 65536.0] += 1
        prev[slot] = (f, b, b[3], (x, y), b[4])
for k in sorted(res):
    top = res[k].most_common(4); topy = resy[k].most_common(3)
    print(f"type {k[0]:02x} state {k[1]:02x}: dx/frame " + ", ".join(f"{v:+.3f}x{n}" for v, n in top) + "   dy/frame " + ", ".join(f"{v:+.3f}x{n}" for v, n in topy))
