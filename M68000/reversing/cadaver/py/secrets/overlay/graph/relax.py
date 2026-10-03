"""relax.py: A1 (Cadaver 91st pass) monotone (delete-relaxed) reachability over the level-1 script corpus, with a support DAG.

Every fact only ever gains possible values (rooms the hero can stand in, possible words of each type-4 flag, possible values of each script
variable, objects that can be in the rucksack, per-object possible room / hidden / state bits / lock / acti); nothing is ever taken away
and a block can run any number of times (spent bits and keep bits are ignored), so the result OVER-approximates what the exact simulator
(sim.py) can reach: a fact that is not reached here is unreachable by the modelled actions (a dead end).  Each fact records the action that
first made it true and the facts that action needed; `plan()` expands that support DAG into the actions of one relaxed plan, and the
`drop` argument re-runs the closure with blocks removed to test whether a block is necessary (a landmark).
Modelled producers: walking through doors, TAKE (event 0), operate (5), examine (16), apply (18), give (26), touch (9), face (7), the hero in a
region (15), a thrown rucksack item in a region (17), room tick (14), the verb-42 countdown (20), verb 9 (19), room entries (28, 6), teleports.
Not modelled: events 1, 4, 10-13, 25 (producers unread), creature kills (23) other than verb 50.
`spells=True` adds the one native writer that matters: UNLOCK DOOR (spell 8, scroll 407, 15 charges) clears the word of any door of the
current room whose descriptor +7 bit 5 is clear (overlay routine $4ceea; refused when bit 5 is set).
Run: relax.py [--spells] [--plan] goal ...    goal: flag:121 ruck:690 room:53 level:2 exist:731"""
import sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sim import Sim
from model import IFVERBS, CONDS

ACTOR = 0xffff
VARCAP = 12          # the biggest value a level-1 condition compares with is 10 (room 15's ten-visit counter)


class Relaxed:
    def __init__(self, sim, start=None, drop=(), spells=False, no_doors=()):
        self.sm = sim; self.w = sim.w
        self.spells = spells; self.drop = set(drop); self.no_doors = set(no_doors)
        S = start or sim.initial()
        self.prov = {}                       # fact -> (label, round, deps)
        self.round = 0; self.changed = False
        self.gold = S['gold']; self.done_gold = set()
        self.queue = []; self.cur_room = None
        INIT = ('init', 0, ())
        self.fact(('room', S['room']), INIT)
        for n in self.w.flags: self.fact(('flag', n, sim.flag(S, n)), INIT)
        for n in range(20): self.fact(('var', n, S['vars'].get(n, 0)), INIT)
        for r in S['ruck']: self.fact(('item', r[0]), INIT)
        self.objs = list(self.w.objs)
        for o in self.objs:
            st = sim.ost(S, o)
            for f, v in zip(('room', 'hidden', 'b0', 'b1', 'lock', 'acti'), st): self.fact(('obj', o, f, v), INIT)
            self.fact(('obj', o, 'dead', False), INIT)
        self.byowner = sim.blocks
        self.fired = set()

    # ---------------------------------------------------------------- facts
    def fact(self, f, prov):
        if f in self.prov: return False
        self.prov[f] = prov; self.changed = True
        return True

    def has(self, f): return f in self.prov

    def v_vals(self, n):
        return [f[2] for f in self.prov if f[0] == 'var' and f[1] == n]

    # ---------------------------------------------------------------- conditions
    def cond(self, v, a, owner, room):
        """-> (can_true, deps_true, can_false, deps_false)"""
        res = lambda x: owner if x == ACTOR and owner is not None else x
        if v in (16, 19, 30):
            o = res(a[0]) if v != 30 else owner
            fld = 'b1' if v == 19 else 'b0'
            t = ('obj', o, fld, 1); f = ('obj', o, fld, 0)
            return self.has(t), [t], self.has(f), [f]
        if v == 34:
            t = ('item', a[0]); return self.has(t), [t], True, []
        if v == 40:
            n, op, x = a                   # byte order n, op, value ($010c06-$010c12)
            fn = {0: lambda u: u > x, 1: lambda u: u < x, 2: lambda u: u == x}.get(op, lambda u: u != x)
            tv = [('var', n, u) for u in self.v_vals(n) if fn(u)]; fv = [('var', n, u) for u in self.v_vals(n) if not fn(u)]
            return bool(tv), tv[:1], bool(fv), fv[:1]
        if v == 43:
            o = res(a[0]); n = room if a[1] == 254 else a[1]
            t = ('obj', o, 'room', n); return self.has(t), [t], True, []
        if v == 47:
            o = res(a[0])
            return True, [('obj', o, 'dead', False)], self.has(('obj', o, 'dead', True)), []
        if v == 60:
            return self.gold >= a[0], [('gold', a[0])], True, []
        if v == 61:
            tv = [f for f in self.prov if f[0] == 'flag' and f[1] == a[0] and f[2] != 0]
            fv = ('flag', a[0], 0)
            return bool(tv), tv[:1], self.has(fv), [fv]
        return True, [], True, []

    # ---------------------------------------------------------------- execution
    def run_block(self, b, label, room, actor, deps):
        self.fired.add((b.kind, b.owner, b.idx))
        ow = b.owner if b.kind == 'obj' else actor
        self.exec_rows(b, b.rows, 0, len(b.rows), label, room, ow, deps, [])

    def exec_rows(self, b, rows, lo, hi, label, room, ow, deps, pend):
        i = lo; conds = list(pend)
        while i < hi:
            d, v, a, name, ctx = rows[i]
            if v == 23: return
            if v in CONDS:
                conds.append(self.cond(v, a, ow, room)); i += 1; continue
            if v in IFVERBS:
                n = a[0] if v in (58, 59) else None
                j = i + 1
                while j < hi and rows[j][0] > d: j += 1
                then = (i + 1, j); els = None; nxt = j
                if j < hi and rows[j][1] == 15 and rows[j][0] == d:
                    k = j + 1
                    while k < hi and rows[k][0] > d: k += 1
                    els = (j + 1, k); nxt = k
                allt = all(c[0] for c in conds) if conds else True
                lastt = conds[-1][0] if conds else True
                lastf = conds[-1][2] if conds else True
                dt_last = list(conds[-1][1]) if conds else []; df_last = list(conds[-1][3]) if conds else []
                dt_all = [x for c in conds for x in c[1]]; df_all = [x for c in conds for x in c[3]]
                if v == 14: tf, ef, dtt, dee = lastt, lastf or not conds, dt_last, df_last
                elif v == 48: tf, ef, dtt, dee = lastf or not conds, lastt, df_last, dt_last
                elif v == 58: tf, ef, dtt, dee = (allt if n == len(conds) else lastt), True, dt_all, []
                else: tf, ef, dtt, dee = True, allt, [], dt_all
                conds = []
                if tf: self.exec_rows(b, rows, then[0], then[1], label, room, ow, deps + dtt, [])
                if els and ef: self.exec_rows(b, rows, els[0], els[1], label, room, ow, deps + dee, [])
                i = nxt; continue
            if v in (22, 15): i += 1; continue
            self.verb(b, v, a, label, room, ow, deps)
            i += 1

    def mk(self, label, deps):
        return (label, self.round, tuple(dict.fromkeys(deps)))

    def verb(self, b, v, a, label, room, ow, deps):
        R = lambda x: ow if x == ACTOR else x
        P = self.mk(label + ' [%s%d.%d@%d verb %d]' % ('o' if b.kind == 'obj' else 'r', b.owner, b.idx, b.event, v), deps)
        if v in (0, 2):
            o = R(a[0]) if v == 0 else ow
            if o in self.sm.base_obj: self.fact(('obj', o, 'dead', True), P); self.fact(('obj', o, 'room', None), P)
        elif v == 1: self.fact(('obj', R(a[0]), 'hidden', False), P)
        elif v == 26: self.fact(('obj', R(a[0]), 'hidden', True), P)
        elif v in (17, 32): self.fact(('obj', R(a[0]) if v == 17 else ow, 'b0', 1), P)
        elif v in (18, 31): self.fact(('obj', R(a[0]) if v == 18 else ow, 'b0', 0), P)
        elif v in (24, 33):
            o = R(a[0]) if v == 24 else ow; self.fact(('obj', o, 'b0', 1), P); self.fact(('obj', o, 'b0', 0), P)
        elif v in (20, 25): self.fact(('obj', R(a[0]), 'b1', 1), P)
        elif v in (21, 25): self.fact(('obj', R(a[0]), 'b1', 0), P)
        elif v == 54: self.fact(('obj', R(a[0]), 'lock', 1), P)
        elif v == 55: self.fact(('obj', R(a[0]), 'lock', 0), P)
        elif v == 68: self.fact(('obj', R(a[0]), 'acti', 1), P)
        elif v == 67: self.fact(('obj', R(a[0]), 'acti', 0), P)
        elif v == 10: self.fact(('flag', a[0], 0), P)
        elif v == 27: self.fact(('flag', a[0], a[1]), P)
        elif v == 38: self.fact(('var', a[0], a[1] & 0xff), P)
        elif v == 39:
            for u in list(self.v_vals(a[0])):
                if u + a[1] <= VARCAP:
                    self.fact(('var', a[0], u + a[1]), self.mk(label + ' [var %d += %d]' % (a[0], a[1]), deps + [('var', a[0], u)]))
        elif v in (6, 86):
            key = (b.kind, b.owner, b.idx, v)
            if key not in self.done_gold and a[0] < 0x8000:
                self.done_gold.add(key); self.gold += a[0]; self.changed = True
                self.fact(('gold', self.gold), P)
        elif v == 37:
            self.enter(a[0], P)
        elif v == 41:
            o = R(a[0]); r = room if a[1] in (254, 0) else a[1]
            self.fact(('obj', o, 'room', r), P)
        elif v == 73:
            src, dst = R(a[0]), R(a[1])
            for f in list(self.prov):
                if f[0] == 'obj' and f[1] == src and f[2] == 'room' and f[3] is not None:
                    self.fact(('obj', dst, 'room', f[3]), self.mk(label, deps + [f]))
        elif v == 35: self.fact(('item', R(a[0])), P)
        elif v == 9: self.queue.append((19, ('room', room), a[0], P, None))
        elif v == 42: self.queue.append((20, ('room', room), a[0], P, None))
        elif v == 50: self.queue.append((23, ('obj', a[0]), 0, P, None))
        elif v == 51: self.fact(('level', a[0] + 1), P)

    def enter(self, r, P):
        self.fact(('room', r), P)
        self.queue.append((28, ('room', r), 0, P, None)); self.queue.append((6, ('room', r), 0, P, None))

    def gate_ok(self, b, ev, word):
        g = b.gate
        if ev in (4, 18, 26): return word is None or ((g[0] << 8) | g[1]) == word
        if ev in (12, 13, 15, 17, 19, 20, 24): return word is None or g[0] == word
        return True

    def fire(self, ev, tgt, word, P, actor):
        kind, owner = tgt
        label, rnd, deps = P
        room = self.cur_room
        for b in self.byowner.get(tgt, ()):
            if b.event != ev or (b.kind, b.owner, b.idx) in self.drop: continue
            if not self.gate_ok(b, ev, word): continue
            self.run_block(b, label, room, actor if b.kind == 'room' else owner, list(deps))

    def drain(self):
        guard = 0
        while self.queue:
            guard += 1
            if guard > 20000: break
            ev, tgt, wd, P, actor = self.queue.pop(0)
            if tgt[0] == 'room': self.cur_room = tgt[1]
            self.fire(ev, tgt, wd, P, actor)

    # ---------------------------------------------------------------- the round
    def run(self, maxrounds=200):
        sm = self.sm; w = self.w
        for rnd in range(1, maxrounds + 1):
            self.round = rnd; self.changed = False
            for room in sorted(f[1] for f in list(self.prov) if f[0] == 'room'):
                self.cur_room = room
                rd = ('room', room)
                for d in w.rooms[room]['doors']:
                    ow = sm.door_owner[d]
                    if len(ow) != 2 or room not in ow or d in self.no_doors: continue
                    other = ow[0] if ow[1] == room else ow[1]
                    if ('room', other) in self.prov: continue
                    for f in [f for f in self.prov if f[0] == 'flag' and f[1] == d]:
                        wd = f[2]
                        if wd == 0 or (wd < 0x8000 and ('item', wd) in self.prov):
                            deps = [rd, f] + ([('item', wd)] if wd else [])
                            self.enter(other, self.mk('WALK door $%02x %d->%d' % (d, room, other), deps)); break
                if self.spells and ('item', 407) in self.prov:
                    for d in w.rooms[room]['doors']:
                        if w.flags[d]['b7'] & 0x20 or d in self.no_doors: continue
                        for f in [f for f in self.prov if f[0] == 'flag' and f[1] == d and f[2] != 0]:
                            self.fact(('flag', d, 0), self.mk('CAST UNLOCK DOOR (scroll 407) at door $%02x in room %d' % (d, room), [rd, ('item', 407), f])); break
                for o in self.objs:
                    if not self.has(('obj', o, 'room', room)): continue
                    ev = sm.has_ev.get(('obj', o), set())
                    if not ev and not sm.take_ok.get(o): continue
                    if not self.has(('obj', o, 'hidden', False)): continue
                    base = [rd, ('obj', o, 'room', room), ('obj', o, 'hidden', False)]
                    if sm.take_ok.get(o) and self.has(('obj', o, 'lock', 0)) and not self.has(('item', o)):
                        P = self.mk('TAKE %d in room %d' % (o, room), base + [('obj', o, 'lock', 0)])
                        self.fact(('item', o), P)
                        self.queue.append((0, ('obj', o), 0, P, None))
                    if 5 in ev and self.has(('obj', o, 'acti', 0)):
                        self.queue.append((5, ('obj', o), 0, self.mk('OPERATE %d in room %d' % (o, room), base + [('obj', o, 'acti', 0)]), None))
                    if 16 in ev: self.queue.append((16, ('obj', o), 0, self.mk('EXAMINE %d in room %d' % (o, room), base), None))
                    if 9 in ev: self.queue.append((9, ('obj', o), 0, self.mk('TOUCH %d in room %d' % (o, room), base), None))
                    if 7 in ev: self.queue.append((7, ('obj', o), 0, self.mk('FACE %d in room %d' % (o, room), base), None))
                    if 18 in ev or 26 in ev:
                        for it in [f[1] for f in list(self.prov) if f[0] == 'item']:
                            for e in (18, 26):
                                if e in ev:
                                    self.queue.append((e, ('obj', o), it, self.mk('%s item %d to %d in room %d' % ('APPLY' if e == 18 else 'GIVE', it, o, room), base + [('item', it)]), None))
                for it in [f[1] for f in list(self.prov) if f[0] == 'item']:
                    for b in sm.blocks.get(('obj', it), ()):
                        if b.event == 4 and (b.kind, b.owner, b.idx) not in self.drop:
                            tgt = (b.gate[0] << 8) | b.gate[1]
                            if self.has(('obj', tgt, 'room', room)):
                                self.queue.append((4, ('obj', it), tgt, self.mk('THROW %d at %d in room %d' % (it, tgt, room), [rd, ('item', it), ('obj', tgt, 'room', room)]), None))
                for b in sm.blocks.get(('room', room), ()):
                    if b.event == 15:
                        self.queue.append((15, ('room', room), b.gate[0], self.mk('REGION %d of room %d' % (b.gate[0], room), [rd]), None))
                    if b.event == 17:
                        acts = [f[1] for f in list(self.prov) if f[0] == 'item'] or [None]
                        for it in acts:
                            self.queue.append((17, ('room', room), b.gate[0], self.mk('THROW %s into region %d of room %d' % (it, b.gate[0], room), [rd] + ([('item', it)] if it else [])), it))
                    if b.event in (14, 24, 20):
                        self.queue.append((b.event, ('room', room), b.gate[0] if b.gate else None,
                                           self.mk('%s of room %d' % ({14: 'TICK', 24: 'CAST', 20: 'COUNTDOWN'}[b.event], room), [rd]), None))
                self.drain()
            if not self.changed: return rnd
        return maxrounds

    # ---------------------------------------------------------------- queries
    def reached(self, spec):
        kind, _, val = spec.partition(':'); val = int(val)
        f = {'room': ('room', val), 'flag': ('flag', val, 0), 'ruck': ('item', val), 'level': ('level', val),
             'exist': ('obj', val, 'hidden', False), 'b0': ('obj', val, 'b0', 1), 'b1': ('obj', val, 'b1', 1),
             'in96': ('obj', val, 'room', 96)}[kind]
        return f if f in self.prov else None

    def plan(self, f):
        """the support DAG of fact f -> list of (round, label, fact) in layer order"""
        seen = set(); out = []
        def rec(x):
            if x in seen or x not in self.prov: return
            seen.add(x)
            label, rnd, deps = self.prov[x]
            for d in deps: rec(d)
            out.append((rnd, label, x))
        rec(f)
        out.sort(key=lambda t: t[0])
        return out


def setup(spells=False, start=None, drop=(), no_doors=()):
    sm = Sim()
    if spells: sm.items.add(407)     # the UNLOCK DOOR scroll (room 52) is only an item when the spell action exists
    rx = Relaxed(sm, start=start, spells=spells, drop=drop, no_doors=no_doors)
    return sm, rx


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    sm, rx = setup(spells='--spells' in sys.argv)
    n = rx.run()
    rooms = sorted(f[1] for f in rx.prov if f[0] == 'room')
    print('relaxed fixpoint after %d rounds: %d rooms reachable, %d items obtainable' % (n, len(rooms), sum(1 for f in rx.prov if f[0] == 'item')))
    print('not reachable:', sorted(set(sm.w.rooms) - set(rooms)))
    for spec in args:
        f = rx.reached(spec)
        print(spec, 'layer', rx.prov[f][1] if f else None)
        if f and '--plan' in sys.argv:
            for rnd, label, x in rx.plan(f): print('   %2d %-100s => %s' % (rnd, label[:160], x))


if __name__ == '__main__':
    main()
