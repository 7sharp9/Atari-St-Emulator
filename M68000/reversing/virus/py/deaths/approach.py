"""Per ground death: the last ticks before the crash from the replayed approach (death_census.py `approach`):
fuel at the first of the last ticks, tick at which fuel reached 0 (None if never in the window), thrust-asked ticks (D2 bit 1) in the
last 25 ticks and the mean change of vy on thrust-asked ticks with fuel > 0 (negative = thrust is braking the fall), peak vy, vy at death.
uv run python approach.py [work dir]"""
import sys, os, json
sys.argv = sys.argv[:1] + sys.argv[1:2]
import aggregate as A
def analyse(d):
    T = d['approach']['ticks']
    if len(T) < 4: return None
    last = T[-25:]
    th = [x for x in last if x['d'][2] & 2]
    dv = []
    for a, b in zip(T[-26:-1], T[-25:]):
        if a['d'][2] & 2 and a['fuel'] > 0: dv.append(b['ship'][4] - a['ship'][4])
    f0 = next((x['tick'] for x in T if x['fuel'] == 0), None)
    return dict(n_thrust_asked=len(th), mean_dvy_thrust=(sum(dv) / len(dv)) if dv else None, peak_vy=max(x['ship'][4] for x in last),
                vy_death=T[-1]['ship'][4], fuel0_tick=f0, tick=T[-1]['tick'], fuel_first=last[0]['fuel'],
                coast_ticks=sum(1 for x in last if not x['d'][2] & 2 and x['fuel'] > 0))
if __name__ == '__main__':
    for r in A.rows:
        if not r['cause'].startswith('ground'): continue
        a = analyse(r['d']) if 'approach' in r['d'] else None
        print(f"g{r['game']:03d}#{r['n']} w{r['wave']} fuel {r['fuel']:5d} replay_ok={r['replay_end']}", a)
