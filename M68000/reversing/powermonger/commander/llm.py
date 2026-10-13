"""llm.py: the LLM commander (commander README plan step 4), a policy for loop.py (decide(obs, clock) -> act.from_json
action dicts, the interface of loop.Scripted).

    from llm import LLM, ClaudeCLI, Replay, Stub
    cmdr = LLM(side, mp, backend=ClaudeCLI('sonnet'), logdir=work / 'llm', every=20e6)
    llm.py selftest                       offline: the parse/validate path against rand1 with the stub backend
    llm.py prompt <snap> [side]           print the prompt for one observation

Prompt = prompt_system.txt (the rules digest, written from strategy.md / economy.md / the commander README order table)
+ a compact JSON observation (observe.py fields only; reachability from astar's land components).
Response = one JSON object {"orders":[{group, order, x, y | posture | to_group}], "retire", "why"}; validated against
SCHEMA and legality (below); an invalid order is dropped with its reason, an unparsable reply gives no orders.

Log: <logdir>/llm.jsonl, one record per decision {clock, step, prompt_hash, response_hash, backend, latency_s, cost_usd,
parse, valid, invalid:[{order, why}], actions}; the texts in <logdir>/prompts/<hash>.txt and responses/<hash>.txt.
Replay(logdir) answers a prompt from that log by its hash without calling the model, so a whole run re-decides
identically (the prompt depends only on the observation and on this policy's own order history).
"""
import hashlib, json, os, re, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ['M68000_ROOT']) if os.environ.get('M68000_ROOT') else \
    next(d for d in HERE.parents if (d / 'tools' / 'rdis.py').exists())
CMD = ROOT / 'reversing' / 'powermonger' / 'commander'
sys.path.insert(0, str(CMD))

SYSTEM = (HERE / 'prompt_system.txt').read_text()
WORK = ROOT / os.environ.get('CMD_WORK', 'scratchpad/cmd1')
STEPS_PER_TICK = 177_000          # README "Forecaster": one sim pass is about 177k steps

# order name -> (type byte, argument kind). Type bytes: commander README order table / strategy.md "What each order does".
ORDERS = {
    'go_to': (0x02, 'cell'), 'get_food': (0x06, 'own'), 'get_men': (0x08, 'own'), 'home': (0x0a, 'none'),
    'attack': (0x0c, 'enemy'), 'invent': (0x0e, 'own'), 'equip': (0x10, 'own'), 'drop_food': (0x12, 'none'),
    'dismiss': (0x14, 'none'), 'posture': (0x16, 'posture'), 'supply': (0x1a, 'cell'), 'trade': (0x1c, 'town'),
    'alliance': (0x1e, 'enemy'), 'spy': (0x20, 'enemy'), 'transfer': (0x04, 'transfer'),
}
RETIRE = 0x2e

SCHEMA = {
    'type': 'object', 'required': ['orders'],
    'properties': {
        'orders': {'type': 'array', 'maxItems': 6, 'items': {
            'type': 'object', 'required': ['group', 'order'],
            'properties': {'group': {'type': 'integer', 'minimum': 0, 'maximum': 5},
                           'order': {'enum': sorted(ORDERS)},
                           'x': {'type': 'integer', 'minimum': 0, 'maximum': 63},
                           'y': {'type': 'integer', 'minimum': 0, 'maximum': 127},
                           'posture': {'enum': [2, 3, 4]},
                           'to_group': {'type': 'integer', 'minimum': 0, 'maximum': 5}}}},
        'retire': {'type': 'boolean'}, 'why': {'type': 'string'}}}


def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()[:16]


# ------------------------------------------------------------------ backends
class ClaudeCLI:
    """Claude Code headless: `claude -p --output-format json --model M --tools "" --system-prompt S
    --no-session-persistence`, prompt on stdin, run from an empty dir so no project CLAUDE.md is discovered."""
    name = 'claude-cli'

    def __init__(self, model='sonnet', exe=None, cwd=None, max_usd='1.00'):
        self.model, self.max_usd = model, max_usd
        self.exe = exe or os.environ.get('CLAUDE_EXE') or str(Path.home() / '.claude/local/claude')
        self.cwd = Path(cwd or WORK / 'llm_cli_cwd'); self.cwd.mkdir(parents=True, exist_ok=True)

    def __call__(self, system, user):
        cmd = [self.exe, '-p', '--output-format', 'json', '--model', self.model, '--tools', '',
               '--system-prompt', system, '--no-session-persistence', '--strict-mcp-config',
               '--max-budget-usd', self.max_usd]
        t = time.time()
        p = subprocess.run(cmd, input=user, capture_output=True, text=True, cwd=self.cwd, timeout=600)
        dt = time.time() - t
        meta = dict(latency_s=round(dt, 2), rc=p.returncode)
        self.last_raw = p.stdout
        try:
            j = json.loads(p.stdout)
        except ValueError:
            return '', dict(meta, error='cli output not json: ' + (p.stdout + p.stderr)[:300])
        if isinstance(j, list):                    # this CLI version prints the event list; the reply is the result event
            j = next((e for e in reversed(j) if isinstance(e, dict) and e.get('type') == 'result'), {})
        meta.update(cost_usd=j.get('total_cost_usd'), is_error=j.get('is_error'),
                    duration_api_ms=j.get('duration_api_ms'), model_usage=list((j.get('modelUsage') or {}).keys()))
        return j.get('result') or '', meta


class Replay:
    """Answers from a previous run's llm log by prompt hash; a miss is an error (the run diverged)."""
    name = 'replay'

    def __init__(self, logdir):
        self.dir = Path(logdir)
        self.map = {}
        for l in (self.dir / 'llm.jsonl').read_text().splitlines():
            r = json.loads(l)
            self.map[r['prompt_hash']] = r['response_hash']

    def __call__(self, system, user):
        h = sha(system + '\n' + user)
        if h not in self.map:
            raise KeyError(f'replay miss: prompt {h} not in {self.dir}')
        return (self.dir / 'responses' / f'{self.map[h]}.txt').read_text(), dict(latency_s=0.0)


class Stub:
    """Offline backend: fn(system, user) -> text, or a fixed list of replies served in order."""
    name = 'stub'

    def __init__(self, replies):
        self.replies = replies if callable(replies) else iter(replies)

    def __call__(self, system, user):
        return (self.replies(system, user) if callable(self.replies) else next(self.replies)), dict(latency_s=0.0)


# ------------------------------------------------------------------ observation
def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def eat_period(R, side):
    # $580a6[side].word0: ticks between meals ($3e06 "The army eats", strategy.md "$d322 + $3e06")
    return (R[0x580a6 + 0x20 * side] << 8) | R[0x580a6 + 0x20 * side + 1] if R is not None else None


class World:
    """The facts the prompt and the validator share, built from one observe.py dict."""

    def __init__(self, obs, side, mp=None, comps=None, R=None):
        self.obs, self.side = obs, side
        S = obs['sides'][side]
        self.lords = [l for s in obs['sides'] for l in obs['sides'][s]['lords']] + obs.get('other_lords', [])
        self.by_cell = {}
        for l in self.lords:
            self.by_cell.setdefault(tuple(l['cell']), []).append(l)
        self.groups = {g['k']: g for g in S['groups']}
        self.mp, self.comps = mp, comps
        self.eat = eat_period(R, side)

    def gcomp(self, g):
        if self.mp is None or 'lead_obj' not in g:
            return None
        return self.mp.component(g['lead_obj']['x'], g['lead_obj']['y'])

    def reach(self, g, cell):
        """True / False from astar's land components; None when unknown (no map)."""
        if self.mp is None:
            return None
        a = self.gcomp(g)
        if a is None:                              # lead on a wet triangle (afloat or on a shore): unknown
            return None
        return a == self.ccomp(cell)

    def ccomp(self, cell):
        # the order's target point is the cell centre (README "The target cell is the cell centre", gate_cellpt 16/16),
        # which $1648e samples as triangle B: its component, None when that point is water
        return self.mp.component(cell[0] * 256 + 128, cell[1] * 256 + 128)

    def land(self, cell):
        return None if self.mp is None else self.ccomp(cell) is not None

    def orderable(self, g):
        return g is not None and g['alive'] and 'lead_obj' in g and g['raw_w4'] == 0


def force(obs, s):
    return obs['sides'][s]['totals']['men_home'] + obs['sides'][s]['totals']['group_men']


def compact_obs(W, history, every):
    obs, side = W.obs, W.side
    forces = {s: force(obs, s) for s in obs['sides']}
    E = sum(v for s, v in forces.items() if s != side) + 1
    mine = forces[side]
    out = dict(you=side, local_side=obs['local_side'], may_retire=side == obs['local_side'],
               force=forces, your_ratio=min(4, (2 * mine + E // 4) // E),
               eat_period_ticks=W.eat, ticks_per_decision=round(every / STEPS_PER_TICK))
    gs = []
    for k, g in sorted(W.groups.items()):
        if not g['alive']:
            continue
        e = dict(group=k, men=g['men'], food=g['food'], state=g['state_name'] or g['state'],
                 posture=g['posture'], cell=g['lead_obj']['cell'] if 'lead_obj' in g else None,
                 busy=g['raw_w4'] != 0)
        carried = {n: v for n, v in g['carrying'].items() if v}
        if carried:
            e['carrying'] = carried
        if k in history:
            e['your_last_order'] = history[k]
        gs.append(e)
    out['your_groups'] = gs
    live = [g for g in W.groups.values() if W.orderable(g)]
    ls = []
    for l in sorted(W.lords, key=lambda l: (l['side'], l['idx'])):
        e = dict(lord=l['idx'], side=l['side'], kind=l['kind_name'], cell=l['cell'], men_home=l['men_home'],
                 food=l['food'], loyalty=l['loyalty'])
        goods = {n: v for n, v in l['goods'].items() if v}
        if goods:
            e['goods'] = goods
        mine = [s for s in obs['sides'].get(l['side'], {}).get('settlements', []) if s['lord'] == l['idx']]
        e['settlement_men'] = sum(s['residents'] for s in mine)   # observe.py residents: unit-chain length, not UI-checked
        if any(s['kind_name'] == 'WorkShop' for s in mine):
            e['workshop'] = True
        if live:
            e['dist'] = {g['k']: cheb(g['lead_obj']['cell'], l['cell']) for g in live}
            if W.mp is not None:
                rb = [g['k'] for g in live if not g['carrying'].get('boat') and W.reach(g, l['cell']) is not False]
                if any(not g['carrying'].get('boat') for g in live):
                    e['reachable_by'] = rb
        ls.append(e)
    # two lists, not one with a side field: with one list the model attacked its own lords (v2_probe, 2 of 2 orders)
    out['your_lords'] = [e for e in ls if e['side'] == side]
    out['enemy_lords'] = [e for e in ls if e['side'] != side]
    out['enemy_groups'] = [dict(side=int(s), group=g['k'], men=g['men'], state=g['state_name'] or g['state'],
                                cell=g['lead_obj']['cell'])
                           for s, v in obs['sides'].items() if int(s) != side
                           for g in v['groups'] if g['alive'] and 'lead_obj' in g]
    return out


def build_prompt(W, history, every):
    o = compact_obs(W, history, every)
    user = ('Observation (JSON):\n' + json.dumps(o, separators=(',', ':')) +
            '\n\nReply with the JSON object only.')
    return SYSTEM, user


# ------------------------------------------------------------------ parse and validate
def parse(text):
    """Strict JSON object. Returns (obj, note) or (None, reason). Code fences are tolerated and noted."""
    t = text.strip()
    note = 'ok'
    m = re.fullmatch(r'```(?:json)?\s*(.*?)\s*```', t, re.S)
    if m:
        t, note = m.group(1), 'fenced'
    try:
        o = json.loads(t)
    except ValueError as e:
        return None, f'not json: {e}'
    if not isinstance(o, dict):
        return None, 'not an object'
    return o, note


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def validate(o, W):
    """-> (actions, invalid). actions are act.from_json dicts; invalid lists {order, why}."""
    acts, bad, seen = [], [], set()
    side = W.side
    orders = o.get('orders')
    if not isinstance(orders, list):
        return [], [dict(order=orders, why='orders is not a list')]
    for od in orders:
        why = None
        if not isinstance(od, dict):
            bad.append(dict(order=od, why='not an object')); continue
        k, name = od.get('group'), od.get('order')
        g = W.groups.get(k) if _int(k) else None
        if not _int(k) or not 0 <= k <= 5:
            why = 'group not an integer 0..5'
        elif name not in ORDERS:
            why = f'unknown order {name!r}'
        elif k in seen:
            why = 'second order for the group'
        elif g is None or not g['alive']:
            why = 'group not alive'
        elif 'lead_obj' not in g:
            why = 'group has no lead'
        elif g['raw_w4'] != 0:
            why = 'group busy (order in transit)'
        if why:
            bad.append(dict(order=od, why=why)); continue
        typ, kind = ORDERS[name]
        x = y = 0
        if kind in ('cell', 'own', 'enemy', 'town'):
            x, y = od.get('x'), od.get('y')
            if not (_int(x) and _int(y) and 0 <= x <= 63 and 0 <= y <= 127):
                why = 'cell out of range or missing'
            else:
                here = W.by_cell.get((x, y), [])
                if kind == 'own' and not any(l['side'] == side for l in here):
                    why = 'not the cell of an own lord'
                elif kind == 'enemy' and not any(l['side'] != side for l in here):
                    why = 'not the cell of an enemy lord'
                elif kind == 'town' and not here:
                    why = 'not the cell of a lord'
                elif kind == 'cell' and W.land((x, y)) is False:
                    why = 'water cell'
                elif W.reach(g, (x, y)) is False and not g['carrying'].get('boat'):
                    why = 'not reachable on foot (and no boats)'
                elif name == 'attack' and g['men'] <= 0:
                    why = 'group has no men'
        elif kind == 'posture':
            p = od.get('posture')
            if p not in (2, 3, 4):
                why = 'posture not 2..4'
            else:
                x, y = 0, p                     # README: posture `$16`, word = posture
        elif kind == 'transfer':
            t = od.get('to_group')
            if not _int(t) or t == k or t not in W.groups or not W.groups[t]['alive']:
                why = 'to_group not another live group'
            else:
                x, y = 2 * k, 2 * t             # README: transfer `$04`, from 2k, to 2k
        if why:
            bad.append(dict(order=od, why=why)); continue
        seen.add(k)
        acts.append(dict(side=side, type=typ, x=x, y=y, group=k))
    if o.get('retire') is True:
        if side == W.obs['local_side']:
            acts.append(dict(side=side, type=RETIRE, x=0, y=0))
        else:
            bad.append(dict(order='retire', why='not the local side'))
    return acts, bad


# ------------------------------------------------------------------ the policy
class LLM:
    def __init__(self, side, mp=None, backend=None, logdir=None, every=20e6, ram_reader=None):
        self.side, self.mp, self.backend, self.every = side, mp, backend, every
        self.comps = mp.cell_components() if mp else None
        self.history = {}                          # k -> {order, cell, at_decision}
        self.n = 0
        self.ram = ram_reader                      # () -> current RAM image, for the eat period
        self.dir = Path(logdir) if logdir else None
        if self.dir:
            for d in ('prompts', 'responses'):
                (self.dir / d).mkdir(parents=True, exist_ok=True)
            self.log = open(self.dir / 'llm.jsonl', 'a')
        self.last = None

    def decide(self, obs, clock):
        W = World(obs, self.side, self.mp, self.comps, self.ram() if self.ram else None)
        system, user = build_prompt(W, self.history, self.every)
        ph = sha(system + '\n' + user)
        rec = dict(decision=self.n, step=clock, clock=obs['clock'], prompt_hash=ph, backend=self.backend.name)
        try:
            text, meta = self.backend(system, user)
        except Exception as e:                     # a backend failure is a no-order decision, logged
            text, meta = '', dict(error=f'{type(e).__name__}: {e}')
        rh = sha(text)
        rec.update(response_hash=rh, **meta)
        o, note = parse(text)
        if o is None:
            acts, bad = [], [dict(order=None, why=note)]
        else:
            acts, bad = validate(o, W)
            rec['why'] = o.get('why')
        rec.update(parse=note if o is not None else 'fail', n_orders=len(o.get('orders', []) if isinstance(o, dict) and
                                                                         isinstance(o.get('orders'), list) else []),
                   valid=len(acts), invalid=bad, actions=acts)
        if self.dir:
            (self.dir / 'prompts' / f'{ph}.txt').write_text(system + '\n' + user)
            (self.dir / 'responses' / f'{rh}.txt').write_text(text)
            raw = getattr(self.backend, 'last_raw', None)
            if raw:
                (self.dir / 'responses' / f'{ph}.cli.json').write_text(raw)
            self.log.write(json.dumps(rec, separators=(',', ':')) + '\n'); self.log.flush()
        for a in acts:
            if 'group' in a:
                name = next(n for n, (t, _) in ORDERS.items() if t == a['type'])
                self.history[a['group']] = dict(order=name, x=a['x'], y=a['y'], at_decision=self.n)
        self.n += 1
        self.last = rec
        return acts


# ------------------------------------------------------------------ CLI
def _selftest():
    from observe import observe, load
    from astar import Map
    R = load(ROOT / 'scratchpad/pm142/rand1.snap')
    obs = observe(R)
    mp = Map(R)
    side = 3
    W = World(obs, side, mp, mp.cell_components(), R)
    sysp, user = build_prompt(W, {}, 20e6)
    ok = []
    chk = lambda name, cond: (ok.append(bool(cond)), print(('PASS ' if cond else 'FAIL ') + name))

    def run(text):
        o, note = parse(text)
        return (None, note) if o is None else validate(o, W)

    own = obs['sides'][side]['lords']
    foe = obs['sides'][4]['lords'][0]
    a, b = run(json.dumps({'orders': [{'group': 1, 'order': 'attack', 'x': foe['cell'][0], 'y': foe['cell'][1]}]}))
    chk('attack enemy lord', len(a) == 1 and a[0]['type'] == 0x0c and not b)
    a, b = run(json.dumps({'orders': [{'group': 1, 'order': 'attack', 'x': own[0]['cell'][0], 'y': own[0]['cell'][1]}]}))
    chk('attack own lord rejected', not a and 'enemy' in b[0]['why'])
    a, b = run(json.dumps({'orders': [{'group': 0, 'order': 'get_men', 'x': 6, 'y': 6}]}))
    chk('get_men off-town rejected', not a and 'own lord' in b[0]['why'])
    a, b = run(json.dumps({'orders': [{'group': 4, 'order': 'home'}]}))
    chk('dead group rejected', not a and 'alive' in b[0]['why'])
    a, b = run(json.dumps({'orders': [{'group': 0, 'order': 'go_to', 'x': 99, 'y': 3}]}))
    chk('x out of range rejected', not a and 'range' in b[0]['why'])
    a, b = run(json.dumps({'orders': [{'group': 0, 'order': 'posture', 'posture': 2},
                                      {'group': 0, 'order': 'home'}]}))
    chk('posture encodes y=2, duplicate rejected', len(a) == 1 and a[0]['y'] == 2 and 'second' in b[0]['why'])
    a, b = run(json.dumps({'orders': [{'group': 1, 'order': 'transfer', 'to_group': 0}]}))
    chk('transfer encodes 2k,2t', a == [dict(side=3, type=4, x=2, y=0, group=1)])
    a, b = run('```json\n{"orders":[]}\n```')
    chk('fenced empty accepted', a == [] and b == [])
    a, b = run('I would attack lord 4.')
    chk('prose -> no orders', a is None)
    a, b = run(json.dumps({'orders': [], 'retire': True}))
    chk('retire refused off the local side', not a and b[0]['order'] == 'retire')
    a, b = run(json.dumps({'orders': [{'group': 1, 'order': 'fly', 'x': 1, 'y': 1}]}))
    chk('unknown order rejected', not a and 'unknown' in b[0]['why'])
    # water / unreachable: find a water cell and a lord unreachable from group 1 if any
    water = next(((x, y) for y in range(128) for x in range(64) if W.land((x, y)) is False), None)
    if water:
        a, b = run(json.dumps({'orders': [{'group': 1, 'order': 'go_to', 'x': water[0], 'y': water[1]}]}))
        chk(f'go_to water {water} rejected', not a and 'water' in b[0]['why'])
    g1 = W.groups[1]
    unr = next((l for l in W.lords if l['side'] != side and W.reach(g1, l['cell']) is False), None)
    if unr:
        a, b = run(json.dumps({'orders': [{'group': 1, 'order': 'attack', 'x': unr['cell'][0], 'y': unr['cell'][1]}]}))
        chk(f'attack unreachable lord {unr["idx"]} rejected', not a and 'reachable' in b[0]['why'])
    # the policy end to end with the stub, logging, then the replay backend reproduces it
    import tempfile, shutil
    d = Path((WORK.mkdir(parents=True, exist_ok=True), tempfile.mkdtemp(dir=WORK))[1])
    reply = json.dumps({'orders': [{'group': 1, 'order': 'attack', 'x': foe['cell'][0], 'y': foe['cell'][1]}],
                        'why': 'stub'})
    p1 = LLM(side, mp, Stub([reply, 'garbage']), d / 'a', ram_reader=lambda: R)
    r1 = [p1.decide(obs, 0), p1.decide(obs, 20_000_000)]
    p2 = LLM(side, mp, Replay(d / 'a'), d / 'b', ram_reader=lambda: R)
    r2 = [p2.decide(obs, 0), p2.decide(obs, 20_000_000)]
    chk('stub run: attack then no-order on garbage', len(r1[0]) == 1 and r1[1] == [])
    chk('second prompt carries the order history', p1.last['prompt_hash'] != json.loads(
        (d / 'a' / 'llm.jsonl').read_text().splitlines()[0])['prompt_hash'])
    chk('replay backend reproduces the decisions', r1 == r2)
    shutil.rmtree(d)
    print(f'{sum(ok)}/{len(ok)} pass; prompt {len(sysp) + len(user)} chars')
    return 0 if all(ok) else 1


if __name__ == '__main__':
    if sys.argv[1:2] == ['selftest']:
        sys.exit(_selftest())
    if sys.argv[1:2] == ['prompt']:
        from observe import observe, load
        from astar import Map
        R = load(sys.argv[2]); side = int(sys.argv[3]) if len(sys.argv) > 3 else 3
        mp = Map(R)
        s, u = build_prompt(World(observe(R), side, mp, mp.cell_components(), R), {}, 20e6)
        print(s); print(u)
