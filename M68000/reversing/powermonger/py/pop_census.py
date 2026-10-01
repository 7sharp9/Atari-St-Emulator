"""The starting population of a land, from the entry state of `$2984` (`capture_hits.py` of its one hit, see `gate_pop.py`):
runs the model `pm_fsm_ref.call_2984` on the RAM image and prints, per land, the men by job, the free field sites (flag bit 4 of
the `$4592f` plane) before and after, the animals and catch markers made, and how each merchant came about.

    cd M68000 && python reversing/powermonger/py/pop_census.py scratchpad/pm139/corpus_2984/k*_1.ram

`economy.md` 5a's table is this output over lands 0, 1, 5, 10, 25, 60, 100, 142. The model is Proven against the 68000 on the same
states (`gate_pop.py`), so this reads the model, not the emulator.
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
import pm_fsm_ref as P

for path in sys.argv[1:]:
    ram = Path(path).read_bytes()
    P.init_tables(ram)
    m = P.Mem(ram)
    sites0 = sum(1 for i in range(0x2000) if ram[P.FLAGS + i] & 0x10)
    P.JOB_TRACE.clear()
    P.call_2984(m)
    sites1 = sum(1 for i in range(0x2000) if m.r[P.FLAGS + i] & 0x10)
    jobs = collections.Counter()
    for s in range(1, 512):
        a = P.OBJ + s * P.REC
        if m.r[a + 5] and not ram[a + 5]:
            b7 = m.r[a + 7]
            jobs[9 if b7 & 0x10 else b7 & 0xf] += 1
    calls, cur = [], []
    for t in P.JOB_TRACE:
        cur.append(t)
        if t in ("captain", "shepherd", "fisher", "farmer", "merchant"):
            calls.append(cur)
            cur = []
    giveup = sum(1 for c in calls if c[-1] == "merchant" and "giveup" in c)
    exhausted = sum(1 for c in calls if c[-1] == "merchant" and "giveup" not in c)
    stale = P.JOB_TRACE.count("farmer_fail_stale")
    genuine = P.JOB_TRACE.count("farmer_fail")
    print(f"{Path(path).stem:10} men={sum(jobs.values()):3d} captain={jobs[9]} farmer={jobs[1]} fisher={jobs[4]} shepherd={jobs[8]} "
          f"merchant={jobs[2]} (give-up {giveup}, five rounds {exhausted}) | field sites {sites0}->{sites1} | animals {m.wu(P.ANIMAL_COUNT) // 20} "
          f"markers {m.wu(P.FISH_COUNT) // 10} | farmer failures: stale D1 {stale}, genuine {genuine}")
