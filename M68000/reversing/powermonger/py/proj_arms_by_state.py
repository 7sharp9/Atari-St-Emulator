"""Per-state arm tags of pm_fsm_ref.call_596a over the natural $596a corpus (scratchpad/pm140/proj/corpus).
Model only (no emulator): prints each state's PROJ_TRACE counter and the total, so the gate's arm
totals (gate_proj.py) can be read as events per state.  Usage: uv run python <this> """
import collections, sys
from pathlib import Path
here = Path(__file__).resolve()
ROOT = next(p for p in here.parents if (p / "tools" / "rdis.py").exists())
sys.path.insert(0, str(ROOT / "tools"))
import pm_fsm_ref as P
tot = collections.Counter(); per = collections.Counter(); n = exc = 0
for sn in sorted((ROOT / "scratchpad/pm140/proj/corpus").glob("*/*.snap")):
    ram0 = sn.with_suffix(".ram").read_bytes()
    P.init_tables(ram0); m = P.Mem(ram0); P.PROJ_TRACE.clear()
    try:
        P.call_596a(m)
    except AssertionError as e:
        exc += 1; print("excluded", sn.stem, dict(collections.Counter(P.PROJ_TRACE))); continue
    c = collections.Counter(P.PROJ_TRACE); n += 1; tot.update(c)
    for k in c: per[k] += 1
    if set(c) - {"fly_miss"}: print(sn.parent.name, sn.stem, dict(c))
print(f"states {n} excluded {exc}; arm events {dict(tot)}; states containing each arm {dict(per)}")
