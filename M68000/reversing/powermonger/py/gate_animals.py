"""139th: the animals' per-tick update (the `$4044..$4166` loop of `$3e06`) vs the real 68000 through callcap 3e06 on the snapshots
of a time series after a land build (`build_series.py`; here all 60 of lands 0 and 5).

`$3e06` does much more (army food, the health indicator, the pigeon records, `$4342`, `$596a`), so the comparison is restricted to what
the animal loop owns: the 40 animal records (links included) and the bucket chains (order, forward and backward links) of every cell an
animal left or entered. The pigeon records' moves and non-player arrivals (`call_pigeons`) are modelled because they relink into the same
buckets right after the animals; snapshots with a live projectile (`$596a`, not modelled) are skipped.

    cd M68000 && python reversing/powermonger/py/gate_animals.py [name-substring]
"""
import collections
import os
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import pm_fsm_ref as P
from pm_fsm_diff import Harness
from disassemble import ram_from_snap

S = os.environ.get("PM_SERIES", "scratchpad/pm139/series")      # PM_SERIES / PM_GATE_OUT: another roll, `build_series.py` with `PAGES0=1`
OUT = os.environ.get("PM_GATE_OUT", "scratchpad/pm139/g4")
(ROOT / OUT).mkdir(parents=True, exist_ok=True)
P.REGIONS = P.REGIONS + [(P.ANIMALS, P.ANIMAL_COUNT + 2, "animals"), (P.RNG_SEED, P.RNG_SEED + 4, "rng")]


def ram_of(name):
    ram = ROOT / S / f"{name}.ram"
    if not ram.exists():
        ram.write_bytes(ram_from_snap(str(ROOT / S / f"{name}.snap")))
    return ram.read_bytes()


def cell_of(r, a):
    return (((r[a + 10] << 8 | r[a + 11]) & 0xff00) >> 2) + r[a + 8]


def chain(r, cell):
    out, d = [], int.from_bytes(r[P.BUCKETS + 2 * cell:P.BUCKETS + 2 * cell + 2], "big")
    while d and len(out) < 64:
        a = P.OBJ + P.s16(d)
        out.append((d, int.from_bytes(r[a:a + 2], "big"), int.from_bytes(r[a + 2:a + 4], "big")))
        d = out[-1][1]
    return out


ram_of("k0_00")
h = Harness(f"{S}/k0_00.snap", f"{S}/k0_00.ram", disk="scratchpad/powermonger.st", out_dir=OUT)
only = next((a for a in sys.argv[1:] if a != "reuse"), None)
tot = ok = n = 0
fails, arms, excluded = [], collections.Counter(), []
for k in (0, 5):
    for i in range(30):
        name = f"k{k}_{i:02d}"
        if only and only not in name:
            continue
        r0 = ram_of(name)
        if any(int.from_bytes(r0[a + 14:a + 16], "big") for a in range(0x4be00, 0x4c110, 16)):
            excluded.append(name)          # a live projectile: `$596a` relinks it into the same buckets and is not modelled
            continue
        h.run_repl([f"callcap 3e06 4000000 {OUT}/o_{name}.json"], f"{S}/{name}.snap")
        j = json.load(open(ROOT / OUT / f"o_{name}.json"))
        if j.get("outcome") != "returned":
            fails.append((name, "outcome", j.get("outcome")))
            continue
        real = bytearray(r0)
        for a, b0, b1 in j["mem"]:
            real[a] = b1
        P.init_tables(r0)
        m = P.Mem(r0)
        P.ANIMAL_TRACE.clear()
        P.call_animals(m)
        P.PIGEON_TRACE.clear()
        P.call_pigeons(m)
        arms.update(P.ANIMAL_TRACE)
        arms.update('pigeon_' + t for t in P.PIGEON_TRACE)
        cells = set()
        for sl in range(40):
            a = P.ANIMALS + 20 * sl
            if r0[a + 6]:
                cells.add(cell_of(r0, a))
                cells.add(cell_of(m.r, a))
                cells.add(cell_of(real, a))
        diffs = [a for a in range(P.ANIMALS, P.ANIMAL_COUNT + 2) if real[a] != m.r[a]]
        cdiff = [c for c in cells if chain(real, c) != chain(m.r, c)]
        changed = sum(1 for a in range(P.ANIMALS, P.ANIMAL_COUNT) if r0[a] != real[a])
        tot += (P.ANIMAL_COUNT + 2 - P.ANIMALS) + len(cells)
        ok += (P.ANIMAL_COUNT + 2 - P.ANIMALS) - len(diffs) + len(cells) - len(cdiff)
        n += 1
        print(f"{name:8} steps={j['steps']:6d} animal bytes changed={changed:3d} cells={len(cells):2d} "
              f"{dict(collections.Counter(P.ANIMAL_TRACE + ["pigeon_" + t for t in P.PIGEON_TRACE]))}  {'ok' if not diffs and not cdiff else 'MISMATCH pool %d chains %d' % (len(diffs), len(cdiff))}")
        for a in diffs[:6]:
            fails.append((name, hex(a), real[a], m.r[a]))
        for c in cdiff[:3]:
            fails.append((name, "cell", c, chain(real, c), chain(m.r, c)))
print(f"\nexcluded (live projectile, `$596a` not modelled): {excluded}")
print(f"COMPARED: {ok}/{tot} identical over {n} snapshots; arms {dict(arms)}")
if fails:
    print("FAILURES:")
    for f in fails[:30]:
        print("  ", f)
    sys.exit(1)
print("PASS")
