"""Gate for the top-level chooser `$16f50` (README, "The behaviour scheduler"): runs the game's own routine in
`stserver` on poked states and checks which branch it takes, the action it hands to `$172a6`, and the player-query
queue it leaves, against `lcp_model.toplevel`.

usage: gate_toplevel.py [n_states] [seed]
Needs $LCP_WORK (default <root>/scratchpad/lcp) holding house.snap and disk/tmbird03_even.st (scratchpad/ANCHORS.md).
Labelled pokes per state: every word in lcp_model.TOP plus the ten-entry queue at $3e272 (priority) / $40966
(action). Each call stops before any action runs: at `$27270` (house event dequeued), `$172a6` (action started,
read from `$2ae0c`), `$2310a` (the "agree" animation before a play/piano query) or `$1747e` (secondary desire).
The 'drop_decrements' control is the queue as one would expect it to work (a dropped low-priority query frees its
slot); it must score below the true model, which is the leak.
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

N = int(sys.argv[1]) if len(sys.argv) > 1 else 600
rng = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
STOPS = {0x27270: 'event', 0x172a6: 'start', 0x2310a: 'agree', 0x1747e: 'secondary'}
ACTS = [0x0, 0x2, 0x5, 0x6, 0x7, 0x8, 0xd, 0xe, 0x10, 0x11, 0x12, 0x14, 0x18, 0x1a, 0x1b, 0x1f, 0x22, 0x24]


def w16(v):
    return v - 0x10000 if v & 0x8000 else v


s = StServer(root)
s('load', snapshot=os.path.join(WORK, 'house.snap'), disk=os.path.join(WORK, 'disk', 'tmbird03_even.st'))
base = s('fork')['id']
VARIANTS = ['true', 'drop_decrements', 'ill_ignores_water', 'eat_repeats', 'execute_at_7']
score = {v: 0 for v in VARIANTS}
labels = {}
for i in range(N):
    s('restore', id=base)
    h = rng.randrange(24)
    st = {
        'event_head': rng.choice([-1] * 9 + [0]), 'alarm': int(rng.random() < 0.05), 'pee': int(rng.random() < 0.08),
        'ill': rng.choice([0, 0, 0, 1, 2]), 'thirst': rng.choice([0, 0, 1, 2, 3]), 'water': rng.choice([0, 7]),
        'hunger': rng.choice([0, 0, 1, 2, 3]), 'bits': rng.randrange(5) << 9, 'last': rng.choice(ACTS + [0x12] * 3),
        'hour': h, 'lunch_done': rng.choice([0, 1]), 'dinner_done': rng.choice([0, 1]),
        'wake_done': rng.choice([0, 1]), 'sleep_done': rng.choice([0, 1]),
        'lunch': rng.choice([h, 12]), 'dinner': rng.choice([h, 18]), 'wake': rng.choice([h, 7]),
        'sleep': rng.choice([h, 23]), 'qcount': rng.choice([0, 0, 1, 2, 3, 10]),
        'qprio': [rng.randrange(13) for _ in range(10)], 'qact': [rng.choice(ACTS) for _ in range(10)],
    }
    if rng.random() < 0.5:   # quiet: no need or event pending, so the query queue and the secondary desire decide
        st.update(event_head=-1, alarm=0, pee=0, thirst=0, hunger=0, lunch_done=1, dinner_done=1, wake_done=1,
                  sleep_done=1, qcount=rng.choice([1, 1, 2, 3, 10]))
    for k, addr in m.TOP.items():
        s('poke', addr=addr, width=2, value=st[k] & 0xffff)
    for j in range(10):
        s('poke', addr=m.QPRIO + 2 * j, width=2, value=st['qprio'][j])
        s('poke', addr=m.QACT + 2 * j, width=2, value=st['qact'][j])
    st['seed'] = int.from_bytes(s.read(m.SEED, 4), 'big')
    r = s.call(0x16f50, stops=list(STOPS))
    pc = int(r['pc'].lstrip('$'), 16)
    label = STOPS.get(pc, f'pc ${pc:x}')
    act = w16(int.from_bytes(s.read(0x2ae0c, 2), 'big')) if label in ('start', 'agree') else None
    q = w16(int.from_bytes(s.read(m.TOP['qcount'], 2), 'big'))
    qp = [w16(int.from_bytes(s.read(m.QPRIO + 2 * j, 2), 'big')) for j in range(10)]
    qa = [w16(int.from_bytes(s.read(m.QACT + 2 * j, 2), 'big')) for j in range(10)]
    got = (label, act, q, qp, qa)
    labels[(label, act)] = labels.get((label, act), 0) + 1
    for v in VARIANTS:
        if tuple(m.toplevel(st, v)) == got:
            score[v] += 1
    if tuple(m.toplevel(st, 'true')) != got:
        print('MISMATCH', i, {k: st[k] for k in st if k not in ('qprio', 'qact')}, 'got', got[:3],
              'model', m.toplevel(st)[:3])
s.close()
print(f'states {N}; branches seen (label, action): '
      + ', '.join(f'{lab}{"" if a is None else f" ${a:x}"} {n}' for (lab, a), n in sorted(labels.items(), key=str)))
for v in VARIANTS:
    tag = '' if v == 'true' else ('  control FAILS (good)' if score[v] < score['true'] else '  control PASSES (corpus too weak)')
    print(f'{v:16s} {score[v]}/{N}{tag}')
