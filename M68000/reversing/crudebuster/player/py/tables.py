"""tables.py: print the player-side ROM tables used by the combat/score engine (cbuster set, decrypted image)."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from romlib import *
def bcd(v): return int("%x" % v)
SCORE = [bcd(l(0x4016 + 4 * i)) for i in range(24)]            # $4016: BCD points, index 1..24 (index 0 = none)
print("score index table ($4016, index 1..24 -> points):", {i + 1: p for i, p in enumerate(SCORE)})
print()
print("points per pool A type: hit (non-lethal) / thrown (state 5) / kill (state 2 or 4)  [$24952, 4 bytes per type: three score indexes and a sound id]")
for t in range(0x50):
    r = [b(0x24952 + 4 * t + k) for k in range(4)]
    pts = [(SCORE[x - 1] if 1 <= x <= 24 else 0) for x in r[:3]]
    if any(pts): print("  type %02x: hit %6d thrown %6d kill %8d  sound %02x" % (t, pts[0], pts[1], pts[2], r[3]))
print()
print("enemy melee damage by attacker type (pool C hit-box record), health units = 4 x table: Normal / Easy / Hard / Hardest  [tables $fd2a $fcca $fd5a $fd8a chosen by (DSW$80054 & $c)]")
tabs = [l(0xfcba + 4 * i) for i in range(4)]       # index = (dsw & 0xc) / 4: 0 Normal, 1 Easy, 2 Hard, 3 Hardest
for t in range(0x2c):
    print("  C type %02x: %s" % (t, " / ".join("%3d" % ((4 * b(tabs[i] + t)) & 0xff) for i in range(4))), end="" if t % 2 == 0 else "\n")
print()
print("contact damage $f78e[type] (health units): ", " ".join("%02x:%d" % (t, b(0xf78e + t)) for t in range(0x50) if b(0xf78e + t) != 1))
print("pool B projectile damage $10122[type] (health units, != 1):", " ".join("%02x:%d" % (t, b(0x10122 + t)) for t in range(0x50) if b(0x10122 + t) != 1))
print("reaction code written to +23 by the pool C melee ($fdba), values != 80:", " ".join("%02x:%02x" % (t, b(0xfdba + t)) for t in range(0x2c) if b(0xfdba + t) != 0x80))
print("pickup carry flags written to +26 by pool B type ($e876) (80 heavy, c0 throwable, e0 weapon):", " ".join("%02x:%02x" % (t, b(0xe876 + t)) for t in range(0x54) if b(0xe876 + t)))
print("initial spare lives by inverted DSW bits 0-1 ($7738):", [b(0x7738 + i) for i in range(4)])
print("level timer start values ($12f8), BCD:", [hex(w(0x12f8 + 2 * i)) for i in range(8)])
