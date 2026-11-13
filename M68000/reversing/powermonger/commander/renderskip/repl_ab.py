"""repl_ab.py <ladder_dir> <outdir> [rounds]: the same arms through the rollout's own engine path, the REPL behind
commander/loop.py's Emu (bin/Debug/net8.0/M68000.dll, `resume <snap> repl`, `bp d2c8 <n>`), interleaved.

For each start snapshot of the ladder and each round, arms base, f898 and drawall run, one process at a time with the
arm order rotated per round, for exactly the step count the stserver ladder recorded for that arm at k = 1000
(<ladder_dir>/<snap>/<arm>.jsonl, base from base_a). The arm's stub is a REPL `w` of the routine's first longword
with its top word replaced by $4e75. Writes one JSON row per run to <outdir>/repl_ab.jsonl (wall seconds of the
`bp` run alone, uptime) and, in round 1, saves the end snapshot and checks its simulation regions (compare.SIM)
against the stserver dump <arm>_k1000.ram: same steps from the same snapshot, so the two engines should agree.
"""
import json, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE))
from loop import Emu, ROOT                    # noqa: E402
from observe import load                      # noqa: E402
from compare import SIM                       # noqa: E402
from renderskip import ARMS                   # noqa: E402

SNAPS = {'rand1': 'scratchpad/pm142/rand1.snap', 'l2o0': 'scratchpad/cmd9/start/o0/final.snap',
         'm1s0': 'scratchpad/pm123/win/m1_s0.snap'}
ORDER = ['base', 'f898', 'drawall']

L, O = Path(sys.argv[1]), Path(sys.argv[2]); rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 3
O.mkdir(parents=True, exist_ok=True)
out = open(O / 'repl_ab.jsonl', 'a')
for r in range(1, rounds + 1):
    for n, snap in SNAPS.items():
        for i in range(3):
            arm = ORDER[(i + r) % 3]
            tag = 'base_a' if arm == 'base' else arm
            row = [json.loads(l) for l in open(L / n / f'{tag}.jsonl')][-1]
            assert row['k'] == 1000, row
            emu = Emu(ROOT / snap, O / f'{n}_{arm}_r{r}.err')
            for addr, w, v in ARMS[arm]:
                assert w == 2 and v == 0x4e75
                b = emu.mem(addr, 4)
                emu.send(f'w {addr:x} 4e75{b[2:].hex()}')
            t = time.time()
            steps, hit = emu.run(row['steps'])
            wall = time.time() - t
            res = dict(snap=n, arm=arm, round=r, steps=steps, land_end=hit, wall_s=round(wall, 3),
                       msteps_s=round(steps / wall / 1e6, 3), uptime=os.popen('uptime').read().strip())
            if r == 1:
                sp = O / f'{n}_{arm}_end.snap'
                emu.save(sp)
                A = load(sp); B = (L / n / f'{tag}_k1000.ram').read_bytes()
                res['sim_bytes_differ_vs_stserver'] = sum(A[i] != B[i] for _, lo, hi in SIM for i in range(lo, hi))
                sp.unlink()
            emu.close() if hasattr(emu, 'close') else emu.p.kill()
            out.write(json.dumps(res) + '\n'); out.flush()
            print(json.dumps(res), flush=True)
