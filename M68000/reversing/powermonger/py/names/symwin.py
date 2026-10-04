"""symwin.py lo hi: list both symbol files' entries in [lo, hi] (hex), the developers' names first."""
import sys, os
from pathlib import Path
R = Path(__file__).resolve().parents[2]   # reversing/powermonger
lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
for fn in ("powermonger_orig.sym", "powermonger.sym"):
    print("==", fn)
    for l in open(R / fn):
        if l.startswith("#") or not l.strip(): continue
        p = l.split("\t") if "\t" in l else l.split(None, 1)
        try: a = int(p[0], 16)
        except ValueError: continue
        if lo <= a <= hi: print("  %06x %s" % (a, (p[1] if len(p) > 1 else "").strip()[:150]))
