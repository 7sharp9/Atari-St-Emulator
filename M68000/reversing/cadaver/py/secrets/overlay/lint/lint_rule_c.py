"""lint_rule_c.py [--level 0|1] [--verbose]: rule (c), keyed doors whose key item can never be obtained.

A door is a type-4 record named by a room record's door list (`+6`, 7 words, `$ffff` = none).  The crossing code reads the
descriptor's word `+2` (`$007178 move.w 2(A0),D3`): 0 crosses (`beq $71ca`), `$ffff` goes to the shut path `$731e`, and ANY
other value is handed to `$011256` as D2, which walks the type-8 list (`moveq #8,D0`, `bsr $c628`) and compares each record's
word +0, the OBJECT id (`$01126a cmp.w 0(A0,D3.w),D2`, D3 = 0); not found -> `$734a` (no crossing).  `+7` bit 1 / bit 2 then
decide consume / clear (`$00719a`-`$0071b8`).  So a keyed door is one whose word is neither 0 nor `$ffff`, at load or after a
script writes it with verb 27 (SET FLAG n = word); its key is the type-6 object with that id.

A key counts as obtainable when
  (1) it is in some room's type-5 list at load and its record `+3` bit 7 (hidden) is clear,
  (2) a script verb puts THAT id where it can be taken: verb 1 SHOW (for a hidden listed key), 41 PLACE, 73 MOVE (second
      operand), 35 PUT IN RUCK.  Verbs 36 CREATE, 44 and 84 (spawn) make a clone with a NEW id >= 900 (`verbs2/sec4_create.py`:
      "exactly one new id ... >= 900"), so a clone of the key never matches the door word; they are listed, not counted;
  (3) it is in the type-8 list (rucksack) of the snapshot.
Script routes are then rated: a route is dubious when its block's event has no push site (ctx.producers, else the cached
`scratchpad/cadaver/lint/push_sites_scan.out`), the block is spent ($ff event byte), the owning object is never in a room (not listed, not
placed by any script, not carried), the owning room / object rooms lie outside the generous reachability closure below, or the
block's gate (events 18/26) or an enclosing verb-34 condition names an item that is itself not obtainable.

Generous reachability (an over-approximation, so "outside it" is a sound "never" under its assumption): from the snapshot's
current room, every door joins the two rooms that list it whatever its word (doors are undirected links of their owners,
mechanics.md section 4: 71/71 door ids resolve to an owner or an edge-adjacent room), plus every verb-37 teleport whose block
runs in a reached room (object blocks: the rooms the object can be in; rucksack items: anywhere).

Interface: rule(ctx) -> list of dicts {rule, level, owner, event, detail}; ctx as lint_abf/lint.py builds it (.snap, .level,
.blocks of Block(owner, event, ops, kind, oid, start, ebyte, body), optional .producers, .notes).
Standalone (from anywhere):  M68000/.venv/bin/python M68000/reversing/cadaver/py/secrets/overlay/lint/lint_rule_c.py [--level 0|1] [--verbose]"""
import sys, os, re, collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ['M68000_ROOT']) if os.environ.get('M68000_ROOT') else next(p for p in HERE.parents if (p / 'tools/rdis.py').exists())
for p in ('reversing/cadaver/py/secrets/overlay/graph', 'reversing/cadaver/py/secrets/overlay', 'reversing/cadaver/py', 'tools'):
    if str(ROOT / p) not in sys.path: sys.path.insert(0, str(ROOT / p))
import model as M          # graph/model.py: Snap (rooms, flags, type-5 lists, type-6 records, rucksack), typed(), Block (IF context)

RULE_ID = 'c'
ACTOR = 0xffff
CREATE_CLONE = {36: 0, 44: 1, 84: 1}          # verb -> operand index of the cloned object
MOVERS = {1: 0, 41: 0, 73: 1, 35: 0}          # verb -> operand index of the object that keeps its id and becomes takeable
# events whose push site exists but whose firing condition is not shown for scripted objects in general (effects.EVENT class '?')
WEAK_EVENTS = {1: 'producers $00a114/$00fa62, conditions unread', 4: 'thrown object hits the gate object ($00f328), not driven',
               10: 'region test $009286, conditions unread', 11: 'fall to z 0 ($00f69c); driven for urns 452/453/198 (mechanics.md "The scroll half"), not for this owner',
               12: 'mover op 4 ($00f9a2)', 13: 'anim op $f8 ($00b0f0)', 25: 'producer $00f0c8 unread'}
# (level, owner object, event) deliveries driven live: the bottle 465 thrown in room 86 pushes event 11 and its block moves key 508 there
# (`l1_objects/bottle_throw.py`, the room entered by an injected teleport)
DRIVEN = {(1, 465, 11)}
PUSH_SCAN_OUT = ROOT / 'scratchpad/cadaver/lint/push_sites_scan.out'   # written by lint.py's scan
EVENT_NAME = {0: 'TAKE', 5: 'operate', 6: 'room entry', 7: 'facing', 9: 'touch', 11: 'ev11', 12: 'mover op 4', 13: 'ev13', 14: 'room tick',
              15: 'hero region', 16: 'EXAMINE', 17: 'object region', 18: 'APPLY item', 19: 'verb 9', 20: 'countdown', 23: 'kill',
              24: 'spell', 26: 'GIVE item', 27: 'SELECT', 28: 'first entry'}


def _producers(ctx):
    p = getattr(ctx, 'producers', None)
    if p is not None: return set(p), 'ctx.producers'
    if PUSH_SCAN_OUT.exists():
        ev = {int(m.group(1)) for m in re.finditer(r'^\s+event\s+(\d+):', PUSH_SCAN_OUT.read_text(), re.M)}
        if ev: return ev, str(PUSH_SCAN_OUT.relative_to(ROOT))
    return None, 'none (producer test skipped)'


def _rows(b):
    """-> (kind, owner id, event, ebyte, gate bytes, model.Block rows with IF context)"""
    kind = getattr(b, 'kind', None) or b.owner.split()[0]
    oid = getattr(b, 'oid', None)
    if oid is None: oid = int(str(b.owner).split()[-1])
    ebyte = getattr(b, 'ebyte', b.event)
    ops = [o for o in b.ops if o[1] != -2]
    mb = M.Block(kind, oid, 0, getattr(b, 'start', 0), ebyte, ops)
    return kind, oid, b.event, ebyte, mb.gate, mb.rows


class World:
    def __init__(self, ctx):
        self.S = S = M.Snap(ctx.snap)
        self.rooms = S.rooms()
        self.lists = {r: [o for o in S.roomlist(r) if o] for r in self.rooms}
        self.loc = collections.defaultdict(set)
        for r, lst in self.lists.items():
            for o in lst: self.loc[o].add(r)
        n, ruck = S.rucksack(); self.ruck = [o for o, t in ruck[:n]]
        self.start = S.cur_room()
        self.flags = S.flags()
        self.owners = collections.defaultdict(set)
        for r, rm in self.rooms.items():
            for d in rm['doors']: self.owners[d].add(r)
        self.blocks = []
        for b in ctx.blocks:
            kind, oid, ev, ebyte, gate, rows = _rows(b)
            rr = []
            for d, v, ta, name, gctx in rows:
                ta = [oid if (kind == 'obj' and x == ACTOR) else x for x in ta] if v in MOVERS or v in CREATE_CLONE or v == 37 else ta
                rr.append((d, v, ta, name, gctx))
            self.blocks.append(dict(b=b, kind=kind, oid=oid, event=ev, ebyte=ebyte, gate=gate, rows=rr, owner=b.owner))
        self._place_closure()
        self._reach()

    # object location sets under scripts: list rooms + PLACE targets + MOVE (to the source's rooms), to a fixpoint
    def site_rooms(self, blk):
        if blk['kind'] == 'room': return {blk['oid']}
        return set(self.oloc.get(blk['oid'], ())) | ({'ANY'} if blk['oid'] in self.ruck else set())

    def _place_closure(self):
        self.oloc = collections.defaultdict(set, {o: set(r) for o, r in self.loc.items()})
        changed = True
        while changed:
            changed = False
            for blk in self.blocks:
                site = self.site_rooms(blk)
                for d, v, ta, name, g in blk['rows']:
                    new = set()
                    if v == 41:
                        o = ta[0]; new = set(site) if ta[1] == 254 else {ta[1]}
                    elif v == 73:
                        o = ta[1]; new = set(self.oloc.get(ta[0], ()))
                    else: continue
                    if o == ACTOR: continue
                    if not new <= self.oloc[o]: self.oloc[o] |= new; changed = True

    def _reach(self, closed=()):
        R = {self.start}; changed = True
        while changed:
            changed = False
            for d, rs in self.owners.items():
                if d in closed: continue
                if rs & R and not rs <= R: R |= rs; changed = True
            for blk in self.blocks:
                site = self.site_rooms(blk)
                if not ('ANY' in site or site & R): continue
                for dd, v, ta, name, g in blk['rows']:
                    if v == 37 and ta[0] in self.rooms and ta[0] not in R: R.add(ta[0]); changed = True
        if not closed: self.reach = R
        return R

    def key_behind_own_doors(self, key, doors):
        """closure with every door keyed by `key` shut: can the key still be reached (listed visible in a reached room, or a
        non-clone script route whose block runs in a reached room)?  -> (ok, closure size, rooms of the key)"""
        R = self._reach(closed=set(doors))
        r = self.routes(key)
        ok = bool(r['ruck'])
        if r['listed'] and not r['hidden'] and set(r['listed']) & R: ok = True
        for blk, v, ta, g in r['script'] + (r['show'] if r['listed'] else []):
            s = self.site_rooms(blk)
            if 'ANY' in s or s & R: ok = True
        return ok, len(R), sorted(x for x in self.oloc.get(key, ()) if x != 'ANY')

    def label(self, o):
        for blk in self.blocks:
            if blk['kind'] == 'obj' and blk['oid'] == o and blk['event'] == 16:
                for d, v, ta, name, g in blk['rows']:
                    if v == 72:
                        import verb_decode as vd
                        return vd.TEXT.get(ta[0], '')
        return ''

    def bid(self, blk):
        return '%s%d ev%d%s' % ('o' if blk['kind'] == 'obj' else 'r', blk['oid'], blk['event'], '' if blk['ebyte'] != 0xff else ' SPENT')

    # ---------------------------------------------------------------- obtainability of one object id
    def routes(self, o):
        ob = self.S.obj(o)
        r = dict(obj=ob is not None, listed=sorted(self.loc.get(o, ())), hidden=bool(ob and ob['b3'] & 0x80), ruck=o in self.ruck,
                 script=[], clones=[], show=[])
        cls = self.S.cls(o) if ob else None
        r['takeable'] = bool(cls and cls['b12'] & 2)
        for blk in self.blocks:
            for d, v, ta, name, g in blk['rows']:
                if v in MOVERS and ta[MOVERS[v]] == o:
                    (r['show'] if v == 1 else r['script']).append((blk, v, ta, g))
                if v in CREATE_CLONE and ta[CREATE_CLONE[v]] == o:
                    r['clones'].append((blk, v, ta, g))
        return r

    def obtainable(self, o, depth=0, seen=None):
        """-> (verdict, reason).  verdict: 'start', 'placed', 'script', 'script-dubious', 'placed-unreachable', 'never', 'not-object'"""
        seen = set() if seen is None else seen
        r = self.routes(o)
        if not r['obj']: return 'not-object', 'id %d resolves to no type-6 record' % o
        if r['ruck']: return 'start', 'in the snapshot rucksack'
        if r['listed'] and not r['hidden']:
            if set(r['listed']) & self.reach: return 'placed', 'room list %s' % r['listed']
        cand = list(r['script']) + (list(r['show']) if r['listed'] else [])
        if not cand:
            if r['listed'] and not r['hidden']:
                return 'placed-unreachable', 'listed in room %s, outside the generous reach closure' % r['listed']
            return 'never', ('listed in %s but hidden and no SHOW' % r['listed']) if r['listed'] else 'in no room list, no script places it'
        if o in seen or depth > 4: return 'script-dubious', 'cyclic dependency'
        seen = seen | {o}
        good, bad = [], []
        for blk, v, ta, g in cand:
            why = self.dubious(blk, g, depth, seen)
            (bad if why else good).append((blk, v, why))
        pre = ('listed in room %s outside the reach closure; ' % r['listed']) if r['listed'] and not r['hidden'] else \
              ('listed hidden in room %s; ' % r['listed']) if r['listed'] else 'in no room list; '
        if good:
            return 'script', pre + '; '.join('%s verb %d' % (self.bid(b), v) for b, v, w in good)
        return 'script-dubious', pre + '; '.join('%s verb %d [%s]' % (self.bid(b), v, w) for b, v, w in bad)

    def dubious(self, blk, guards, depth, seen):
        why = []
        if self.producers is not None and blk['event'] not in self.producers: why.append('event %d has no push site' % blk['event'])
        if blk['ebyte'] == 0xff: why.append('block spent in this snapshot')
        site = self.site_rooms(blk)
        if blk['kind'] == 'obj' and not site: why.append('owner %d is in no room and not carried' % blk['oid'])
        elif 'ANY' not in site and not site & self.reach: why.append('owner rooms %s outside the reach closure' % sorted(site))
        items = []
        if blk['event'] in (18, 26) and len(blk['gate']) == 2:
            w = (blk['gate'][0] << 8) | blk['gate'][1]
            if w < 0x8000: items.append(('gate', w))
        for v, n, conds, br in guards:
            for cv, cta in conds:
                if cv == 34 and br == 'then' and v in (14, 58): items.append(('guard', cta[0]))
        for k, it in items:
            vd_, rs = self.obtainable(it, depth + 1, seen)
            if vd_ in ('never', 'not-object', 'placed-unreachable', 'script-dubious'):
                why.append('%s item %d is %s (%s)' % (k, it, vd_, rs))
        return '; '.join(why)


def rule(ctx):
    import verb_decode as vd
    if not vd.TEXT: vd.load_text(ctx.snap)
    W = World(ctx)
    W.producers, psrc = _producers(ctx)
    lv = ctx.level
    notes = getattr(ctx, 'notes', None)
    if notes is None: notes = ctx.notes = []
    # keyed doors: at load, and made keyed by verb 27
    keyed = []        # (door, key, how)
    doors = sorted(W.owners)
    for d in doors:
        f = W.flags.get(d)
        if f and f['word'] not in (0, 0xffff): keyed.append((d, f['word'], 'load +7=$%02x' % f['b7']))
    set27 = []
    for blk in W.blocks:
        for dd, v, ta, name, g in blk['rows']:
            if v == 27:
                set27.append((ta[0], ta[1], W.bid(blk)))
                if ta[0] in W.owners and ta[1] not in (0, 0xffff): keyed.append((ta[0], ta[1], 'verb 27 by %s' % W.bid(blk)))
    nonroom_items = sorted(n for n, f in W.flags.items() if n not in W.owners and f['word'] not in (0, 0xffff))
    out = []; tally = collections.Counter(); per = []
    for d, key, how in keyed:
        verdict, reason = W.obtainable(key)
        tally[verdict] += 1
        r = W.routes(key)
        rooms = sorted(W.owners[d]); f = W.flags[d]
        extra = []
        if r['obj'] and not r['takeable']: extra.append('template b12 bit 1 clear: icon 2 TAKE not offered')
        if r['clones']: extra.append('clone-only creators (new id, never this key): %s' % ', '.join('%s verb %d' % (W.bid(b), v) for b, v, ta, g in r['clones']))
        openers = [W.bid(b) for b in W.blocks for x in b['rows'] if x[1] == 10 and x[2][0] == d]
        if openers: extra.append('also cleared by verb 10 in %s' % ', '.join(openers))
        if not f['b7'] & 0x20: extra.append('+7 bit 5 clear: UNLOCK DOOR spell opens it')
        label = W.label(key) if r['obj'] else ''
        row = dict(door=d, rooms=rooms, key=key, how=how, verdict=verdict, reason=reason, label=label, listed=r['listed'],
                   hidden=r['hidden'], extra=extra)
        head = 'door $%02x (rooms %s, %s) key %d%s' % (d, '/'.join(map(str, rooms)), how, key, ' "%s"' % label[:40] if label else '')
        tail = ('; ' + '; '.join(extra)) if extra else ''
        if verdict in ('start', 'placed', 'script'):
            # the key exists somewhere reachable; is it reachable with every door this key opens still shut?
            same = [dd for dd, kk, hh in keyed if kk == key]
            ok, nR, krooms = W.key_behind_own_doors(key, same)
            row['own_door'] = (ok, nR)
            if not ok:
                out.append(dict(rule='c', level=lv, owner='door $%02x' % d, event=-1, detail='%s: BEHIND ITS OWN DOOR: with %s shut the closure is %d rooms '
                                'and holds none of the key rooms %s (%s)%s' % (head, ','.join('$%02x' % x for x in same), nR, krooms, reason, tail)))
            if verdict == 'script':
                evs = {int(m.group(1)) for m in re.finditer(r' ev(\d+)', reason)}
                weak = evs & set(WEAK_EVENTS)
                pairs = {(lv, int(o), int(e)) for o, e in re.findall(r'o(\d+) ev(\d+)', reason)}
                if pairs and pairs <= DRIVEN: weak = set()
                if weak and evs <= set(WEAK_EVENTS):
                    out.append(dict(rule='c', level=lv, owner='door $%02x' % d, event=min(weak), detail='%s: SCRIPT-ONLY, WEAK TRIGGER: %s; event(s) %s: %s%s' % (
                        head, reason, sorted(weak), '; '.join(WEAK_EVENTS[e] for e in sorted(weak)), tail)))
            per.append(row); continue
        per.append(row)
        kind = 'SCRIPT-ONLY, DUBIOUS TRIGGER' if verdict == 'script-dubious' else 'KEY NOT AN OBJECT' if verdict == 'not-object' else 'NEVER OBTAINABLE'
        out.append(dict(rule='c', level=lv, owner='door $%02x' % d, event=-1, detail='%s: %s (%s), %s%s' % (head, kind, verdict, reason, tail)))
    nblk = len(W.blocks); nob = sum(1 for b in W.blocks if b['kind'] == 'obj')
    notes.append('c L%d census: %d rooms (type-3) and their type-5 lists walked (%d listed object entries, %d distinct objects); %d doors named by '
                 'room lists, %d keyed at load, %d made keyed by verb 27 (of %d verb-27 sites %s); %d type-4 records not named by a room with an '
                 'item-like word %s; %d blocks walked (%d object, %d room); creator verbs counted: SHOW 1 (listed hidden keys), PLACE 41, MOVE 73, '
                 'PUT IN RUCK 35; clone verbs 36/44/84 listed only; rucksack %s; start room %d; reach closure %d of %d rooms (outside: %s); '
                 'producers from %s' % (lv, len(W.rooms), sum(len(l) for l in W.lists.values()), len(W.loc), len(doors),
                                        sum(1 for k in keyed if k[2].startswith('load')), sum(1 for k in keyed if not k[2].startswith('load')),
                                        len(set27), set27, len(nonroom_items), nonroom_items, nblk, nob, nblk - nob, W.ruck, W.start,
                                        len(W.reach), len(W.rooms), sorted(set(W.rooms) - W.reach), psrc))
    notes.append('c L%d verdicts: %s' % (lv, dict(tally)))
    for row in per:
        notes.append('c L%d   door $%02x rooms %s %s key %d "%s": %s (%s); key reachable with its own doors shut (ok, closure): %s%s' % (
            lv, row['door'], row['rooms'], row['how'], row['key'], row['label'][:36], row['verdict'], row['reason'], row.get('own_door'),
            (' | ' + '; '.join(row['extra'])) if row['extra'] else ''))
    return out


# ---------------------------------------------------------------- standalone
def _load_ctx(level, snap):
    import importlib.util
    spec = importlib.util.spec_from_file_location('lint_abf_lint', str(HERE / 'lint.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m.load_level(level, snap, None)


if __name__ == '__main__':
    import verb_decode as vd
    snaps = [(0, str(ROOT / 'scratchpad/cadaver/gameplay_empire.snap')), (1, str(ROOT / 'scratchpad/cadaver/level1_loaded.snap'))]
    want = [int(sys.argv[i + 1]) for i, a in enumerate(sys.argv) if a == '--level'] or [0, 1]
    for level, snap in snaps:
        if level not in want: continue
        ctx = _load_ctx(level, snap)
        vd.TEXT.clear()
        fs = rule(ctx)
        for n in ctx.notes: print('note ' + n)
        print('findings L%d: %d' % (level, len(fs)))
        for f in fs: print('%s L%d %-9s ev %2d  %s' % (f['rule'], f['level'], f['owner'], f['event'], f['detail']))
        print()
