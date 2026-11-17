"""Gate for the clock and needs tick `$24648` (README, "Needs and the clock"): calls the game's routine in `stserver`
on poked states and checks every word it can change (clock, date, thirst, hunger, bladder, illness, happy, the
house-event queue, the daily-appointment flags and the TOS Random seed) against `lcp_model.needs_tick`.

usage: gate_tick.py [n_states] [seed]
Needs $LCP_WORK (default <root>/scratchpad/lcp) holding house.snap and disk/tmbird03_even.st (scratchpad/ANCHORS.md).
Labelled pokes per state: every word in lcp_model.TICK, the event queue at $2c948 and the seed at $29b8. States are
biased so that each counter is often one tick from rolling over, else the rare branches would not be reached.
"""
import os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or HERE
while not os.path.exists(os.path.join(root, 'tools', 'rdis.py')):
    root = os.path.dirname(root)
WORK = os.environ.get('LCP_WORK') or os.path.join(root, 'scratchpad', 'lcp')
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(root, 'tools'))
import lcp_model as m  # noqa: E402
from stclient import StServer  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
rng = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 1)


def w16(v):
    return v - 0x10000 if v & 0x8000 else v


def near(lo, hi, edge, p=0.6):
    return edge if rng.random() < p else rng.randint(lo, hi)


def state():
    st = {
        'frame': rng.choice([rng.randrange(0, 4096, 8), rng.randrange(0, 4096)]) if rng.random() < 0.2 else rng.randrange(0, 4096, 8),
        'sec': near(0, 59, 59, 0.85), 'min': near(0, 59, 59, 0.5), 'hour': rng.randint(0, 23),
        'year': rng.choice([86, 87, 88]), 'month': rng.randint(0, 11),
        'thirst': rng.randint(0, 3), 'thirst_len': rng.randint(45, 75), 'thirst_left': near(1, 75, 1, 0.5),
        'hunger': rng.randint(0, 3), 'hunger_len': rng.randint(75, 120), 'hunger_left': near(1, 120, 1, 0.5),
        'pee': rng.randint(0, 1), 'pee_left': near(1, 40, 1, 0.5),
        'ill': rng.choice([0, 0, 1, 2, 3, 4, 5]), 'ill_left': near(1, 60, 1, 0.6), 'ill_dir': rng.choice([1, -1]),
        'happy': rng.randint(0, 2), 'happy_t0': rng.randint(6, 24), 'happy_t1': rng.randint(6, 24),
        'happy_t2': rng.randint(6, 12), 'happy_left': near(1, 24, 1, 0.6), 'happy_dir': rng.choice([1, -1]),
        'event_block': int(rng.random() < 0.15), 'away': int(rng.random() < 0.15), 'event_flag': 0,
        'lunch_done': rng.randint(0, 1), 'dinner_done': rng.randint(0, 1), 'wake_done': rng.randint(0, 1),
        'sleep_done': rng.randint(0, 1),
    }
    days = m.MONTH_DAYS[st['month']] + (1 if st['month'] == 1 and st['year'] % 4 == 0 else 0)
    st['mday'] = near(0, days - 1, days - 1, 0.5)
    n = rng.choice([0, 0, 1, 3, 9, 10])
    st['evq'] = [rng.choice([0x1c, 0x1d, 0x1f, 0x21]) for _ in range(n)] + [-1] * (10 - n)
    st['seed'] = rng.randrange(1, 1 << 32)
    if rng.random() < 0.3:                       # a seed whose rnd(0,100) wins the 2-in-101 house-event roll
        while m.rnd(st['seed'], 0, 100)[1] >= 2:
            st['seed'] = rng.randrange(1, 1 << 32)
    if rng.random() < 0.15:                      # the last frame of a day, month or year (Februaries over-sampled)
        st.update(frame=rng.randrange(0, 4096, 8), sec=59, min=59, hour=23, month=rng.choice([1, 1, 11, rng.randint(0, 11)]))
        days = m.MONTH_DAYS[st['month']] + (1 if st['month'] == 1 and st['year'] % 4 == 0 else 0)
        st['mday'] = rng.choice([days - 1, 27, 28]) if st['month'] == 1 else days - 1
    return st


s = StServer(root)
s('load', snapshot=os.path.join(WORK, 'house.snap'), disk=os.path.join(WORK, 'disk', 'tmbird03_even.st'))
base = s('fork')['id']
VARIANTS = ['true'] + m.TICK_BROKEN
score = {v: 0 for v in VARIANTS}
seen = {k: 0 for k in ('second', 'minute', 'hour', 'day', 'month', 'year', 'leap_feb', 'thirst_up', 'starve',
                       'ill_step', 'ill_cured', 'pee', 'roll', 'event', 'happy_step')}
for i in range(N):
    s('restore', id=base)
    st = state()
    for k, a in m.TICK.items():
        s('poke', addr=a, width=2, value=st[k] & 0xffff)
    for j, e in enumerate(st['evq']):
        s('poke', addr=m.EVQ + 2 * j, width=2, value=e & 0xffff)
    s('poke', addr=m.SEED, width=4, value=st['seed'])
    s.call(0x24648, max_steps=200000)
    got = {k: w16(int.from_bytes(s.read(a, 2), 'big')) for k, a in m.TICK.items()}
    b = s.read(m.EVQ, 20)
    got['evq'] = [w16(int.from_bytes(b[2 * j:2 * j + 2], 'big')) for j in range(10)]
    got['seed'] = int.from_bytes(s.read(m.SEED, 4), 'big')
    exp = m.needs_tick(st)
    # coverage of the branches the true model took
    if exp['sec'] != st['sec']: seen['second'] += 1
    if exp['sec'] == 0 and st['sec'] == 59: seen['minute'] += 1
    if exp['hour'] != st['hour']: seen['hour'] += 1
    if exp['mday'] != st['mday']: seen['day'] += 1
    if exp['month'] != st['month']: seen['month'] += 1
    if exp['year'] != st['year']: seen['year'] += 1
    if exp['month'] != st['month'] and st['month'] == 1 and st['year'] % 4 == 0: seen['leap_feb'] += 1
    if exp['thirst'] > st['thirst'] or exp['hunger'] > st['hunger']: seen['thirst_up'] += 1
    if any(st[n] == 3 and st[l] == 1 for n, l in (('thirst', 'thirst_left'), ('hunger', 'hunger_left'))) and exp['sec'] == 0 and st['sec'] == 59: seen['starve'] += 1
    if exp['ill'] != st['ill'] and st['ill'] > 0: seen['ill_step'] += 1
    if exp['ill'] == 0 and st['ill'] > 0: seen['ill_cured'] += 1
    if exp['pee'] and not st['pee']: seen['pee'] += 1
    if exp['seed'] != st['seed']: seen['roll'] += 1
    if exp['event_flag']: seen['event'] += 1
    if exp['happy'] != st['happy']: seen['happy_step'] += 1
    for v in VARIANTS:
        e = exp if v == 'true' else m.needs_tick(st, v)
        if all(e[k] == got[k] for k in got):
            score[v] += 1
        elif v == 'true':
            print('MISMATCH', {k: (st.get(k), e[k], got[k]) for k in got if e[k] != got[k]})
s.close()
print(f'states {N}; branches reached: {seen}')
for v in VARIANTS:
    tag = '' if v == 'true' else ('  control FAILS (good)' if score[v] < score['true'] else '  control PASSES (corpus too weak)')
    print(f'{v:22s} {score[v]}/{N}{tag}')
