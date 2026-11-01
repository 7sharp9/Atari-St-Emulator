"""outcomes.py <seeds out> <side> <arm> ...: score finished seeds.sh runs by land outcome for <side>. Per arm: won
(end ratio 4), lost by the captain's death, lost by the no-lord retire (captain alive, side holds 0 lords), alive at
the budget; median and range of the loss step; LLM calls and cost from each run's llm/llm.jsonl. Then one line per
start, and for every pair of arms a two-sided sign test on a per-start rank (a win, earlier better; then alive; then a
loss, later better) and an exact McNemar test on the starts only one arm won. Starts are the o<k> dirs every arm has.
("Land 2 as a rate" in README.md is scored with it.)"""
import json, os, sys, statistics as st
from math import comb
out, side, arms = sys.argv[1], sys.argv[2], sys.argv[3:]
ks = sorted(set.intersection(*[{int(d[1:]) for d in os.listdir(f'{out}/{a}') if d[:1] == 'o' and d[1:].isdigit()}
                              for a in arms]))
R = {}
for a in arms:
    R[a] = {}
    for k in ks:
        d = f'{out}/{a}/o{k}'
        e = json.loads(open(d + '/decisions.jsonl').readlines()[-1])
        if e['kind'] != 'end':
            print(a, k, 'not ended'); continue
        lords = e['totals'][side]['lords']
        c = ('won' if e.get('ratio') == 4 else 'alive' if e['reason'] == 'budget'
             else 'nolord' if e.get('local_captain_owner') == int(side) and lords == 0 else 'killed')
        calls = [json.loads(l) for l in open(d + '/llm/llm.jsonl')] if os.path.exists(d + '/llm/llm.jsonl') else []
        R[a][k] = dict(c=c, step=e['step'], lords=lords, n=len(calls), cost=sum(x.get('cost_usd') or 0 for x in calls))
ks = [k for k in ks if all(k in R[a] for a in arms)]

def p2(w, l):
    n = w + l
    return min(1, 2 * sum(comb(n, i) for i in range(min(w, l) + 1)) / 2 ** n) if n else 1

for a in arms:
    xs = [R[a][k] for k in ks]
    n = {c: sum(x['c'] == c for x in xs) for c in ('won', 'killed', 'nolord', 'alive')}
    loss = [x['step'] / 1e6 for x in xs if x['c'] in ('killed', 'nolord')]
    print(f"{a}: {len(xs)} starts, won {n['won']} killed {n['killed']} no-lord {n['nolord']} alive {n['alive']}",
          f'loss median {st.median(loss):.0f}M ({min(loss):.0f}..{max(loss):.0f}M)' if loss else '',
          f"LLM {sum(x['n'] for x in xs)} calls ${sum(x['cost'] for x in xs):.2f}")
for k in ks:
    print(f'o{k}', ' '.join(f"{a}:{R[a][k]['c']}/{R[a][k]['step'] // 1000000}M" for a in arms))

def rank(x):
    return (2, -x['step']) if x['c'] == 'won' else (1, 0) if x['c'] == 'alive' else (0, x['step'])
for i, a in enumerate(arms):
    for b in arms[i + 1:]:
        w = sum(rank(R[a][k]) > rank(R[b][k]) for k in ks); l = sum(rank(R[a][k]) < rank(R[b][k]) for k in ks)
        wa = sum(R[a][k]['c'] == 'won' != R[b][k]['c'] for k in ks); wb = sum(R[b][k]['c'] == 'won' != R[a][k]['c'] for k in ks)
        print(f'{a} vs {b}: above {w}, below {l}, tie {len(ks) - w - l}, sign p={p2(w, l):.4g};'
              f' won only {a} {wa}, only {b} {wb}, McNemar p={p2(wa, wb):.4g}')
