"""The 9th branch of the forest animator $4342: a marker arriving at its tree ($44c6: bset #7 of the
tree's state, $16778 unlink), against pm_fsm_ref.call_4342, from markers claimed live.

diff_4342.py's poked arrival ("step_expire_arrive") puts a marker that was never $16808-inserted
next to its tree, so its unlink finds nothing. Here the claim itself runs live: diff_4342's claim
pokes on pm97_map0 (tree 0 gets worker slot 1, slot 1's byte 6 := 0), then the game runs.
Each claimed marker is snapped to its tree's cell, ramps in, takes a degenerate zero-distance
$164bc step that sends it away (dwell 62 for marker 0), and arrives on the way back.

A. pokes, then `bp 44c6` / `s 1` NARR times: the absolute step of every arrival.
B. per arrival tick, a run to 20k steps before it and `bp 4342`: the snapshot at that tick's
   $4342 entry (in parallel, one emulator each).
C. pm_fsm_diff.Harness on those snapshots, no pokes, callcap $4342 vs call_4342.

Run from anywhere (repo root found by walking up to tools/rdis.py):
    python reversing/powermonger/py/fsm/gate_4342_arrive.py [reuse]
Output in $PM_WORK/f4342 (default scratchpad/pm161/f4342).
"""
import os
import re
import struct
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

M68 = next(p for p in Path(__file__).resolve().parents if (p / "tools/rdis.py").exists())
os.chdir(M68)
sys.path.insert(0, str(M68 / "tools"))
import pm_fsm_ref
pm_fsm_ref.REGIONS = pm_fsm_ref.REGIONS + pm_fsm_ref.HERD_REGIONS   # process-local only
from pm_fsm_diff import Harness, State

ANCHOR = "scratchpad/pm97/pm97_map0.snap"
OUT = f"{os.environ.get('PM_WORK', 'scratchpad/pm161')}/f4342"
NARR = 12
LEAD = 20_000
Path(OUT).mkdir(parents=True, exist_ok=True)

R = Path("scratchpad/pm97/pm97_map0.ram").read_bytes()
wu = lambda a: struct.unpack_from(">H", R, a)[0]
TREE0 = pm_fsm_ref.HERD_ANIMALS + wu(pm_fsm_ref.HERD_OPS + 4)
SHEP = pm_fsm_ref.REC
POKES = Harness.bytepokes(R, {TREE0 + 2: (SHEP >> 8) & 0xff, TREE0 + 3: SHEP & 0xff,
                              pm_fsm_ref.OBJ + SHEP + 6: 0})
PK = [f"w {a:x} {w:08x}" for a, w in POKES]


def repl(cmds):
    p = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", ANCHOR, "repl"],
                       input="\n".join(["disk scratchpad/pm69.st"] + PK + cmds + ["q"]) + "\n",
                       capture_output=True, text=True, env=dict(os.environ, ATARI_NOTRACE="1"))
    return p.stdout + p.stderr


reuse = "reuse" in sys.argv[1:]
snaps = sorted(Path(OUT).glob("arr_*.snap"))
if not (reuse and snaps):
    # A. every arrival, by absolute step from the poked anchor
    log = repl(sum([["bp 44c6 50000000", "s 1"] for _ in range(NARR)], []))
    ns = [int(n) for n in re.findall(r"breakpoint \$000044c6 hit \(1/1\) after (\d+) step", log)]
    assert len(ns) == NARR, f"{len(ns)} of {NARR} arrivals:\n{log[-800:]}"
    arr, t = [], 0
    for n in ns:
        t += n
        arr.append(t)
        t += 1
    ticks = [a for i, a in enumerate(arr) if i == 0 or a - arr[i - 1] > 100_000]
    print(f"A. {NARR} arrivals at steps {arr}; {len(ticks)} arrival ticks")

    # B. the $4342 entry of each arrival tick
    def snap_tick(i_a):
        i, a = i_a
        p = f"{OUT}/arr_{i}.snap"
        log = repl([f"s {a - LEAD}", "bp 4342 300000", f"snap {p}"])
        m = re.search(r"breakpoint \$00004342 hit \(1/1\) after (\d+) step", log)
        assert m and a - LEAD + int(m.group(1)) < a, f"tick {i}: $4342 entry not before the arrival"
        subprocess.run([sys.executable, "reversing/powermonger/py/snap2ram.py", p], check=True)
        return p
    with ThreadPoolExecutor(max_workers=len(ticks)) as ex:
        snaps = [Path(p) for p in ex.map(snap_tick, enumerate(ticks))]

# C. callcap $4342 on each arrival tick vs the model
h = Harness(ANCHOR, "scratchpad/pm97/pm97_map0.ram", out_dir=OUT)
states = []
for p in snaps:
    st = State(p.stem, [], tag="arrive", snap=str(p), ram=str(p.with_suffix(".ram")), target="4342")
    st.recon = lambda m: pm_fsm_ref.call_4342(m)
    states.append(st)
h.run_corpus(states, min_states=len(states), min_branches=1, steps=200_000, reuse_json=reuse)
