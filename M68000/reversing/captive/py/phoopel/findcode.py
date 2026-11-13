"""Search chained bases for a lock code (lock list 13720 code word) over D0 ranges, D2 = 0 and 1."""
import sys
import os as _os
_M = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '../../../..'))  # M68000/
sys.path.insert(0, _M + '/reversing/captive/py/mapgen/full')
import lockcensus as LC
want = int(sys.argv[1]); lo, hi = int(sys.argv[2]), int(sys.argv[3])
d2s = [int(x) for x in sys.argv[4].split(',')] if len(sys.argv) > 4 else [0, 1]
import chain_run as CR
n = 0
for d2 in d2s:
    for d0 in range(lo, hi):
        locks, m, ab, full = LC.record_locks(d0, d2)
        n += 1
        # positive control on representation: lock-list code words equal recorded codes
        q = int.from_bytes(m[13720:13724], 'big') - CR.FED
        lst = [(full[q+10*i+2] << 8) | full[q+10*i+3] for i in range(LC.w(m, 13270))]
        assert lst == [L['code'] for L in locks], (d0, d2)
        for i, L in enumerate(locks):
            if L['code'] == want:
                print(f'HIT d0={d0} d2={d2} lock {i}: {L}')
print('bases searched', n)
