"""Hazard census: for one track, poke the race counter -1748(A4) to each value in a list and record which hazard systems
the game's own setup code ($a6c4 oil, $a8a0 cones, $b094 tornado, $b22a arrows) enabled.  usage: hazard_table.py T n [n ...]"""
import sys; sys.path.insert(0,'.')
from tkcommon import *
from hazard_probe import probe
T = int(sys.argv[1])
for n in map(int, sys.argv[2:]):
    st = probe(T, n, 2500000)
    print('T%d race=%-3d oil_n=%d types=%s cells(col,row)=%s | cones=%d cells=%s | tornado=%d | arrows=%d | gates=%d' % (
        T+1, n, st['oil_n'], st['oil_types'][:st['oil_n']], list(zip(st['oil_col'], st['oil_row']))[:st['oil_n']],
        st['obst_n'], list(zip(st['obst_col'], st['obst_row']))[:st['obst_n']], st['roam'], st['arrows'], st['gates']), flush=True)
