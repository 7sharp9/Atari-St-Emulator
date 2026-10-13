"""loop.py: the commander's decision loop with replay logging (commander README plan step 3).

    loop.py <work> [--snap S] [--budget N] [--every N] [--side K] [--policy scripted|none|llm] [--move] [--no-take]
            [--gap N] [--read m|snap] [--replay LOG] [--backend cli|replay:<llm logdir>] [--model sonnet]

Policy llm (llm.py) logs every prompt and reply under <work>/llm/.

One persistent emulator (`resume <snap> repl`) is driven over stdin/stdout pipes; nothing is restarted between
decisions, so the run is one uninterrupted emulation and the pokes always see current RAM.

Protocol (Program.fs `runRepl`, read, not modified): the REPL reads one line per command and falls out of the loop
(the process exits) on EOF, `q`, an empty line or any unknown command. `w` and `s` print nothing; `m <a> <n>` prints
exactly one line of n hex bytes; `snap` one "Snapshot written" line; `bp <a> <n>` prints a "--- breakpoint ... hit"
or "--- gave up after <n> step(s)" line and then the register block, which ends with a `PC: ...` line and a
"-------------" line. All of it goes through Diag.result to the real stdout, which .NET autoflushes, so a reader
syncs on each reply. Stepping uses `bp d2c8 <n>` instead of `s <n>`: RunToBreakpoint runs exactly n Step() calls
when $d2c8 (the end-of-land verdict, strategy.md "How a land ends") is not reached, and stops on its entry when it
is, so a land end is caught at its step and every chunk gets a sync line.

The commander (scripted baseline, Scripted.decide(obs, clock) -> act.from_json action dicts) plays one side whose
command slot the loop takes at step 0 (slot state 2: `$6522` stops writing it, gate_inject.sh). One decision per
--every steps. Orders of one decision are applied --gap steps apart (one executor pass `$6a3a` runs per sim tick,
about 170k steps; the gap lets each order be consumed before the next is written into the same slot).

Log (<work>/decisions.jsonl): a start record, one record per decision {step, clock, side, obs_hash, totals,
actions}, one `applied` record per poke batch {step, actions, lines (the REPL `w` lines)} and an end record (reason,
step, clock, ratio, per-side totals, final obs_hash). --replay LOG re-issues the logged `applied` actions at their
logged steps and observes at the logged decision steps without calling
decide, writing its own log in the same format; the final snapshot is <work>/final.snap.

Movement: orders are target-cell orders. A* (astar.Map.path) plugs in at Scripted.decide where tgt is chosen:
replace the single cell order by one `$02` go order per waypoint, re-issued at each arrival (README "Design").
An order cell (cx, cy) becomes the lead's target (cx*256+128, cy*256+128), the cell centre (gate_cellpt.py 16/16),
which astar's triangle rule samples as triangle B: snap each waypoint to its cell and prefer cells whose triangle B
is land, or the order target is water. An attack on a cell holding only a foreign man targets that man's position.
"""
import hashlib, json, os, struct, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ['M68000_ROOT']) if os.environ.get('M68000_ROOT') else \
    next(d for d in HERE.parents if (d / 'tools' / 'rdis.py').exists())
CMD = HERE if (HERE / 'observe.py').exists() else ROOT / 'reversing' / 'powermonger' / 'commander'
sys.path.insert(0, str(CMD))
from observe import observe, load          # noqa: E402
from act import from_json                  # noqa: E402

DLL = ROOT / 'bin/Debug/net8.0/M68000.dll'
DISK = 'scratchpad/powermonger.st'
D2C8 = 0xd2c8                              # end-of-land verdict (strategy.md "How a land ends")
# RAM regions observe.py reads: the clock long $2df72; lords $4e514 .. settlements .. groups $51538 .. objects
# $51b66 (lead offsets seen up to ~$2300) .. totals $57fba, ratio $57fce, slots $58016, acting words $58042.
REGIONS = [(0x2df70, 8), (0x4e500, 0x58130 - 0x4e500)]   # to $58130: the $580a6 blocks to side 4 (eat period word0)
RAMSIZE = 0x100000


class Emu:
    def __init__(self, snap, errpath):
        self.err = open(errpath, 'w')
        self.p = subprocess.Popen(['dotnet', 'exec', str(DLL), 'resume', str(snap), 'repl'], cwd=ROOT,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.err, text=True,
                                  bufsize=1, env=dict(os.environ, ATARI_NOTRACE='1'))
        l = self._line()
        assert l.startswith('--- state loaded'), l
        self.send(f'disk {DISK}')
        l = self._line()
        assert l.startswith('Disk A swapped'), l
        self.ram = bytearray(RAMSIZE)

    def _line(self):
        l = self.p.stdout.readline()
        if not l:
            raise EOFError(f'emulator exited (rc {self.p.poll()})')
        return l.rstrip('\n')

    def send(self, line):
        assert line.strip(), 'an empty line ends the REPL'
        self.p.stdin.write(line + '\n')
        self.p.stdin.flush()

    def mem(self, addr, n):
        self.send(f'm {addr:x} {n}')
        b = bytes.fromhex(self._line().replace(' ', ''))
        assert len(b) == n
        self.ram[addr:addr + n] = b
        return b

    def read(self, how, tmp):
        if how == 'snap':
            self.save(tmp)
            self.ram[:] = load(tmp)
        else:
            for a, n in REGIONS:
                self.mem(a, n)
        return self.ram

    def run(self, n):
        """n steps, stopping early on $d2c8: returns (steps run, hit)."""
        self.send(f'bp {D2C8:x} {n}')
        head = self._line()
        while True:
            l = self._line()
            if l.startswith('PC:'):
                self._line()
                break
        if head.startswith('--- breakpoint'):
            return int(head.split(' after ')[1].split()[0]), True
        assert head.startswith('--- gave up after'), head
        return int(head.split()[4]), False

    def poke(self, lines):
        for l in lines:
            self.send(l)

    def save(self, path):
        self.send(f'snap {path}')
        l = self._line()                      # SaveState's own "--- state saved to" line, then the REPL's
        if l.startswith('--- state saved'):
            l = self._line()
        assert l.startswith('Snapshot written'), l

    def close(self):
        try:
            self.send('q'); self.p.stdin.close()
        except Exception:
            pass
        self.p.wait(); self.err.close()


def obs_hash(obs):
    return hashlib.sha256(json.dumps(obs, sort_keys=True, separators=(',', ':')).encode()).hexdigest()[:16]


# ------------------------------------------------------------------ the scripted baseline
GET_FOOD, GET_MEN, ATTACK = 0x06, 0x08, 0x0c   # commander README order table
POSTURE, GET_EQUIP, INVENT = 0x16, 0x10, 0x0e     # commander README order table
FOLLOWUP = {0x0d: (GET_FOOD, 4), 2: (GET_MEN, 3), 3: (GET_EQUIP, 2), 0x0a: (INVENT, 3)}   # $67d0 {prev state: order,
                                                # posture}; $67d0's invent posture is (rng & 3) + 2, 3 here
LORD0, OBJ = 0x4e514, 0x51b66                   # lord records (32 bytes), object base (observe.py)
RETIRE = 0x2e                                   # strategy.md "How a land ends": $2e in the local side's slot -> $d2c8
GOTO = 0x02                                     # go to (move.py)
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
THREAT = 16                                     # rollout: an enemy group this many cells away (Chebyshev) offers a retreat
IDLE = (0, 1, 6)                                # state names (observe.STATE): none, Waiting, In Camp
MEN_LOW = 22                                    # $6522's own get-men arm: men < 22 (strategy.md "The AI as modern pseudocode")
STALE = 8                                       # decisions with no change of state or lead cell before re-ordering
FOOD_MIN = 20                                   # local side: an own lord's store worth a trip or a top-up
FOOD_CAP = 500                                  # local side: no top-up above this group food
FOOD_BITES = 40                                 # local side: fetch food below this many meals (men/8 + 1 each, $3f6a;
                                                # a 25-man captain ate one about every 5M steps on land 2, so ~200M)
WAIT = 20_000_000                               # steps an ordered group is left alone: an injected order reaches a
                                                # non-first group by pigeon ~9M steps later (README) and sets no
                                                # pending word 4 (observed in this loop's first runs), so without
                                                # this the same order is re-sent every decision


class Scripted:
    """Deterministic baseline for one side. For each live group with no pending pigeon (word 4, as $6564 skips)
    and idle (or stale): a camped group 20 ticks after it made camp follows $6762's chain at its target lord when that
    lord is now its own (after a fight with a lord: get food, posture 4; after get food: get men, posture 3; after get
    men: equip, posture 2; after equip: invent); else men < 22 (0 included, as $6564 offers it to arm 1) -> posture 2
    and get men at the nearest reachable own lord with men at home > 1; else
    food short of the trip ($68ee's cost: (d/2)*((men-4)/8+1) + d/2) -> get food at the nearest own lord with food;
    else posture 4 and attack the nearest reachable enemy lord with men at home < men - 4 ($6522's attack arm test).
    Postures are $16 orders sent just before the order, as $6638 / $65c8 stamp them: at posture 4 every kill the
    group makes is a rout ($5590), so a conquered lord's captain survives to defect and found a new group ($5c2c,
    $25d6); at posture 2 the men are killed, no group is ever made, and get men takes the whole garrison.
    Playing the local side, before get men it provisions: a group within a cell of an own lord holding FOOD_MIN food
    takes it while under FOOD_CAP, and a group under FOOD_BITES meals fetches it from the nearest such lord; every
    local get food goes at posture 2, which moves the lord's whole store ($150f2, food >> 0) where posture 4 moves a
    quarter. Of $6762's chain the local side keeps get food after a fight and get men at a lord with men at home: a
    top-up at home otherwise led the captain through get men, equip and invent for 80M steps before its first attack.
    Only the local captain's loss ends a land, and on land 2 it starved with 327 food in its own lords'
    stores that side 2 then conquered. Also on the local side it posts retire $2e as soon as the observed ratio $57fce is 4 (a win), or when the side
    has no lord and no man left (a loss the game does not end by itself)."""

    def __init__(self, side, mp=None, move=False):
        self.side, self.mp, self.move = side, mp, move
        self.movers = {}         # --move: k -> move.Mover in flight
        self.events = []         # Mover events since the last decision (logged by the loop)
        self.seen = {}           # k -> ((state, lead cell), decisions unchanged)
        self.ordered = {}        # k -> step of the last order
        self.comps = mp.cell_components() if mp else None

    def _reach(self, g, cell):
        if self.mp is None:
            return True
        a = self.mp.component(g['lead_obj']['x'], g['lead_obj']['y'])
        b = self.comps[cell[1]][cell[0]]
        return a is not None and a == b

    def _move(self, k, mv, obs, R, clock):
        n0 = len(mv.events)
        acts = mv.tick(obs, R, clock)
        self.events += [[k] + list(e) for e in mv.events[n0:]]
        if mv.done or mv.failed:
            del self.movers[k]
            self.ordered[k] = clock
            self.seen[k] = (None, 0)
            if mv.failed:
                self.events.append([k, clock, 'failed', mv.failed])
        return acts

    def decide(self, obs, clock, R=None):
        self.events = []
        S = obs['sides'][self.side] if self.side in obs['sides'] else obs['sides'][str(self.side)]
        allside = obs['sides']
        own = [l for l in S['lords']]
        enemy = [l for s, v in allside.items() if int(s) != self.side for l in v['lords']]
        lords = {l['idx']: (int(s), l) for s, v in allside.items() for l in v['lords']}
        tick = obs['clock'] >> 16               # observe's clock is the long at $2df72: the tick in its high word
        out = []
        local = self.side == obs['local_side']
        if local:
            t = S['totals']
            # the scale is full ($57fce == 4): retire now, $d2c8 then shows the victory screen. Also retire a
            # hopeless side (no lord, no man in any group): a captain group at 0 men keeps its owner word and the
            # land does not end by itself (side-1 run: 1.6G steps in that state, proof1/)
            if obs['ratio'] == 4 or (t['lords'] == 0 and t['group_men'] == 0):
                return [dict(side=self.side, type=RETIRE, x=0, y=0)]
        for g in S['groups']:
            k = g['k']
            if not g['alive'] or 'lead_obj' not in g or g['raw_w4'] != 0:
                self.seen.pop(k, None); continue
            if k in self.movers:
                out += self._move(k, self.movers[k], obs, R, clock)
                continue
            here = tuple(g['lead_obj']['cell'])
            key = (g['state'], here)
            prev = self.seen.get(k)
            n = prev[1] + 1 if prev and prev[0] == key else 0
            self.seen[k] = (key, n)
            if g['state'] not in IDLE and n < STALE:
                continue
            if clock - self.ordered.get(k, -WAIT) < WAIT:
                continue
            d = lambda l: max(abs(l['cell'][0] - here[0]), abs(l['cell'][1] - here[1]))
            pick = lambda ls: min(ls, key=lambda l: (d(l), l['idx'])) if ls else None
            tgt = typ = post = None
            if g['state'] == 6 and tick >= g['camp_since'] + 20:          # $6762 / $67d0 (strategy.md)
                e = FOLLOWUP.get(g['prev_state'])
                a = OBJ + g['target']
                if e and not (g['prev_state'] == 0x0d and g['opp_class'] != 2) and LORD0 <= a < LORD0 + 160 * 32 \
                        and (a - LORD0) % 32 == 0 and lords.get((a - LORD0) // 32, (0,))[0] == self.side:
                    tgt, typ, post = lords[(a - LORD0) // 32][1], e[0], e[1]
                    if local and (typ in (GET_EQUIP, INVENT) or (typ == GET_MEN and tgt['men_home'] <= 1)):
                        tgt = None       # local side: the chain only plunders and recruits (provisioning below)
                    elif local and typ == GET_FOOD:
                        post = 2
            if tgt is None and local:                                   # provisioning, posture 2 takes the whole store
                larder = [l for l in own if l['food'] >= FOOD_MIN and self._reach(g, l['cell'])]
                at = [l for l in larder if d(l) <= 1]
                if at and g['food'] < FOOD_CAP:
                    tgt, typ, post = pick(at), GET_FOOD, 2
                elif larder and g['food'] < FOOD_BITES * (g['men'] // 8 + 1):
                    tgt, typ, post = pick(larder), GET_FOOD, 2
            if tgt is None and g['men'] < MEN_LOW:
                tgt, typ, post = pick([l for l in own if l['men_home'] > 1 and self._reach(g, l['cell'])]), GET_MEN, 2
            if tgt is None and g['men'] > 4:
                foes = [l for l in enemy if l['men_home'] < g['men'] - 4 and self._reach(g, l['cell'])]
                foe = pick(foes)
                if foe:
                    dd = d(foe) * 2      # cells -> the half-cell units $68ee halves (inferred scale)
                    cost = (dd // 2) * ((g['men'] - 4) // 8 + 1) + dd // 2
                    if g['food'] < cost:
                        tgt, typ = pick([l for l in own if l['food'] > 0 and self._reach(g, l['cell'])]), GET_FOOD
                        post = 2 if local else None
                    if tgt is None:
                        tgt, typ, post = foe, ATTACK, 4
            if tgt is None:
                continue
            self.seen[k] = (None, 0)
            self.ordered[k] = clock
            if post is not None and g['posture'] != post:
                out.append(dict(side=self.side, type=POSTURE, x=0, y=post, group=k))
            if self.move:
                from move import Mover
                self.movers[k] = Mover(self.mp, self.side, k, tuple(tgt['cell']), typ)
                out += self._move(k, self.movers[k], obs, R, clock)
            else:
                out.append(dict(side=self.side, type=typ, x=tgt['cell'][0], y=tgt['cell'][1], group=k))
        return out


class Nobody:
    def decide(self, obs, clock):
        return []


class RolloutPolicy(Scripted):
    """The scripted baseline proposes; exact rollouts choose. At a decision where Scripted orders at least one group,
    the candidates are: Scripted's own orders; a no-order baseline (none of them sent); and for the first ordered group
    the alternatives get men at the nearest reachable own lord with men at home > 1, get food at the nearest reachable
    own lord with food, attack the nearest reachable enemy lord with men at home < men (a looser test than
    $6522's men - 4), attack the second-nearest enemy lord passing Scripted's test, and holding that group alone
    (the other groups keep Scripted's orders). Duplicates are dropped and the list is cut at K. Scripted's WAIT
    bookkeeping stands whatever is chosen, so a group that was held is reconsidered 20M steps later, not at once.
    Playing the local side, a decision where Scripted orders nothing still forks when the captain group (group 0) is
    alive with no pending word and either idle and not ordered or forked in the last WAIT steps, or threatened (below):
    none against the same alternatives for the captain. Also on the local side only, when an enemy group with at least the group's men stands
    within THREAT cells, the first alternative is a retreat: go to ($02) the reachable own lord farthest from every such
    group (a heuristic, not the game's AI). Scripted has no rule for a group of MEN_LOW or more with no enemy lord under
    men - 4, so without this the captain sat idle and starved on campaign land 1 (rollout.py's docstring)."""

    def __init__(self, side, mp, K):
        super().__init__(side, mp)       # no --move: a candidate is one decision's order list, not a Mover's legs
        self.K = K

    def _threats(self, obs, g):
        """Lead cells of the enemy groups with at least g's men, when one of them is within THREAT cells of g."""
        here = tuple(g['lead_obj']['cell'])
        eg = [tuple(e['lead_obj']['cell']) for s, v in obs['sides'].items() if int(s) != self.side
              for e in v['groups'] if e['alive'] and e['men'] >= g['men'] and 'lead_obj' in e]
        return eg if eg and min(cheb(here, e) for e in eg) <= THREAT else []

    def candidates(self, obs, pol, clock=None):
        if any('group' not in a for a in pol):
            return []                    # a retire: issue Scripted's actions as they are
        S = obs['sides'][self.side]
        if not pol:                      # nothing ordered: fork for the local captain only
            g = S['groups'][0]
            if (self.side != obs['local_side'] or clock is None or not g['alive'] or 'lead_obj' not in g
                    or g['raw_w4'] != 0):
                return []
            idle = g['state'] in IDLE and clock - self.ordered.get(0, -WAIT) >= WAIT
            if not idle and not self._threats(obs, g):
                return []
            self.ordered[0] = clock      # reconsidered WAIT steps later whatever the rollout picks
        else:
            g = next(g for g in S['groups'] if g['k'] == pol[0]['group'])
        enemy = [l for s, v in obs['sides'].items() if int(s) != self.side for l in v['lords']]
        here = tuple(g['lead_obj']['cell'])
        d = lambda l: max(abs(l['cell'][0] - here[0]), abs(l['cell'][1] - here[1]))
        srt = lambda ls: sorted(ls, key=lambda l: (d(l), l['idx']))
        o = lambda typ, l: dict(side=self.side, type=typ, x=l['cell'][0], y=l['cell'][1], group=g['k'])
        alt = []
        eg = self._threats(obs, g) if self.side == obs['local_side'] else []
        if eg:                           # go to ($02) the reachable own lord farthest from the threatening groups
            safe = [l for l in S['lords'] if self._reach(g, l['cell'])]
            if safe:
                l = max(safe, key=lambda l: (min(cheb(l['cell'], e) for e in eg), -l['idx']))
                alt.append(('retreat', o(GOTO, l)))
        men = srt([l for l in S['lords'] if l['men_home'] > 1 and self._reach(g, l['cell'])])
        if men: alt.append(('get_men', o(GET_MEN, men[0])))
        food = srt([l for l in S['lords'] if l['food'] > 0 and self._reach(g, l['cell'])])
        if food: alt.append(('get_food', o(GET_FOOD, food[0])))
        weak = srt([l for l in enemy if l['men_home'] < g['men'] and self._reach(g, l['cell'])])
        if weak: alt.append(('attack_loose', o(ATTACK, weak[0])))
        foes = srt([l for l in enemy if l['men_home'] < g['men'] - 4 and self._reach(g, l['cell'])])
        if len(foes) > 1: alt.append(('attack_2nd', o(ATTACK, foes[1])))
        if not pol:
            if foes: alt.insert(0, ('attack', o(ATTACK, foes[0])))
            out = [('none', [])] + [(n, [a]) for n, a in alt]
            return out[:self.K]
        out = [('scripted', pol), ('none', [])]
        if len(pol) > 1:
            out.append(('hold_first', pol[1:]))
        for n, a in alt:
            out.append((n, [a] + pol[1:]))
        seen, ded = set(), []
        for n, a in out:
            key = json.dumps(a, sort_keys=True)
            if key not in seen:
                seen.add(key); ded.append((n, a))
        return ded[:self.K]


# ------------------------------------------------------------------ the loop
def main(argv):
    a = list(argv)
    opt = lambda name, d: (a.pop(a.index(name) + 1), a.remove(name))[0] if name in a else d
    flag = lambda name: (a.remove(name), True)[1] if name in a else False
    snap = ROOT / opt('--snap', 'scratchpad/pm142/rand1.snap')
    budget = int(float(opt('--budget', '300e6')))
    every = int(float(opt('--every', '5e6')))
    gap = int(float(opt('--gap', '400e3')))
    side = int(opt('--side', '3'))
    policy = opt('--policy', 'scripted')
    how = opt('--read', 'm')
    replay = opt('--replay', None)
    rK = int(opt('--K', '5'))                       # rollout: candidates per decision (incl. scripted and none)
    rN = int(float(opt('--N', '40e6')))             # rollout: horizon in steps
    rP = int(opt('--par', '5'))                     # rollout: processes at once (the loop's own emulator idles meanwhile)
    force = opt('--force', None)                    # proof: always take the candidate with this name if present
    snap_at = [int(float(x)) for x in opt('--snap-at', '').split(',') if x]   # proof: save <work>/at_<step>.snap
    take = not flag('--no-take')
    move = flag('--move')
    backend = opt('--backend', 'cli')
    model = opt('--model', 'sonnet')
    work = (ROOT / a[0]).resolve()
    work.mkdir(parents=True, exist_ok=True)

    sched = {}           # step -> [action]
    dsteps = None
    if replay:
        recs = [json.loads(l) for l in Path(replay).read_text().splitlines()]
        h = recs[0]
        snap, budget, every, gap, side, take, policy = ROOT / h['snap'], h['budget'], h['every'], h['gap'], h['side'], \
            h['take'], 'replay'
        dsteps = [r['step'] for r in recs if r['kind'] == 'decision']
        for r in recs:
            if r['kind'] == 'applied':
                sched.setdefault(r['step'], []).extend(r['actions'])
    mp = None
    if policy == 'rollout':
        assert not move, '--policy rollout does not take --move'
        sys.path.insert(1, str(HERE))
        from astar import Map
        from rollout import rollout
        mp = Map(load(snap))
        cmdr = RolloutPolicy(side, mp, rK)
    elif policy == 'scripted':
        sys.path.insert(0, str(CMD))
        from astar import Map
        mp = Map(load(snap))   # terrain from the start snapshot (inferred static during a land)
        cmdr = Scripted(side, mp, move)
    elif policy == 'llm':
        from astar import Map
        import llm
        mp = Map(load(snap))
        be = llm.ClaudeCLI(model) if backend == 'cli' else llm.Replay(ROOT / backend.split(':', 1)[1])
        holder = {}
        cmdr = llm.LLM(side, mp, be, work / 'llm', every=every, ram_reader=lambda: holder['emu'].ram)
    else:
        cmdr = Nobody()

    log = open(work / 'decisions.jsonl', 'w')
    W = lambda r: (log.write(json.dumps(r, separators=(',', ':')) + '\n'), log.flush())
    W(dict(kind='start', snap=str(snap.relative_to(ROOT)), budget=budget, every=every, gap=gap, side=side,
           take=take, policy=policy, **(dict(move=True) if move else {}), **(dict(backend=backend, model=model) if policy == 'llm' else {}),
           **(dict(K=rK, N=rN, par=rP, force=force) if policy == 'rollout' else {})))
    emu = Emu(snap, work / 'emu.err')
    if policy == 'llm':
        holder['emu'] = emu
    tmp = work / 'read.snap'
    clock, reason, t0, tread, nread = 0, 'budget', time.time(), 0.0, 0
    trollout, nroll = 0.0, 0
    if take and not replay:
        sched.setdefault(0, []).append(dict(side=side, take=True))
    nextd = 0
    di = 0
    rec = None
    try:
        while True:
            if clock in snap_at:
                emu.save(work / f'at_{clock}.snap')
            if (dsteps is None and clock == nextd and clock < budget) or (dsteps and di < len(dsteps) and dsteps[di] == clock):
                t = time.time(); R = emu.read(how, tmp); tread += time.time() - t; nread += 1
                obs = observe(R)
                rec = dict(kind='decision', step=clock, clock=obs['clock'], side=side, obs_hash=obs_hash(obs),
                           totals={s: v['totals'] for s, v in obs['sides'].items()},
                           groups=[[g['k'], g['men'], g['state'], g['food'], g['raw_w4'],
                                    g.get('lead_obj', {}).get('cell')] for g in obs['sides'][side]['groups'] if g['alive']],
                           actions=[])
                if dsteps is None:
                    acts = list(cmdr.decide(obs, clock, R) if isinstance(cmdr, Scripted) else cmdr.decide(obs, clock))
                    if getattr(cmdr, 'events', None):
                        rec['moves'] = cmdr.events
                    if getattr(cmdr, 'last', None):
                        L = cmdr.last
                        rec['llm'] = dict(prompt=L['prompt_hash'], response=L['response_hash'], parse=L['parse'],
                                          n_orders=L['n_orders'], valid=L['valid'], invalid=len(L['invalid']),
                                          latency_s=L.get('latency_s'))
                    pre = []
                    sl = obs['sides'][side]['slot']
                    if take and clock > 0 and sl['state'] != 2:     # re-take a slot something re-armed ($71ae)
                        pre = [dict(side=side, take=True)]
                    if take and clock == 0:
                        pre = sched.pop(0, [])
                    cands = cmdr.candidates(obs, acts, clock) if policy == 'rollout' else []
                    if cands:
                        dsnap = work / 'dec' / f'{clock}.snap'      # the decision point, before this decision's pokes
                        dsnap.parent.mkdir(exist_ok=True)
                        emu.save(dsnap)
                        t = time.time()
                        res, best = rollout(dsnap, side, [dict(name=n, actions=pre + c) for n, c in cands],
                                            rN, gap, rP, work / 'ro' / str(clock), baseline=False)
                        if force is not None and any(n == force for n, _ in cands):
                            best = [n for n, _ in cands].index(force)
                        acts = cands[best][1]
                        rec['rollout'] = dict(N=rN, best=cands[best][0], wall_s=round(time.time() - t, 2),
                                              cands=[dict(name=r['name'], score=r['score'], steps=r['steps'],
                                                          land_end=r['land_end'], obs_hash=r['obs_hash'],
                                                          sides={s: [v['lords'], v['men_home'], v['group_men'],
                                                                     v['force']] for s, v in r['sides'].items()},
                                                          actions=r['actions'][len(pre):]) for r in res])
                        trollout += time.time() - t; nroll += 1
                    acts = pre + acts
                    for i, ac in enumerate(acts):
                        sched.setdefault(clock + i * gap, []).append(ac)
                    rec['actions'] = acts
                    nextd += every
                else:
                    di += 1
                    rec['actions'] = [ac for s0 in sorted(sched) if s0 >= clock and (di >= len(dsteps) or s0 < dsteps[di])
                                      for ac in sched[s0]]
                W(rec)
            if clock in sched:
                acts = sched.pop(clock)
                emu.mem(0x58010, 0x40)      # slots and acting words, for Poker's neighbour bytes
                lines = from_json(emu.ram, acts)
                emu.poke(lines)
                W(dict(kind='applied', step=clock, actions=acts, lines=lines))
            if clock >= budget:
                break
            cands = [budget] + [s0 for s0 in sched if s0 > clock]
            cands += [s0 for s0 in snap_at if s0 > clock]
            cands.append(nextd if dsteps is None else (dsteps[di] if di < len(dsteps) else budget))
            nxt = min(c for c in cands if c > clock)
            n, hit = emu.run(nxt - clock)
            clock += n
            if hit:
                reason = 'land_end_d2c8'; break
    except EOFError as e:
        reason = f'emulator_exit: {e}'
    wall = time.time() - t0
    final = work / 'final.snap'
    try:
        emu.save(final); R = load(final); obs = observe(R)
        totals = {s: v['totals'] for s, v in obs['sides'].items()}
        cap = obs['sides'][obs['local_side']]['groups'][0]['owner'] if obs['local_side'] in obs['sides'] else None
        fin = dict(clock=obs['clock'], ratio=obs['ratio'], local_captain_owner=cap, obs_hash=obs_hash(obs), totals=totals)
    except Exception as e:
        fin = dict(error=str(e))
    emu.close()
    W(dict(kind='end', step=clock, reason=reason, **fin))
    log.close()
    print(json.dumps(dict(work=str(work), step=clock, reason=reason, wall_s=round(wall, 1),
                          s_per_10M=round(wall * 1e7 / max(clock, 1), 2), reads=nread,
                          read_ms=round(1000 * tread / max(nread, 1), 1), rollouts=nroll, rollout_s=round(trollout, 1), **{k: fin.get(k) for k in ('clock', 'ratio')})))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
