"""group_states.py <snap>...: group state (+0), men (-24), owner (-48) of every group of every side ($51538 + side*$13c + $4c + 2k, k 0..5), live ones only,
and a tally of the states. strategy.md "What each order does": state 3 get men, 4 / 8 march, 6 idle, 9 support."""
import struct
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
from pm_export import ram_from_snap

tally = Counter()
for p in sys.argv[1:]:
    R = ram_from_snap(Path(p))
    w = lambda a: struct.unpack(">H", R[a:a + 2])[0]
    sw = lambda a: struct.unpack(">h", R[a:a + 2])[0]
    row = []
    for side in range(1, 6):
        for k in range(6):
            A = 0x51538 + side * 0x13c + 0x4c + 2 * k
            if sw(A - 48) <= 0 or not 0 < w(A - 24) < 400 or w(A) > 15:
                continue
            tally[w(A)] += 1
            row.append(f"s{side}g{k}:state{w(A)}/men{w(A - 24)}")
    print(Path(p).name, " ".join(row))
print("state tally (live groups, all snapshots):", dict(sorted(tally.items())))
