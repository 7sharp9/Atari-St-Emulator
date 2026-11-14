"""chain_table.py [chain.jsonl]: print the per-game table of an unpoked chain (chain.py output) and the rank correlation of the game
number with the game-over tick and score (Spearman, n games; with n this small it is a weak test, exact p is not claimed)."""
import sys, os, json
root = os.path.abspath(os.path.dirname(__file__))
while not os.path.exists(os.path.join(root, 'tools', 'rdis.py')): root = os.path.dirname(root)
f = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, 'scratchpad', 'virus', 'demo', 'chain', 'chain.jsonl')
R = [json.loads(l) for l in open(f)]
def rank(v): o = sorted(v); return [o.index(x) + 1 for x in v]
def rho(x, y):
    n = len(x); rx, ry = rank(x), rank(y); d = sum((a - b) ** 2 for a, b in zip(rx, ry)); return 1 - 6 * d / (n * (n * n - 1))
print('game | RNG at start     | $27134 entries 0,1 (x,y,z)        | life-loss ticks                         | over tick | over score | wave | losses | top-4 table at start')
for r in R:
    e = r['table27134']; t = ' '.join(e[12*i:12*i+12] for i in range(2)) if e != '0' * 48 else 'zeros'
    print(f"{r['game']:4d} | {r['rng']} | {e[:12]} {e[12:24]}"[:70].ljust(70), '|', ','.join(str(l['tick']) for l in r['losses']).ljust(40), f"| {r['over']['tick']:9d} | {r['over']['score']:10d} | {r['over']['wave']:4d} | {len(r['losses']):6d} | {r['hs_scores'][:4]}")
n = [r['game'] for r in R]
print('first life-loss tick by game :', [r['losses'][0]['tick'] for r in R], ' rho vs game number = %.2f' % rho(n, [r['losses'][0]['tick'] for r in R]))
print('game-over tick by game       :', [r['over']['tick'] for r in R], ' rho = %.2f' % rho(n, [r['over']['tick'] for r in R]))
print('game-over score by game      :', [r['over']['score'] for r in R], ' rho = %.2f' % rho(n, [r['over']['score'] for r in R]))
print('life losses per game         :', [len(r['losses']) for r in R], ' rho = %.2f' % rho(n, [len(r['losses']) for r in R]))
