"""summarise.py ladder <ladder_dir> | timing <timing_dir>

ladder: per start snapshot and arm, steps per tick (from the k=1000 row, or the last rung) and the compare.jsonl verdict
per rung (sim regions equal or the differing regions with byte counts; RNG fields).
timing: per snapshot and arm, wall seconds for the timed tick count over the rounds (median, min), steps, steps/tick,
steps/s, and the per-round ratio base/arm, with the load average recorded in each row.
"""
import json, statistics, sys
from pathlib import Path


def rows(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def ladder(D):
    D = Path(D)
    cmp = {}
    for r in rows(D / 'compare.jsonl'):
        cmp.setdefault((r['snap'], r['tag']), {})[r['k']] = r['cmp']
    for sd in sorted(p for p in D.iterdir() if p.is_dir()):
        print(f'== {sd.name}')
        for f in sorted(sd.glob('*.jsonl')):
            rs = rows(f); tag = f.stem
            last = rs[-1]
            spt = last['steps'] / last['k'] if last.get('k') else None
            line = f'  {tag:10s} k={last.get("k")} steps={last.get("steps")} steps/tick={spt:,.0f}' if spt else f'  {tag} {last}'
            print(line)
            for k, c in sorted(cmp.get((sd.name, tag), {}).items()):
                bad = {n: v['bytes'] for n, v in c['sim'].items() if v['bytes']}
                rng = ''.join('=' if v['equal'] else 'x' for v in c['rng'].values())
                print(f'      k={k:5d} sim {"EQUAL" if c["sim_equal"] else "DIFFER " + json.dumps(bad)} rng[lcg,season,seed]={rng}'
                      f' outside={c["outside_bytes"]} total={c["total"]}')


def timing(D):
    D = Path(D)
    for sd in sorted(p for p in D.iterdir() if p.is_dir()):
        by = {}
        for f in sd.glob('*_r*.jsonl'):
            arm, rnd = f.stem.rsplit('_r', 1)
            r = rows(f)[-1]
            by.setdefault(arm, {})[int(rnd)] = r
        print(f'== {sd.name}')
        for arm in ['base', 'f898', 'gated', 'drawall']:
            if arm not in by:
                continue
            w = [r['wall_s'] for r in by[arm].values()]
            r0 = next(iter(by[arm].values()))
            ratios = [round(by['base'][n]['wall_s'] / by[arm][n]['wall_s'], 2) for n in sorted(by[arm]) if n in by.get('base', {})]
            loads = [r['uptime'].split('load averages:')[-1].split()[0] for _, r in sorted(by[arm].items())]
            print(f'  {arm:8s} k={r0["k"]} steps={r0["steps"]:,} steps/tick={r0["steps"] / r0["k"]:,.0f} '
                  f'wall median {statistics.median(w):.2f} min {min(w):.2f} (n={len(w)}) '
                  f'Msteps/s {r0["steps"] / statistics.median(w) / 1e6:.2f} base/arm per round {ratios} load1 {loads}')


if __name__ == '__main__':
    {'ladder': ladder, 'timing': timing}[sys.argv[1]](sys.argv[2])
