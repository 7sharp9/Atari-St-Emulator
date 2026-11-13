"""Clipboard key text as $12d4e computes it (inferred from the listing): two LCG steps of (word + base number 32(A6))."""
import sys
import os as _os
_M = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '../../../..'))  # M68000/
sys.path.insert(0, _M + '/reversing/captive/py/mapgen/full')
import lockcensus as LC
def shown(word, d0):
    x = (word + d0) & 0xffff
    for _ in range(2):
        x = (x * 0x5e5 + 0x29) & 0xffff
    return x
if __name__ == '__main__':
    d0, d2 = int(sys.argv[1]), int(sys.argv[2])
    locks, m, ab, full = LC.record_locks(d0, d2)
    for i, L in enumerate(locks):
        if L['K']:
            print(i, 'code', L['code'], 'shown', f"{shown(L['code'], d0):05d}", 'key kind', L['key'], 'K', L['K'], 'D', L['D'])
