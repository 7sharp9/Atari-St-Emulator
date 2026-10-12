#!/usr/bin/env python3
"""cand66.py <land.snap>...: candidate sheep clicks for a lead water veto. For every cell sheep_cells.py classifies 'animal'
within 22 cells of the local side's group-0 lead: Chebyshev distance, whether the straight lead->cell line is dry (the march
can arrive), and the fraction of half-cell samples within 2 cells of the cell centre that are water (terrain byte 0)."""
import sys
from pathlib import Path
ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(ROOT / 'reversing/powermonger/py/arms'))
import pm_fsm_ref as P
import sheep_cells as SC
from disassemble import ram_from_snap
for sn in sys.argv[1:]:
    local, (lx, ly), men, res = SC.run(sn)
    m = P.Mem(ram_from_snap(sn))
    wat = lambda x, y: P.terrain_sample(m, int(x * 256), int(y * 256)) == 0
    for d, (x, y), cls, n, *_ in res:
        if cls != 'animal' or d > 22 or d < 2: continue
        line = all(not wat(lx + .5 + (x - lx) * t / 64, ly + .5 + (y - ly) * t / 64) for t in range(65))
        smp = [wat(x + .5 + dx / 4, y + .5 + dy / 4) for dx in range(-8, 9) for dy in range(-8, 9)]
        print(f'{Path(sn).stem} men {men} lead ({lx},{ly}) cell ({x},{y}) d {d} sheep {n} dryline {int(line)} water {sum(smp)/len(smp):.2f}')
