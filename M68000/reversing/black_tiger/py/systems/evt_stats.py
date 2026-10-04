"""Per-address call / trap / interrupt census over an ATARI_TRACE_EVENTS log.
usage: evt_stats.py file.evt [topN]   (BT_WORK / M68000_ROOT not needed: reads only the log)
"""
import os, sys, struct
from collections import Counter
HEADER = struct.Struct("<4sBBHQ"); REC = struct.Struct("<QIIHBB")
def load(path):
    d = open(path, "rb").read()
    m, v, rl, _, start = HEADER.unpack_from(d, 0)
    assert m == b"A68E" and rl == REC.size
    off = HEADER.size
    n = (len(d) - off) // REC.size
    return start, [REC.unpack_from(d, off + i * REC.size) for i in range(n)]
if __name__ == "__main__":
    start, recs = load(sys.argv[1]); top = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    calls = Counter(); ints = Counter(); traps = Counter(); intsteps = {}
    for sc, pc, tgt, op, kind, fl in recs:
        if kind == 3: calls[tgt] += 1
        elif kind == 6: ints[tgt] += 1; intsteps.setdefault(tgt, []).append(sc)
        elif kind == 5: traps[(op & 0xf, tgt)] += 1
    print("start step", start, "records", len(recs))
    print("INTERRUPT handler targets:")
    for t, c in ints.most_common():
        st = intsteps[t]; gaps = Counter(b - a for a, b in zip(st, st[1:]))
        print(f"  ${t:08x} x{c}  commonest gaps {gaps.most_common(3)}")
    print("TRAP (opcode low nibble, target):")
    for k, c in traps.most_common(): print(f"  trap#{k[0]} -> ${k[1]:08x} x{c}")
    print("CALL targets:")
    for t, c in calls.most_common(top): print(f"  ${t:08x} x{c}")
