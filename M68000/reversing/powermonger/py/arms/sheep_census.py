"""sheep_census.py <snap>...: kind-8 (byte6 == 8, animal) records, their owner byte 5, cell (bytes 8/10), and the cell of every
local-side group lead; prints the nearest sheep to each local lead (Chebyshev).  (PowerMonger 148th, agent A)"""
import os, sys
from pathlib import Path
def _root():
    if os.environ.get('M68000_ROOT'): return Path(os.environ['M68000_ROOT'])
    for p in Path(__file__).resolve().parents:
        if (p / 'tools' / 'pm_fsm_ref.py').exists(): return p
ROOT = _root()
sys.path.insert(0, str(ROOT / 'tools'))
import pm_fsm_ref as P
from pm_common import OBJ, OBJ_STRIDE
from disassemble import ram_from_snap
GROUPS = 0x51538
def run(snap, verbose=True):
    ram = ram_from_snap(snap); m = P.Mem(ram)
    local = m.wu(0x57ffe)
    sheep = []
    n = P.s16(m.wu(0x4cff6)) // 20            # animals: 20-byte records at $4ccd6, byte 6 == 8 sheep, byte 7 state ($11 free, $12 herded, $10 dead)
    for i in range(n):
        a = 0x4ccd6 + i * 20
        if m.bu(a + 6) == 8:
            sheep.append((a - OBJ, P.s8(m.bu(a + 5)), m.bu(a + 8), m.bu(a + 10), m.bu(a + 7), 0))
    leads = []
    base = GROUPS + local * 0x13c
    for D7 in range(0, 12, 2):
        if m.wu(base + 28 + D7) == local and local > 0:
            lo = m.wu(base + 64 + D7)
            a = OBJ + P.s16(lo)
            leads.append((D7, m.wu(base + 52 + D7), m.wu(base + 76 + D7), m.bu(a + 8), m.bu(a + 10)))
    if verbose:
        print(snap, 'local side', local, 'sheep', len(sheep), 'owners', sorted(set(s[1] for s in sheep)))
        for l in leads:
            best = sorted((max(abs(s[2] - l[3]), abs(s[3] - l[4])), s) for s in sheep)[:3]
            print('   local group D7', l[0], 'men', l[1], 'state', l[2], 'lead cell', (l[3], l[4]), 'nearest sheep', [(d, s[0], s[2], s[3], s[1], hex(s[4]), hex(s[5])) for d, s in best])
    return sheep, leads
if __name__ == '__main__':
    for s in sys.argv[1:]:
        run(s)
