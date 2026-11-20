"""hud_icons.py: prove the lives and rockets icon rows ($248a2) by differential rendering.
Vary one of lives/rockets (the other fixed), same snapshot, same budget, same score/wave/best; diff the HUD strip
(rows 0..16, x 64..319) between consecutive counts. Prediction from $248a2..$24904: the nth lives ship (n = 1.. min(lives-1,7))
is drawn at x = $ac - 8*(n-1), the nth rocket (n = 1..min(rockets,8)) at x = $d6 - 8*(n-1), y = 3.
Usage: hud_icons.py [snap]. Output: per count the bbox of changed columns versus the previous count, and the prediction."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fcommon import G_GAME2
import numpy as np
from hud_match import screen_idx, trial   # noqa  (hud_match runs main on import: see guard below)

snap = sys.argv[1] if len(sys.argv) > 1 else G_GAME2
def strip(L, R, tag):
    p, out = trial(snap, 500, 0, 0, L, R, tag)
    img, ram = screen_idx(p)
    return img[0:16, 64:320].copy()
def bbox(a, b):
    cols = np.where((a != b).any(axis=0))[0]
    return (int(cols.min()) + 64, int(cols.max()) + 64) if len(cols) else None
print("lives (rockets 3):")
prev = strip(1, 3, "l01")
for L in range(2, 10):
    cur = strip(L, 3, f"l{L:02d}"); n = min(L - 1, 7)
    print(f"  lives {L}: ships {n}, changed columns vs lives {L-1}: {bbox(prev, cur)}; predicted slot x={0xac - 8*(n-1)} for ship {n}" if L - 1 <= 7 else f"  lives {L}: changed columns {bbox(prev, cur)} (cap 7 ships)")
    prev = cur
print("rockets (lives 3):")
prev = strip(3, 1, "r01")
for R in range(2, 11):
    cur = strip(3, R, f"r{R:02d}"); n = min(R, 8)
    print(f"  rockets {R}: icons {n}, changed columns vs rockets {R-1}: {bbox(prev, cur)}; predicted slot x={0xd6 - 8*(n-1)}" if R - 1 < 8 else f"  rockets {R}: changed columns {bbox(prev, cur)} (cap 8)")
    prev = cur
