"""table.py <chain.jsonl>: per-game table (wave reached, score, game-over tick, flight steps, carried queue) and the trend tests:
Spearman rank correlation of each metric against the game index, exact-ish two-sided permutation p (20000 shuffles, fixed seed),
and the first-half vs second-half medians.  Pure python.  Wave = the $32a50 value at the last life's decrement."""
import sys, json, random, statistics
rows = [json.loads(l) for l in open(sys.argv[1])]
def rank(v):
    o = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0]*len(v); i = 0
    while i < len(o):
        j = i
        while j+1 < len(o) and v[o[j+1]] == v[o[i]]: j += 1
        for k in range(i, j+1): r[o[k]] = (i+j)/2+1
        i = j+1
    return r
def spearman(x, y):
    a, b = rank(x), rank(y); ma, mb = statistics.mean(a), statistics.mean(b)
    num = sum((p-ma)*(q-mb) for p, q in zip(a, b)); den = (sum((p-ma)**2 for p in a)*sum((q-mb)**2 for q in b))**.5
    return num/den if den else float('nan')
def perm_p(x, y, n=20000):
    r0 = abs(spearman(x, y)); rnd = random.Random(1); y2 = list(y); c = 0
    for _ in range(n):
        rnd.shuffle(y2); c += abs(spearman(x, y2)) >= r0 - 1e-12
    return (c+1)/(n+1)
print('game  wave  score  over_tick  flight_Msteps  over->next_Msteps  wall_s  lives_lost  prev_wave($32a52)  queue')
for r in rows:
    print(f"{r['game']:4d}  {r['over']['wave']:4d}  {r['over']['score']:6d}  {r['over']['tick']:8d}  {r['flight_steps']/1e6:11.1f}  {r['over_to_next_steps']/1e6:15.1f}  {r['wall_s']:6.1f}  {len(r['losses']):4d}  {r['w32a52']:6d}  {r['queue'][:24]}")
g = list(range(1, len(rows)+1)); n = len(g)
for name, v in [('wave', [r['over']['wave'] for r in rows]), ('score', [r['over']['score'] for r in rows]),
                ('over_tick', [r['over']['tick'] for r in rows]), ('flight_steps', [r['flight_steps'] for r in rows])]:
    h = n//2
    print(f'{name:12s} Spearman vs game index rho={spearman(g, v):+.3f} perm p={perm_p(g, v):.3f} n={n}; median first half {statistics.median(v[:h])} second half {statistics.median(v[h:])}; max {max(v)} at game {v.index(max(v))+1}')
