"""137th: are the four {r7, r7+3, r7+6, r7+9} slots of each prop-sheet family distinct art?
Reads the 27-frame prop sheet at $37c7c (480 B/frame) from a snapshot where world-build has run."""
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from pm_export import ram_from_snap

snap = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "scratchpad/pm121/run/k5_s4.snap")
ram = ram_from_snap(snap)
SHEET, N, STRIDE = 0x37c7c, 27, 480
frames = [ram[SHEET + i * STRIDE: SHEET + (i + 1) * STRIDE] for i in range(N)]
print("snap", snap.name, "nonzero frames", sum(any(f) for f in frames), "of", N)
dup_fams = 0
for r7 in range(12):  # r7 = 0..11 gives r7+9 <= 20; r7=12 reaches 21
    fam = [r7 + 3 * k for k in range(4)]
    fam = [f for f in fam if f < N]
    hs = [hashlib.md5(frames[f]).hexdigest()[:8] for f in fam]
    distinct = len(set(hs))
    if distinct < len(fam):
        dup_fams += 1
    print(f"r7={r7:2d} slots={fam} distinct={distinct}/{len(fam)} {hs}")
print("families with a repeated slot:", dup_fams)
