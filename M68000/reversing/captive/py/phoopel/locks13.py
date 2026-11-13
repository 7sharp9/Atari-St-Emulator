"""List $25722's locks for one base (lockcensus.record_locks on chain_run.generate) and coded-door list entries."""
import sys
import os as _os
_M = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '../../../..'))  # M68000/
sys.path.insert(0, _M + '/reversing/captive/py/mapgen/full')
import lockcensus as LC, chain_run as CR
d0 = int(sys.argv[1]); d2 = int(sys.argv[2])
want = int(sys.argv[3]) if len(sys.argv) > 3 else None
locks, m, ab, full = LC.record_locks(d0, d2)
g = LC.Grid(m)
ex = LC.w(m, 32); ent = (ex % 64, ex // 64)
print(f'D0={d0} D2={d2} entrance {ent} locks {len(locks)} abandoned {ab}')
for i, L in enumerate(locks):
    K = L['K']
    reach = g.reach(ent, {L['D']})
    flag = '  <==' if want is not None and L['code'] == want else ''
    print(f"{i:2d} code {L['code']:5d} (${L['code']:04x}) door kind {L['door']} key kind {L['key']} E{L['E']} D{L['D']} W{L['W']} K{K}"
          f" G0 D={g.g0(*L['D'])} K={g.g0(*K) if K else '-'} Kreach-without-D={K in reach if K else '-'}{flag}")
# coded door list at fed 13708 pointer
q = int.from_bytes(m[13708:13712], 'big') - CR.FED
print('coded-door list:', [(full[q+4*i], full[q+4*i+1], ((full[q+4*i+2]<<8)|full[q+4*i+3])>>4) for i in range(8)])
