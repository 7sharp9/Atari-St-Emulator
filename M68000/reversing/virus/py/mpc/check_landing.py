"""Landing and pad paths: a rule-based descent onto the launch pad planned with exact.step_game, replayed in the game,
then 40 ticks sitting on the pad and a take-off.   uv run python check_landing.py   (writes seq_landing.json, out_landing.json)
Compares every tick's state, fuel, latch $62a63 and the outcome class with the game's path markers."""
import json, math, os, sys
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import exact, replay as R

exact.load()
st = dict(pos=[1604, -6980, 3047], vel=[26, -330, 162], att=[5016, -16383], g=3, fuel=3961, latch=0xff, contact=0)
ctl = []; sim = [dict(st)]; outs = []; landed_at = None
for k in range(900):
    x, y, z = st['pos']; vx, vy, vz = st['vel']
    if landed_at is not None and k < landed_at + 40:
        u = [0, 0, 0]                                   # sit on the pad
    elif landed_at is not None:
        u = [0x400, 0x2000, 2]                          # take off
    else:
        c = exact.clearance(st['pos'])
        wx = max(-50, min(50, (1024 - x) / 24)); wz = max(-50, min(50, (1024 - z) / 24))
        ax = wx - vx; az = wz - vz                      # wanted change of horizontal velocity
        mag = math.hypot(ax, az)
        head = int(math.atan2(-az, ax) / (2 * math.pi) * 65536) & 0xffff      # accel = (s0*cos1, -cos0, -s0*s1)
        tilt = int(min(0x1800, mag * 0x200)) if c > 300 else int(min(0x600, mag * 0x100))
        want = max(18, min(150, c // 10))
        thrust = vy > want
        if c > 1500 and mag > 6 and vy > -20:
            thrust = True                               # spend height on horizontal correction
        u = [tilt, head, 2 if thrust else 0]
    st, out = exact.step_game(st, u)
    ctl.append(u); outs.append(out); sim.append(dict(st))
    if out == 'landed' and landed_at is None:
        landed_at = k
    if out.startswith('dead'):
        break
    if landed_at is not None and k >= landed_at + 60:
        break
cnt = {}
for o in outs: cnt[o] = cnt.get(o, 0) + 1
print('model plan:', len(ctl), 'ticks; outcomes', cnt, '; landed at tick', landed_at, '; final', sim[-1]['pos'], sim[-1]['vel'])
json.dump(ctl, open(os.path.join(R.WORK, 'seq_landing.json'), 'w'))
if landed_at is None:
    raise SystemExit('the model plan did not land: no game run made')
out = R.replay(ctl, ground=True)
json.dump(out, open(os.path.join(R.WORK, 'out_landing.json'), 'w'))
T = out['ticks']; N = len(T) - 1 if out['complete'] else len(T) - 1
print(f'game: {N} ticks compared, complete {out["complete"]}, end {out["end"]}, {out["seconds"]} s')
n = dict(state=0, fuel=0, latch=0, contact=0, outcome=0); seen = {}
for k in range(N):
    a, b, m = T[k], T[k + 1], sim[k + 1]
    good = m['pos'] == b['pos'] and m['vel'] == b['vel'] and m['att'] == b['att']
    p = a['path']
    game = 'landed' if 'landed' in p else 'pad' if 'pad' in p else 'low' if 'low' in p else 'free'
    seen[game] = seen.get(game, 0) + 1
    n['state'] += good; n['fuel'] += m['fuel'] == b['fuel']; n['latch'] += bool(m['latch']) == bool(b['flags']['latch_62a63'])
    n['contact'] += bool(m['contact']) == bool(b['flags']['x_62a62']); n['outcome'] += game == outs[k]
    if not good or game != outs[k]:
        print('  MISMATCH tick', k, 'model', outs[k], m['pos'], m['vel'], m['att'], 'game', p, b['pos'], b['vel'], b['att'])
print('  ' + '; '.join(f'{k} {v}/{N}' for k, v in n.items()) + f'; game outcomes {seen}')
print('  raw around the landing:', [(k, T[k]['pos'], T[k]['vel'], T[k]['fuel'], T[k]['path']) for k in range(landed_at - 1, landed_at + 4)])
