"""hof_match.py [snap]: compare the hall-of-fame page ($25e44 -> table loop $25ed8..$25f00) with the table in RAM.
Reads the ten 28-byte entries at $25ccc (long score, 24-byte name) from the snapshot, renders score (right-aligned at x=$3c via the $24a92
rule) and name (from x=$87) with the font $e9fa at y = $50 + 9*row, and checks that the pixels of the live screen
equal that mask (any single colour) in each row's band. Default snapshot: $VIRUS_WORK/frontend/gate/hof.snap (made by gameover_seq.py)."""
import os, sys
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, d)
from fcommon import ROOT, OUT
sys.path.insert(0, os.path.join(ROOT, "tools"))
import numpy as np
from hud_match import screen_idx, render, field_x, number_text
snap = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, "gate", "hof.snap")
img, ram = screen_idx(snap)
ok = 0
for i in range(10):
    e = 0x25ccc + 28 * i
    score = int.from_bytes(ram[e:e+4], "big", signed=True)
    name = ram[e+4:e+28].split(b"\0")[0].decode("latin1")
    y = 0x50 + 9 * i
    txt = number_text(score)
    exp = render(ram, txt, field_x(ram, txt, 0x3c), y) | render(ram, name, 0x87, y)
    band = slice(y, y + 8)
    got = img[band, 0:320]
    cols = set(np.unique(got[exp[band, 0:320]]))
    bg_rows = got[~exp[band, 0:320]]
    # pixels of the expected text must be one colour; the same colour must not occur elsewhere in the band right of x=48 (background is a picture)
    c = list(cols)[0] if len(cols) == 1 else None
    extra = int(((got == c) & ~exp[band, 0:320])[:, 40:].sum()) if c is not None else -1
    good = c is not None and extra == 0
    ok += good
    print(f"row {i}: score {score:>6} name {name!r:28} text colour {c} stray pixels of that colour in band: {extra} -> {'MATCH' if good else 'DIFF'}")
print(f"{ok}/10 rows match")
