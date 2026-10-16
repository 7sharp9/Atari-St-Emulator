#!/usr/bin/env python3
"""census.py <snap>...: per snapshot, every lead (flag bit 4) of side 1, and the side-2 man objects in a fight
mode with how many of them pass $548a's gate against side 1's leads (bow, better weapon, health >= his, or retry 39 == 2)."""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1]))
from observe import load

O = 0x51b66
FIGHT = {0x2c, 0x2e, 0x30, 0x32, 0x34}


def sb(v):
    return v - 256 if v > 127 else v


def recs(R):
    for i in range(512):
        r = R[O + i * 50: O + i * 50 + 50]
        if r[6] == 0 and sb(r[5]) > 0:          # category 0: a man
            yield O + i * 50, r


def passes(A1, L):
    return A1[44] in (6, 0xe, 0x10) or sb(A1[44]) > sb(L[44]) or sb(A1[45]) >= sb(L[45]) or A1[39] == 2


for p in sys.argv[1:]:
    R = load(p)
    men = list(recs(R))
    leads = [(a, r) for a, r in men if sb(r[5]) == 1 and r[7] & 0x10]
    for a, L in leads:
        foes = [r for _, r in men if sb(r[5]) == 2 and (r[31] in FIGHT or r[30] in FIGHT)]
        n = len(foes); np_ = sum(passes(r, L) for r in foes)
        r2 = sum(r[39] == 2 for r in foes); hpge = sum(sb(r[45]) >= sb(L[45]) for r in foes)
        hp = sorted(sb(r[45]) for r in foes)
        print('%s lead $%05x mode %02x hp %d | side-2 fighters %d, pass %d (r39=2 %d, hp>=lead %d), hp median %s' % (
            p.split('/')[-2] + '/' + p.split('/')[-1], a, L[31], sb(L[45]), n, np_, r2, hpge, hp[n // 2] if n else '-'))
