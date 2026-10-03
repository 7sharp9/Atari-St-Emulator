"""sim.py: A1 (Cadaver 91st pass) abstract executor of the level-1 script corpus + breadth-first planner over player-level actions.

What it is: the verb semantics of secrets.md (callcap-proven by verbs2/) run over an abstract world state (room, type-4 flag words, script
variables, rucksack, per-object room/hidden/state bits/lock/acti, spent blocks, gold, health, the verb-42 countdown).  The consumer rules are
the ones read from $00fdbc: a queue entry (event, target, word) scans the target's blocks in order, the first block whose event byte matches
and whose gate passes runs; a non-keep block is spent before its verbs run; gates per table $00fe84 (events 4/18/26 word compare, 9 word
compare with <0 = any, 12/13/19/20 and 15/17 byte compare with the low byte of the word, 24 spell id).  Teleports (verb 37) queue
event 28 (first entry) then 6 (every entry) for the new room.  IF verbs: 14 then-part when the counter is non-zero, 48 when zero,
58 n when == n, 59 n when != n; a COND adds 1 when true and clears the counter when false.
What it is NOT: physics.  Walking inside a room, the jump/throw arithmetic, creatures, health (kept as a ledger only) and the unread
producers (events 1, 4, 10-13, 25) are not modelled.  A plan is therefore a lower bound on the script-level steps, labelled INFERRED
until each step is driven (the 10 live spot checks of the report cover individual edges, not whole chains)."""
import sys, collections, itertools, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from graph import World
from model import vd, IFVERBS, CONDS, Snap, LINEAGE, L1
import effects as fx

ACTOR = 0xffff


class Sim:
    def __init__(self, world=None, health_floor=1):
        self.w = world or World()
        w = self.w
        self.blocks = collections.defaultdict(list)           # (kind, owner) -> [Block] in record order
        for b in w.blocks: self.blocks[(b.kind, b.owner)].append(b)
        L = w.lineage
        self.base_room = {}
        for r, lst in L['lists'].items():
            for o in lst:
                if o and o not in self.base_room: self.base_room[o] = r
        self.base_obj = {}
        for o in w.objs:
            ob = w.l.obj(o)
            if ob is None: continue
            self.base_obj[o] = dict(hidden=bool(ob['b3'] & 0x80), b0=ob['b3'] & 1, b1=(ob['b3'] >> 1) & 1, lock=(ob['b15'] >> 2) & 1,
                                    acti=(ob['b15'] >> 6) & 1, tmpl=ob['tmpl'])
        self.tmpl = {o: w.objs[o]['tmpl'] for o in w.objs}
        self.cls = {o: w.s.cls(o) for o in w.objs}
        self.take_ok = {o: bool(c and (c['b12'] & 2)) for o, c in self.cls.items()}      # icon 2 needs template byte 12 bit 1 ($0094c0) and +15 bit 2 (lock) clear
        self.door_owner = collections.defaultdict(list)
        for r, rr in w.rooms.items():
            for d in rr['doors']: self.door_owner[d].append(r)
        self.event28_rooms = {b.owner for b in w.blocks if b.kind == 'room' and b.event == 28}
        self.items = set()
        for n in list(w.R) + list(w.W):
            if n[0] in ('item', 'item_used') and isinstance(n[1], int): self.items.add(n[1])
        for f in w.flags.values():
            if 0 < f['word'] < 0x8000: self.items.add(f['word'])
        self.has_ev = collections.defaultdict(set)            # owner -> events with a block
        for b in w.blocks: self.has_ev[(b.kind, b.owner)].add(b.event)
        self.health_floor = health_floor
        self.unmodelled = collections.Counter()
        self.spells = False                                    # native UNLOCK DOOR (scroll 407): set by the caller

    # ------------------------------------------------------------------ state
    def initial(self, room=None):
        L = self.w.lineage
        S = dict(room=room if room is not None else L['room'], flags={}, vars=dict(L['vars']), ruck=tuple(tuple(x) for x in L['ruck']),
                 od={}, spent=frozenset(self.w.spent), gold=L['gold'], health=L['health'], pending=None, dead=frozenset(), visited=frozenset(
                     r for r in self.event28_rooms if self.w.l.rooms()[r]['b23'] & 0x40), level=0, rand=0, trace=[])
        return S

    @staticmethod
    def key(S):
        return (S['room'], tuple(sorted(S['flags'].items())), tuple(sorted(S['vars'].items())), S['ruck'], tuple(sorted(S['od'].items())),
                S['spent'], S['gold'], S['pending'], S['visited'], S['level'], S['dead'])

    @staticmethod
    def copy(S):
        T = dict(S); T['flags'] = dict(S['flags']); T['vars'] = dict(S['vars']); T['od'] = dict(S['od']); T['trace'] = list(S['trace'])
        return T

    def ost(self, S, o):
        """(room, hidden, b0, b1, lock, acti); room None = deleted/nowhere/in the rucksack"""
        if o in S['od']: return S['od'][o]
        b = self.base_obj.get(o)
        if b is None: return (None, False, 0, 0, 0, 0)
        return (self.base_room.get(o), b['hidden'], b['b0'], b['b1'], b['lock'], b['acti'])

    def setost(self, S, o, **kw):
        if o is None: return
        r, h, b0, b1, lk, ac = self.ost(S, o)
        r = kw.get('room', r) if 'room' in kw else r
        S['od'][o] = (kw['room'] if 'room' in kw else r, kw.get('hidden', h), kw.get('b0', b0), kw.get('b1', b1), kw.get('lock', lk), kw.get('acti', ac))

    def flag(self, S, n):
        return S['flags'].get(n, self.w.lineage['flags'].get(n, 0))

    def in_ruck(self, S, o): return any(r[0] == o for r in S['ruck'])

    def objs_in(self, S, room):
        out = []
        seen = set()
        for o, (r, *_rest) in S['od'].items():
            if r == room: out.append(o)
            seen.add(o)
        for o, r in self.base_room.items():
            if r == room and o not in seen: out.append(o)
        return out

    # ------------------------------------------------------------------ consumer
    def fire(self, S, event, target, word=0, actor=None):
        """run one queue entry and everything it queues (FIFO), like one drain of $00fdbc"""
        q = [(event, target, word, actor)]
        guard = 0
        while q:
            guard += 1
            if guard > 400: raise RuntimeError('queue runaway')
            ev, tgt, wd, act = q.pop(0)
            kind, owner = tgt
            if kind == 'obj' and owner in S['dead']: continue
            for b in self.blocks.get(tgt, ()):
                bid = (b.kind, b.owner, b.idx)
                if bid in S['spent'] or b.event != ev: continue
                if not self.gate_ok(b, ev, wd): continue
                if not b.keep: S['spent'] = S['spent'] | {bid}
                S['trace'].append('%s%d.%d@%d' % ('o' if b.kind == 'obj' else 'r', b.owner, b.idx, b.event))
                self.run_block(S, b, q, act if act is not None else ('obj', owner) if kind == 'obj' else None)
                break

    def gate_ok(self, b, ev, wd):
        g = b.gate
        if ev in (2, 8): return False
        if ev in (4, 18, 26):
            return ((g[0] << 8) | g[1]) == wd
        if ev == 9:
            w = (g[0] << 8) | g[1]
            return w >= 0x8000 or w == wd
        if ev in (12, 13, 15, 17, 19, 20, 24): return g[0] == (wd & 0xff)
        if ev == 10: return g[1] == (wd & 0xff)
        if ev == 1: return True
        return True

    def run_block(self, S, b, q, actor):
        S['_cnt'] = 0
        self.exec_rows(S, b, b.rows, 0, len(b.rows), q, actor)

    def exec_rows(self, S, b, rows, lo, hi, q, actor):
        i = lo
        while i < hi:
            d, v, a, name, ctx = rows[i]
            if v == 23: return True
            if v in IFVERBS:
                c = S['_cnt']
                take = {14: c != 0, 48: c == 0, 58: c == (a[0] if a else 0), 59: c != (a[0] if a else 0)}[v]
                j = i + 1
                while j < hi and rows[j][0] > d: j += 1
                then = (i + 1, j)
                els = None; nxt = j
                if j < hi and rows[j][1] == 15 and rows[j][0] == d:
                    k = j + 1
                    while k < hi and rows[k][0] > d: k += 1
                    els = (j + 1, k); nxt = k
                S['_cnt'] = 0
                rng = then if take else els
                if rng:
                    if self.exec_rows(S, b, rows, rng[0], rng[1], q, actor): return True
                i = nxt; continue
            if v in (22, 15): i += 1; continue
            self.verb(S, b, v, a, q, actor)
            i += 1
        return False

    # ------------------------------------------------------------------ verbs
    def resolve(self, o, b, actor):
        if o != ACTOR: return o
        if actor is not None and actor[0] == 'obj': return actor[1]
        if b.kind == 'obj': return b.owner
        return None

    def delete(self, S, o):
        if o is None: return
        S['ruck'] = tuple(r for r in S['ruck'] if r[0] != o)
        S['od'][o] = (None, False, 0, 0, 0, 0)
        S['dead'] = S['dead'] | {o}

    def verb(self, S, b, v, a, q, actor):
        me = self.resolve(ACTOR, b, actor)
        R = lambda i: self.resolve(a[i], b, actor)
        cnt = S['_cnt']
        def cond(ok):
            S['_cnt'] = S['_cnt'] + 1 if ok else 0
        if v == 0: self.delete(S, a[0])
        elif v == 1: self.setost(S, a[0], hidden=False)
        elif v == 2: self.delete(S, me)
        elif v in (3, 4, 11, 12, 28, 70, 72, 87, 7, 8, 5, 85, 49, 65, 66, 69, 79, 90, 93, 36, 44, 84, 46, 71, 52, 83):
            if v == 79: S['rand'] = a[0]
            if v in (36, 44, 84, 66): self.unmodelled[v] += 1
        elif v == 6: S['gold'] += a[0]
        elif v == 13: S['gold'] -= a[0]
        elif v == 86: S['gold'] += a[0] - 0x10000 if a[0] >= 0x8000 else a[0]
        elif v == 45: S['health'] += a[0] - 0x10000 if a[0] >= 0x8000 else a[0]
        elif v == 9: q.append((19, ('room', S['room']), a[0], None))
        elif v == 10: S['flags'][a[0]] = 0
        elif v == 27: S['flags'][a[0]] = a[1]
        elif v == 61: cond(self.flag(S, a[0]) != 0)
        elif v == 16: cond(bool(self.ost(S, R(0))[2]))
        elif v == 17: self.setost(S, R(0), b0=1)
        elif v == 18: self.setost(S, R(0), b0=0)
        elif v == 24: self.setost(S, R(0), b0=1 - self.ost(S, R(0))[2])
        elif v == 19: cond(bool(self.ost(S, R(0))[3]))
        elif v == 20: self.setost(S, R(0), b1=1)
        elif v == 21: self.setost(S, R(0), b1=0)
        elif v == 25: self.setost(S, R(0), b1=1 - self.ost(S, R(0))[3])
        elif v == 26: self.setost(S, R(0), hidden=True)
        elif v == 29: S['spent'] = S['spent'] | {(b.kind, b.owner, b.idx)}
        elif v == 30: cond(bool(self.ost(S, me)[2]))
        elif v == 31: self.setost(S, me, b0=0)
        elif v == 32: self.setost(S, me, b0=1)
        elif v == 33: self.setost(S, me, b0=1 - self.ost(S, me)[2])
        elif v == 34: cond(self.in_ruck(S, a[0]))
        elif v == 35:
            o = R(0)
            if len(S['ruck']) < 32:
                S['ruck'] = S['ruck'] + ((o, self.tmpl.get(o, 0)),)
                self.setost(S, o, room=None)
                q.append((0, ('obj', o), 0, None))
        elif v == 37: self.teleport(S, a[0], q)
        elif v == 38: S['vars'][a[0]] = a[1] & 0xff
        elif v == 39: S['vars'][a[0]] = (S['vars'].get(a[0], 0) + a[1]) & 0xff
        elif v == 40:
            x = S['vars'].get(a[0], 0); op = a[1]; n = a[2]       # byte order n, op, value ($010c06-$010c12)
            cond({0: x > n, 1: x < n, 2: x == n}.get(op, x != n))
        elif v == 41:
            o = R(0); r = S['room'] if a[1] in (254, 0) else a[1]
            if o is not None: self.setost(S, o, room=r)
        elif v == 42: S['pending'] = a[0]
        elif v == 43:
            r = self.ost(S, R(0))[0]; n = S['room'] if a[1] == 254 else a[1]
            cond(r == n)
        elif v == 47: cond(self.ost(S, R(0))[0] is not None or self.in_ruck(S, R(0)))
        elif v == 50: q.append((23, ('obj', a[0]), 0, None))
        elif v == 51: S['level'] = a[0] + 1
        elif v == 54: self.setost(S, R(0), lock=1)
        elif v == 55: self.setost(S, R(0), lock=0)
        elif v == 56: cond(False)
        elif v == 57: cond(False)                               # selected object not modelled
        elif v == 60:
            ok = S['gold'] >= a[0]
            if ok: S['gold'] -= a[0]
            cond(ok)
        elif v == 67: self.setost(S, R(0), acti=0)
        elif v == 68: self.setost(S, R(0), acti=1)
        elif v == 73:
            src = R(0); dst = R(1)
            r = self.ost(S, src)[0]
            if dst is not None: self.setost(S, dst, room=r if r is not None else S['room'])
        elif v == 76: cond(False)
        elif v == 80: cond(S.get('rand', 0) == a[0])
        elif v == 81: S['rand'] = S['vars'].get(a[0], 0)
        elif v == 82:
            S['ruck'] = tuple(r for r in S['ruck'] if r[1] != a[0])
        elif v == 88: cond(False)
        elif v == 91: cond(self.tmpl.get(me, -1) == a[0])
        elif v == 60: pass
        else:
            self.unmodelled[('verb', v)] += 1

    def teleport(self, S, room, q):
        S['room'] = room
        if room in self.event28_rooms and room not in S['visited']:
            S['visited'] = S['visited'] | {room}
            q.append((28, ('room', room), 0, None))
        q.append((6, ('room', room), 0, None))

    # ------------------------------------------------------------------ player actions
    def actions(self, S):
        w = self.w; room = S['room']
        acts = []
        # walking
        for d in w.rooms[room]['doors']:
            word = self.flag(S, d)
            ow = self.door_owner[d]
            if len(ow) != 2 or room not in ow: continue
            other = ow[0] if ow[1] == room else ow[1]
            if word == 0: acts.append(('walk', d, other))
            elif word < 0x8000 and self.in_ruck(S, word): acts.append(('walk', d, other))
        here = [o for o in self.objs_in(S, room) if not self.ost(S, o)[1]]
        for o in here:
            ev = self.has_ev.get(('obj', o), set())
            st = self.ost(S, o)
            takeable = self.take_ok.get(o, False) and not st[4]
            if takeable and len(S['ruck']) < 32: acts.append(('take', o))
            if 5 in ev and not st[5]: acts.append(('operate', o))
            if 16 in ev: acts.append(('examine', o))
            if 18 in ev:
                for (i, t) in S['ruck']: acts.append(('apply', i, o))
            if 26 in ev:
                for (i, t) in S['ruck']: acts.append(('give', i, o))
            if 9 in ev: acts.append(('touch', o))
            if 7 in ev: acts.append(('face', o))
        # event 4 = a thrown/launched object hits object X ($00f2d8-$00f328: queue [4][projectile][word = id of the object hit]):
        # the projectile's own event-4 block runs, gate word = the target id
        for (i, t) in S['ruck']:
            for b in self.blocks.get(('obj', i), ()):
                if b.event == 4 and (b.kind, b.owner, b.idx) not in S['spent']:
                    tgt = (b.gate[0] << 8) | b.gate[1]
                    if tgt in here: acts.append(('throw_at', i, tgt))
        rb = self.blocks.get(('room', room), [])
        for b in rb:
            if (b.kind, b.owner, b.idx) in S['spent']: continue
            if b.event == 15: acts.append(('region', b.gate[0]))
            if b.event == 17:
                for (i, t) in S['ruck']: acts.append(('throw', i, b.gate[0]))
            if b.event == 14: acts.append(('tick',))
            if b.event == 24: acts.append(('cast', b.gate[0]))
        if S['pending'] is not None: acts.append(('wait', S['pending']))
        if self.spells and self.in_ruck(S, 407):
            for d in w.rooms[room]['doors']:
                if self.flag(S, d) != 0 and not (w.flags[d]['b7'] & 0x20): acts.append(('cast8', d))
        return sorted(set(acts))

    def apply(self, S, act):
        T = self.copy(S); T['trace'] = []
        kind = act[0]; q = []
        if kind == 'walk':
            d, other = act[1], act[2]
            word = self.flag(T, d)
            if word != 0:
                f = self.w.flags[d]
                if f['b7'] & 2: T['flags'][d] = 0; T['ruck'] = tuple(r for r in T['ruck'] if r[0] != word)
                elif f['b7'] & 4: T['flags'][d] = 0
            self.teleport(T, other, q)
            self.drain(T, q)
        elif kind == 'take':
            o = act[1]
            T['ruck'] = T['ruck'] + ((o, self.tmpl.get(o, 0)),)
            self.setost(T, o, room=None)
            self.fire(T, 0, ('obj', o))
        elif kind == 'operate': self.fire(T, 5, ('obj', act[1]))
        elif kind == 'examine': self.fire(T, 16, ('obj', act[1]))
        elif kind == 'apply': self.fire(T, 18, ('obj', act[2]), word=act[1])
        elif kind == 'give':
            self.fire(T, 26, ('obj', act[2]), word=act[1])
            T['ruck'] = tuple(r for r in T['ruck'] if r[0] != act[1])
        elif kind == 'throw_at':
            i, tgt = act[1], act[2]
            T['ruck'] = tuple(r for r in T['ruck'] if r[0] != i)
            self.setost(T, i, room=T['room'])
            self.fire(T, 4, ('obj', i), word=tgt)
        elif kind == 'touch': self.fire(T, 9, ('obj', act[1]), word=0)
        elif kind == 'face': self.fire(T, 7, ('obj', act[1]))
        elif kind == 'region': self.fire(T, 15, ('room', T['room']), word=act[1], actor=('hero', 0))
        elif kind == 'throw':
            i, k = act[1], act[2]
            T['ruck'] = tuple(r for r in T['ruck'] if r[0] != i)
            self.setost(T, i, room=T['room'])
            self.fire(T, 17, ('room', T['room']), word=k, actor=('obj', i))
        elif kind == 'tick': self.fire(T, 14, ('room', T['room']))
        elif kind == 'wait':
            g = T['pending']; T['pending'] = None
            self.fire(T, 20, ('room', T['room']), word=g)
        elif kind == 'cast': self.fire(T, 24, ('room', T['room']), word=act[1])
        elif kind == 'cast8':
            T['flags'][act[1]] = 0
            self.fire(T, 24, ('room', T['room']), word=8)
        T.pop('_cnt', None)
        return T

    def drain(self, S, q):
        while q:
            ev, tgt, wd, act = q.pop(0)
            self.fire(S, ev, tgt, wd, act)

    # fire() handles teleports queued entries by itself through run_block's q; make teleports inside fire drain too
    def describe(self, act):
        k = act[0]
        if k == 'walk': return 'walk through door $%02x to room %d' % (act[1], act[2])
        if k == 'take': return 'TAKE %s' % self.w.oname(act[1])
        if k == 'operate': return 'OPERATE %s' % self.w.oname(act[1])
        if k == 'examine': return 'EXAMINE %s' % self.w.oname(act[1])
        if k == 'apply': return 'APPLY item %d to %s' % (act[1], self.w.oname(act[2]))
        if k == 'give': return 'GIVE item %d to %s' % (act[1], self.w.oname(act[2]))
        if k == 'touch': return 'TOUCH %s' % self.w.oname(act[1])
        if k == 'face': return 'FACE %s' % self.w.oname(act[1])
        if k == 'region': return 'hero steps into region %d' % act[1]
        if k == 'throw': return 'THROW item %d into region %d' % (act[1], act[2])
        if k == 'throw_at': return 'THROW item %d at object %d (event 4)' % (act[1], act[2])
        if k == 'tick': return 'wait for the room tick'
        if k == 'wait': return 'wait for the verb-42 countdown (gate %d)' % act[1]
        if k == 'cast': return 'CAST spell %d' % act[1]
        if k == 'cast8': return 'CAST UNLOCK DOOR (scroll 407) at door $%02x' % act[1]
        return str(act)

    def bfs(self, S0, goal, maxdepth=40, maxstates=2_000_000, action_filter=None, verbose=True):
        """breadth-first search; visited set and parent links keyed by hash(key) (collisions are negligible at these sizes).  Returns (path, state) with
        path = [(action, trace of blocks fired)] replayed from the start, or None."""
        import gc
        h0 = hash(self.key(S0))
        parent = {h0: None}
        S0 = self.copy(S0); S0['trace'] = []
        frontier = [(S0, h0)]
        depth = 0; t0 = time.time()
        def build(hh, S_final):
            acts = []
            while parent[hh] is not None:
                ph, act = parent[hh]; acts.append(act); hh = ph
            acts.reverse()
            S = self.copy(S0); out = []
            for act in acts:
                S = self.apply(S, act); out.append((act, list(S['trace'])))
            return out, S
        if goal(S0): return [], S0
        while frontier and depth < maxdepth:
            nxt = []
            for S, hh in frontier:
                for act in self.actions(S):
                    if action_filter and not action_filter(S, act): continue
                    try: T = self.apply(S, act)
                    except Exception as e:
                        import os, traceback
                        if os.environ.get('SIMDEBUG'): traceback.print_exc(); print('action', act)
                        continue
                    if T['health'] < self.health_floor: continue
                    h = hash(self.key(T))
                    if h in parent: continue
                    parent[h] = (hh, act)
                    if goal(T): return build(h, T)
                    T['trace'] = []
                    nxt.append((T, h))
            depth += 1
            frontier = nxt
            if verbose: print('  depth %d: %d states (total %d, %.0fs)' % (depth, len(frontier), len(parent), time.time() - t0), flush=True)
            if len(parent) > maxstates: return None
        return None

    def explore(self, S0, action_filter, maxdepth=26, maxstates=3_000_000, facts=None):
        """lean BFS (hash-only visited set): returns {fact: (depth, path)} for the first state in BFS order that makes each fact true.
        facts(S) -> iterable of hashable facts of a state."""
        seen = {hash(self.key(S0))}
        frontier = [(S0, ())]
        first = {}
        for f in facts(S0): first.setdefault(f, (0, ()))
        depth = 0; t0 = time.time()
        while frontier and depth < maxdepth:
            nxt = []
            for S, path in frontier:
                for act in self.actions(S):
                    if action_filter and not action_filter(S, act): continue
                    try: T = self.apply(S, act)
                    except Exception: continue
                    if T['health'] < self.health_floor: continue
                    h = hash(self.key(T))
                    if h in seen: continue
                    seen.add(h)
                    p2 = path + (act,)
                    for f in facts(T):
                        if f not in first: first[f] = (depth + 1, p2)
                    T['trace'] = []
                    nxt.append((T, p2))
            depth += 1; frontier = nxt
            print('  depth %d: %d states (total %d, %.0fs)' % (depth, len(frontier), len(seen), time.time() - t0), flush=True)
            if len(seen) > maxstates: print('  state limit'); break
        return first

    def path(self, S, parent, seen):
        out = []
        k = self.key(S)
        while seen.get(k):
            pk, act, tr = seen[k]
            out.append((act, tr)); k = pk
        out.reverse()
        return out, S


# ---------------------------------------------------------------------- relevance (regression) filter
def relevant_blocks(w, goal_nodes, extra_kinds=('tele',), movement=True, actor_writers=False):
    """least fixpoint: a block is relevant when it writes a relevant node; its reads (COND verbs, item gates) become relevant nodes.
    Door flags (all type-4 records that are a door of some room) and every teleport target are relevant from the start (movement)."""
    relevant_nodes = set(goal_nodes)
    if movement:
      for n in list(w.W) + list(w.R):
        if n[0] == 'tele': relevant_nodes.add(n)
    for r, rr in (w.rooms.items() if movement else ()):
        for d in rr['doors']:
            relevant_nodes.add(('flag', d))
            fw = w.flags[d]['word']
            if 0 < fw < 0x8000: relevant_nodes.add(('item', fw)); relevant_nodes.add(('exist', fw))   # a keyed door: the key is an item
    rel = set(); changed = True
    blk_w = collections.defaultdict(set); blk_r = collections.defaultdict(set)
    for n, lst in w.W.items():
        for (b, row, det, ctx) in lst: blk_w[id(b)].add(n)
    for n, lst in w.R.items():
        for (b, row, det, ctx) in lst: blk_r[id(b)].add(n)
    byid = {id(b): b for b in w.blocks}
    while changed:
        changed = False
        for bi, b in byid.items():
            if bi in rel: continue
            ws = blk_w[bi]
            any_exist = actor_writers and any(m[0] == 'exist' for m in relevant_nodes)
            hit = any(n in relevant_nodes or (n[0] == 'exist' and n[1] == 'ACTOR' and any_exist) for n in ws)
            # a DELETE of an item/object that is itself relevant also counts via the exist node
            if hit:
                rel.add(bi); changed = True
                for n in blk_r[bi]:
                    if n not in relevant_nodes:
                        relevant_nodes.add(n)
                        if n[0] == 'item': relevant_nodes.add(('exist', n[1]))
                        if n[0] == 'item_used': relevant_nodes.add(('item', n[1])); relevant_nodes.add(('exist', n[1]))
                        changed = True
    return {(byid[bi].kind, byid[bi].owner, byid[bi].idx) for bi in rel}, relevant_nodes


def make_filter(sm, rel, nodes):
    w = sm.w
    byowner = collections.defaultdict(list)
    for b in w.blocks:
        if (b.kind, b.owner, b.idx) in rel: byowner[(b.kind, b.owner)].append(b)

    def has(kind, owner, ev, word=None):
        for b in byowner.get((kind, owner), ()):
            if b.event != ev: continue
            if word is not None and ev in (18, 26) and ((b.gate[0] << 8) | b.gate[1]) != word: continue
            return True
        return False

    def f(S, act):
        k = act[0]
        if k == 'walk': return True
        if k == 'take': return has('obj', act[1], 0) or ('item', act[1]) in nodes or ('exist', act[1]) in nodes
        if k == 'operate': return has('obj', act[1], 5)
        if k == 'examine': return has('obj', act[1], 16)
        if k == 'apply': return has('obj', act[2], 18, act[1])
        if k == 'give': return has('obj', act[2], 26, act[1])
        if k == 'touch': return has('obj', act[1], 9)
        if k == 'face': return has('obj', act[1], 7)
        if k == 'region': return any(b.event == 15 and b.gate[0] == act[1] for b in byowner.get(('room', S['room']), ()))
        if k == 'throw': return any(b.event == 17 and b.gate[0] == act[2] for b in byowner.get(('room', S['room']), ()))
        if k == 'throw_at': return has('obj', act[1], 4)
        if k == 'tick': return has('room', S['room'], 14)
        if k == 'wait': return has('room', S['room'], 20)
        if k == 'cast': return has('room', S['room'], 24)
        return True
    return f
