"""Census of keys placed on their own door cell (K == D) over chained bases, with the clipboard number the game
shows (shown.shown, gated 301/301 against $12d4e). D2 = 0 for the ten target bases of each mission (D0 = 11m + t,
t = 0..9) and D2 = 1 for the station base (t = 10).
Usage: keyondoor.py <first mission index> <last mission index exclusive>"""
import sys
import os as _os
_M = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '../../../..'))  # M68000/
sys.path.insert(0, _M + '/reversing/captive/py/mapgen/full')
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import lockcensus as LC
from shown import shown
from collections import Counter
lo, hi = int(sys.argv[1]), int(sys.argv[2])
c = Counter()
for mi in range(lo, hi):
    for t in range(11):
        d0, d2 = 11 * mi + t, (1 if t == 10 else 0)
        locks, m, ab, full = LC.record_locks(d0, d2)
        c['bases'] += 1
        hit = False
        for i, L in enumerate(locks):
            c['locks'] += 1
            if L['K'] is None:
                continue
            c['keys'] += 1
            c[f'keys kind {L["key"]}'] += 1
            if L['K'] == L['D']:
                c['key on its own door'] += 1
                c[f'key on its own door, key kind {L["key"]} door kind {L["door"]}'] += 1
                hit = True
                print(f'mission {mi+1} target {t+1} D0={d0} D2={d2} lock {i} door {L["D"]} door kind {L["door"]} key kind {L["key"]} code {L["code"]} shown {shown(L["code"], d0):05d}')
        c['bases with one'] += hit
for k, v in c.items():
    print(f'{k}: {v}')
