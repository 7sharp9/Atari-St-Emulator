"""firstframe.py <probe.txt> <type hex> <state hex> [n]: the first n frames in which a record of the type is in the state, with a frame in the middle of the first run."""
import sys
path, ty, st = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16)
runs = []; last = None
for line in open(path):
    p = line.split()
    if p[0] != "A": continue
    b = bytes.fromhex(p[3])
    if b[2] == ty and b[3] == st:
        f = int(p[1])
        if last is not None and f == last[1] + 1: last[1] = f
        else: last = [f, f]; runs.append(last)
print([tuple(r) for r in runs[:int(sys.argv[4]) if len(sys.argv) > 4 else 3]])
