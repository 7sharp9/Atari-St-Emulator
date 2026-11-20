"""Per-life fuel budget from work/gNNN.json (a_life: drain by writer class over the whole life; ticks from tick counters).
uv run python lives.py"""
import sys; sys.argv = sys.argv[:1]
import aggregate as A, collections, statistics as S
cls = collections.Counter(); out = []
for r in A.rows:
    d = r['d']; a = d['a_life']
    cls.update(a.keys())
for g in sorted({r['game'] for r in A.rows}):
    prev = 0
    for r in [x for x in A.rows if x['game'] == g]:
        life = r['tick'] - prev; prev = r['tick'] + 51
        a = r['d']['a_life']
        r['life_ticks'] = max(life, 1)
print('classes seen in a_life:', dict(cls))
def stats(rows, label):
    if not rows: return
    f = lambda k: S.mean(-x['d']['a_life'].get(k, 0) for x in rows)
    print(f"{label:30s} n={len(rows):3d} life ticks mean {S.mean(x['life_ticks'] for x in rows):6.0f}  drain per life: thrust {f('thrust'):6.0f} fire {f('fire'):5.0f} shot {f('shot'):5.0f} bomb {f('bomb'):5.0f} attractor {f('attractor'):5.0f}  thrust ticks/life tick {S.mean(-x['d']['a_life'].get('thrust',0)/3/x['life_ticks'] for x in rows):.2f}  shot hits mean {S.mean(x['d']['hits_life']['shot'] for x in rows):.2f} bomb hits {S.mean(x['d']['hits_life']['bomb'] for x in rows):.2f}")
stats(A.rows, 'all lives')
stats([x for x in A.rows if x['fuel'] == 0], 'died with fuel 0')
stats([x for x in A.rows if x['fuel'] > 0], 'died with fuel > 0')
stats([x for x in A.rows if x['cat'] == 'ground, fuel 0'], 'ground, fuel 0')
stats([x for x in A.rows if x['cat'] == 'ground, fuel > 0'], 'ground, fuel > 0')
stats([x for x in A.rows if x['cause'].startswith('flag:EnemyShot')], 'shot borrow')
# lives that died with fuel 0: how many had 0, 1, 2, 3+ shot hits
c = collections.Counter(min(x['d']['hits_life']['shot'] + x['d']['hits_life']['bomb'], 4) for x in A.rows if x['fuel'] == 0)
print('fuel-0 deaths by (shot+bomb hits in the life):', sorted(c.items()))
c = collections.Counter(min(x['d']['hits_life']['shot'] + x['d']['hits_life']['bomb'], 4) for x in A.rows if x['fuel'] > 0)
print('fuel>0 deaths by (shot+bomb hits in the life):', sorted(c.items()))
# fuel-0 ground deaths: free-fall length from fuel-out to impact (ticks), from the approach window
fl = []
for x in A.rows:
    if x['cat'] == 'ground, fuel 0' and 'approach' in x['d']:
        T = x['d']['approach']['ticks']; f0 = next((t['tick'] for t in T if t['fuel'] == 0), None)
        if f0 is not None and T[0]['fuel'] > 0: fl.append(T[-1]['tick'] - f0)
print('fuel-0 ground deaths whose window shows the fuel-out tick: n', len(fl), 'ticks from fuel 0 to impact', sorted(fl))
