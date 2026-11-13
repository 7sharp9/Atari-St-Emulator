"""forecast_check.py <ladder_dir> <side>: what the commander's forecast reads, per arm and rung. For every dump
<snap>/<tag>_k<k>.ram, rollout.summary() (the observation, per-side totals and the score the rollout policy ranks
candidates by) is computed for <side>, and its score and obs_hash compared with base_a's at the same k.
Prints one line per (snap, k): base_a's score and hash, then each arm's 'same' or its differing values."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from rollout import summary   # noqa: E402

D, side = Path(sys.argv[1]), int(sys.argv[2])
bad = 0
for sd in sorted(p for p in D.iterdir() if p.is_dir()):
    ks = sorted({int(f.stem.rsplit('_k', 1)[1]) for f in sd.glob('base_a_k*.ram')})
    for k in ks:
        R0 = (sd / f'base_a_k{k}.ram').read_bytes()
        _, b = summary(R0, side)
        line = [f'{sd.name} k={k} base_a score={b["score"]} hash={b["obs_hash"]}']
        for f in sorted(sd.glob(f'*_k{k}.ram')):
            tag = f.stem.rsplit('_k', 1)[0]
            if tag == 'base_a':
                continue
            _, r = summary(f.read_bytes(), side)
            same = r['score'] == b['score'] and r['obs_hash'] == b['obs_hash'] and r['sides'] == b['sides']
            bad += (not same) and not tag.startswith('neg_')
            line.append(f'{tag}={"same" if same else "DIFF(score " + str(r["score"]) + " hash " + r["obs_hash"] + ")"}')
        print(' '.join(line))
print(f'non-control arms differing from base_a: {bad}')
