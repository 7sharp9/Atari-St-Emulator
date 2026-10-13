"""loop.py: the commander's decision loop with replay logging (commander README plan step 3).

    loop.py <work> [--snap S] [--budget N] [--every N] [--side K] [--policy scripted|none|llm] [--no-take]
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
RETIRE = 0x2e                                   # strategy.md "How a land ends": $2e in the local side's slot -> $d2c8
IDLE = (0, 1, 6)                                # state names (observe.STATE): none, Waiting, In Camp
MEN_LOW = 22                                    # $6522's own get-men arm: men < 22 (strategy.md "The AI as modern pseudocode")
STALE = 8                                       # decisions with no change of state or lead cell before re-ordering
WAIT = 20_000_000                               # steps an ordered group is left alone: an injected order reaches a
                                                # non-first group by pigeon ~9M steps later (README) and sets no
                                                # pending word 4 (observed in this loop's first runs), so without
                                                # this the same order is re-sent every decision


class Scripted:
    """Deterministic baseline for one side. For each live group with men, no pending pigeon (word 4, as $6564
    skips) and idle (or stale): men < 22 -> get men at the nearest reachable own lord with men at home > 1; else
    food short of the trip ($68ee's cost: (d/2)*((men-4)/8+1) + d/2) -> get food at the nearest own lord with food;
    else attack the nearest reachable enemy lord with men at home < men - 4 ($6522's attack arm test).
    Playing the local side, it posts retire $2e as soon as the observed ratio $57fce is 4 (a win), or when the side
    has no lord and no man left (a loss the game does not end by itself)."""

    def __init__(self, side, mp=None):
        self.side, self.mp = side, mp
        self.seen = {}           # k -> ((state, lead cell), decisions unchanged)
        self.ordered = {}        # k -> step of the last order
        self.comps = mp.cell_components() if mp else None

    def _reach(self, g, cell):
        if self.mp is None:
            return True
        a = self.mp.component(g['lead_obj']['x'], g['lead_obj']['y'])
        b = self.comps[cell[1]][cell[0]]
        return a is not None and a == b

    def decide(self, obs, clock):
        S = obs['sides'][self.side] if self.side in obs['sides'] else obs['sides'][str(self.side)]
        allside = obs['sides']
        own = [l for l in S['lords']]
        enemy = [l for s, v in allside.items() if int(s) != self.side for l in v['lords']]
        out = []
        if self.side == obs['local_side']:
            t = S['totals']
            # the scale is full ($57fce == 4): retire now, $d2c8 then shows the victory screen. Also retire a
            # hopeless side (no lord, no man in any group): a captain group at 0 men keeps its owner word and the
            # land does not end by itself (side-1 run: 1.6G steps in that state, proof1/)
            if obs['ratio'] == 4 or (t['lords'] == 0 and t['group_men'] == 0):
                return [dict(side=self.side, type=RETIRE, x=0, y=0)]
        for g in S['groups']:
            k = g['k']
            if not g['alive'] or g['men'] <= 0 or 'lead_obj' not in g or g['raw_w4'] != 0:
                self.seen.pop(k, None); continue
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
            tgt = typ = None
            if g['men'] < MEN_LOW:
                tgt, typ = pick([l for l in own if l['men_home'] > 1 and self._reach(g, l['cell'])]), GET_MEN
            if tgt is None:
                foes = [l for l in enemy if l['men_home'] < g['men'] - 4 and self._reach(g, l['cell'])]
                foe = pick(foes)
                if foe:
                    dd = d(foe) * 2      # cells -> the half-cell units $68ee halves (inferred scale)
                    cost = (dd // 2) * ((g['men'] - 4) // 8 + 1) + dd // 2
                    if g['food'] < cost:
                        tgt, typ = pick([l for l in own if l['food'] > 0 and self._reach(g, l['cell'])]), GET_FOOD
                    if tgt is None:
                        tgt, typ = foe, ATTACK
            if tgt is None:
                continue
            self.seen[k] = (None, 0)
            self.ordered[k] = clock
            out.append(dict(side=self.side, type=typ, x=tgt['cell'][0], y=tgt['cell'][1], group=k))
        return out


class Nobody:
    def decide(self, obs, clock):
        return []


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
    take = not flag('--no-take')
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
    if policy == 'scripted':
        sys.path.insert(0, str(CMD))
        from astar import Map
        mp = Map(load(snap))   # terrain from the start snapshot (inferred static during a land)
        cmdr = Scripted(side, mp)
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
           take=take, policy=policy, **(dict(backend=backend, model=model) if policy == 'llm' else {})))
    emu = Emu(snap, work / 'emu.err')
    if policy == 'llm':
        holder['emu'] = emu
    tmp = work / 'read.snap'
    clock, reason, t0, tread, nread = 0, 'budget', time.time(), 0.0, 0
    if take and not replay:
        sched.setdefault(0, []).append(dict(side=side, take=True))
    nextd = 0
    di = 0
    rec = None
    try:
        while True:
            if (dsteps is None and clock == nextd and clock < budget) or (dsteps and di < len(dsteps) and dsteps[di] == clock):
                t = time.time(); R = emu.read(how, tmp); tread += time.time() - t; nread += 1
                obs = observe(R)
                rec = dict(kind='decision', step=clock, clock=obs['clock'], side=side, obs_hash=obs_hash(obs),
                           totals={s: v['totals'] for s, v in obs['sides'].items()},
                           groups=[[g['k'], g['men'], g['state'], g['food'], g['raw_w4'],
                                    g.get('lead_obj', {}).get('cell')] for g in obs['sides'][side]['groups'] if g['alive']],
                           actions=[])
                if dsteps is None:
                    acts = list(cmdr.decide(obs, clock))
                    if getattr(cmdr, 'last', None):
                        L = cmdr.last
                        rec['llm'] = dict(prompt=L['prompt_hash'], response=L['response_hash'], parse=L['parse'],
                                          n_orders=L['n_orders'], valid=L['valid'], invalid=len(L['invalid']),
                                          latency_s=L.get('latency_s'))
                    sl = obs['sides'][side]['slot']
                    if take and clock > 0 and sl['state'] != 2:     # re-take a slot something re-armed ($71ae)
                        acts.insert(0, dict(side=side, take=True))
                    if take and clock == 0:
                        acts = sched.pop(0, []) + acts
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
                          read_ms=round(1000 * tread / max(nread, 1), 1), **{k: fin.get(k) for k in ('clock', 'ratio')})))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
