"""Gate for shot.actor_step (one actor-walker pass, record at arrival k -> record at arrival k+1) and the error of
shot.predict over 10, 20 and 40 ticks, per behaviour, against shot_capture.py runs.

    uv run python gate_actor.py cap_auto.json [...] [--control drag|spring|ground]
--mode oracle|frozen|ballistic selects what predict() is given for the patrol (default oracle).
Controls: nophase (tick phase off by one), oldship (ship position before the tick's move), drag (seeder vy drag 1/8), spring (target height $2c0), ground (the shot's sum-of-sines ground for the walker).
"""
import json, struct, sys
import shot as S

args = sys.argv[1:]
control = 'none'
mode = 'oracle'
if '--mode' in args:
    i = args.index('--mode'); mode = args[i + 1]; del args[i:i + 2]
if '--control' in args:
    i = args.index('--control'); control = args[i + 1]; del args[i:i + 2]
if control == 'ground':
    S.aground = S.exact.ground
if control in ('drag', 'spring'):
    import inspect
    src = inspect.getsource(S.actor_step)
    src = src.replace('vy = s16(vy - (vy >> 4))', 'vy = s16(vy - (vy >> 3))') if control == 'drag' else \
        src.replace('y - gh + 0x280', 'y - gh + 0x2c0')
    exec(src, S.__dict__)

step_t = {}; pred = {}
names = {b: '/'.join(v[:2]) for b, v in S.KINDS.items()}
for path in args:
    rows = json.load(open(path))['rows']
    pools = [S.unpack_pool(r['pool']) for r in rows]
    for k in range(len(rows) - 1):
        r, nx = rows[k], rows[k + 1]
        if any(e['e'] in ('dead', 'crash') for e in r['ev']):
            continue
        kills = [e['idx'] for e in r['ev'] if e['e'] == 'kill']
        hit_idx = {e['idx'] for e in r['ev'] if e['e'] == 'hit'}
        P, Q = pools[k], pools[k + 1]
        for i, a in enumerate(P):
            q0 = list(struct.unpack('>3h', bytes.fromhex(r['queue'])[:6]))
            t48 = r['tick44'] + i + 1 + sum(1 for x in kills if x < i) if 'nophase' != control else r['tick44'] + i
            got, info = S.actor_step(a, ship=nx['pos'] if control != 'oldship' else r['pos'], g=r['g'], tick48=t48, queue0=q0)
            nm = names.get(a[8], hex(a[8]))
            if info == 'unmodelled':
                continue
            t = step_t.setdefault(nm + (':' + info if info else ''), [0, 0])
            t[1] += 1
            if got is None:
                t[0] += i in kills
                continue
            if kills:                         # the pool was reordered this pass: find the record by content
                cand = [q for q in Q if q[8] == got[8] and q[:6] == got[:6]]
                t[0] += len(cand) == 1; continue
            q = list(Q[i])
            if i in hit_idx: q[6] = S.s16(q[6] & 0x7fff) if not (got[6] & 0x8000) else q[6]
            if info == 'rng':
                t[0] += (q[:3] + q[4:5] + q[6:]) == (got[:3] + got[4:5] + got[6:]); continue
            ok = q == got
            t[0] += ok
            if not ok and control == 'none' and t[1] - t[0] <= 3:
                print(path, k, i, nm, 'from', a, 'pred', got, 'game', q)
        # prediction error over horizons
        for i, a in enumerate(P):
            nm = names.get(a[8], hex(a[8]))
            if S.KINDS.get(a[8], ('', 'wait'))[1] == 'wait':
                continue
            for n in (10, 20, 40):
                if k + n >= len(rows) or any(rows[j]['npool'] != r['npool'] for j in range(k, k + n + 1)):
                    continue
                if any(any(e['e'] in ('dead', 'crash') for e in rows[j]['ev']) for j in range(k, k + n)):
                    continue
                q0 = list(struct.unpack('>3h', bytes.fromhex(r['queue'])[:6]))
                if mode == 'oracle':      # the ship's true future path and the tick phase; the queue as read at k
                    p = S.predict(a, n, g=r['g'], tick48=r['tick44'] + i + 1, queue0=q0,
                                  ship_path=[rows[k + 1 + j]['pos'] for j in range(n)])
                elif mode == 'frozen':    # the ship frozen where it is after tick k
                    p = S.predict(a, n, g=r['g'], tick48=r['tick44'] + i + 1, queue0=q0, ship=nx['pos'])
                else:                     # no tick phase: the ballistic fallback for the patrol
                    p = S.predict(a, n, ship=nx['pos'], g=r['g'])
                if len(p) < n:
                    continue
                act = pools[k + n][i][:3]
                err = max(abs(S.s16(p[-1][c] - act[c])) for c in range(3))
                d = pred.setdefault((nm, n), [])
                d.append(err)

print('control:', control, 'predict mode:', mode)
print('actor_step, record at k+1 == model (all nine fields):')
for nm, (a, b) in sorted(step_t.items()):
    print(f'  {nm:22s} {a}/{b}')
print('predict(a, n): max-axis position error after n ticks, by the state at the start (count, exact, median, p90, max):')
for (nm, n), d in sorted(pred.items()):
    d.sort()
    print(f'  {nm:16s} n={n:2d}  {len(d):5d}  exact {sum(1 for x in d if x == 0):5d}  med {d[len(d)//2]:5d}  '
          f'p90 {d[int(len(d)*.9)]:5d}  max {d[-1]:5d}   inside +-$a0: {sum(1 for x in d if x < 0xa0)}')
