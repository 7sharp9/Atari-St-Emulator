"""lint_rule_e.py: Cadaver script linter, rule (e): gates and conditions that can never pass.

    rule(ctx) -> [ {rule:'e', level, owner, event, detail, kind, census} ... ]
    ctx: .snap (snapshot path), .level (0/1), .blocks = [(owner, event, decoded_ops)] where decoded_ops is the list of
    verb_decode.decode_block() rows (the GATE row -1 first).  owner may be ('obj', id) / ('room', slot), 'obj 81' / 'room 27',
    or 'o81' / 'r27'.  event is the raw event byte (bit 7 = keep) or the masked event; when every event is < $80 the keep
    bits are re-read from the snapshot's own block lists (verb_decode.collect / room_blocks), since the variable analysis needs them.

Standalone (from M68000/, or anywhere below the directory holding tools/rdis.py):
    .venv/bin/python reversing/cadaver/py/secrets/overlay/lint/lint_rule_e.py [--census]
        lints scratchpad/cadaver/gameplay_empire.snap (level 0) and scratchpad/cadaver/level1_loaded.snap (level 1).

Checks (the census each one uses is printed with --census and carried in each finding's `census` field):
  gate-id       event 4/9/18/26 gate word names an object id with no type-6 record in the level (event 9 bit 15 = wildcard)
  gate-item     event 18/26 gate word names an object that can never be in the rucksack: its template has no TAKE icon
                (template +12 bit 1, $0094c0) and no verb 35 / level-carry list (1044(A5)) / initial rucksack puts it there   [read]
  gate-spell    event 1 gate byte: no object whose body byte 0 equals it (the item's spell id, $00fece)                      [read]
  gate-mover    event 12 gate byte: the owner's mover program (rec+rec[13]+14, ops 00/4 01/2 02/1 03/2 04/2) has no `04 n`
  gate-anim     event 13 gate byte: the owner's template anim script (T+$28, word(T+34)/2 pairs) has no `$f8 n`
  gate-region   event 15/17 gate byte outside 1..N regions of the room
  gate-19/20    event 19/20 gate byte that no verb 9 / verb 42 argument of the level supplies (the only producers: $010c4e, $010c78)
  gate-2        any block answering event 2 (the gate $00fe84[2] always rejects) or event 8 (consumer diverts before the gate)
  no-producer   blocks answering events 3 and 21 (no push site in any image, secrets.md)
  cond-obj      COND 16/19/43/47/56/57 naming an object id with no type-6 record
  cond-bit      COND 16/19/30 on a state bit (+3 bit 0 / bit 1) that is clear at load and that no verb of the level sets
                (verbs 17, 24, 32, 33 / 20, 25; room blocks with `actor` = any object; the engine never writes them, secrets.md)
  cond-var      COND 40 on VAR n for a value no reachable value satisfies (init, verb 38 sets, verb 39 adds: repeatable when the
                block keeps or its owner is cloned; native: timer handler 7 `addq.b #1,2299(A5)` = VAR 17 += 1)
  cond-rand     COND 80 on 2520(A5) == n outside every writer's range (verb 79 lo..hi, verb 81 VAR copy; block-local when the
                block itself wrote 2520 before the test)
  cond-shield   COND 76 bit n > 6 (writers $04ccf6 bset D0 with potion bits 0-3, $04cd18 $7f)
  cond-tmpl     COND 91 n not the template of the owner (object block) / of any object of the level (room block)
  cond-room     COND 43 room n not a type-3 slot; or object that is never in room n: not there at load, not takeable, not a
                creature, no mover, no verb 41/73 moving it there                                                    [read]
  counter       an IF that does not see every condition (counter_census.py): 14/48 after != 1 conditions, 58/59 n after != n
"""
import sys, os, collections, math
from pathlib import Path


def _root():
    r = os.environ.get('M68000_ROOT')
    if r: return Path(r)
    for p in [Path.cwd(), *Path.cwd().parents, Path(__file__).resolve().parent, *Path(__file__).resolve().parents]:
        if (p / 'tools' / 'rdis.py').exists(): return p
    raise SystemExit('cannot find the M68000 root (tools/rdis.py); set M68000_ROOT')


ROOT = _root()
os.environ.setdefault('M68000_ROOT', str(ROOT))
sys.path.insert(0, str(ROOT / 'reversing/cadaver/py/secrets/overlay/graph'))
from model import Snap, typed, u16, u32, CONDS, IFVERBS  # noqa: E402
import model  # noqa: E402
vd = model.vd
rb = model.rb

STANDALONE = False   # True when run on its own: then it also reports the no-producer blocks rule b owns under lint.py
SNAPS = {0: str(ROOT / 'scratchpad/cadaver/gameplay_empire.snap'), 1: str(ROOT / 'scratchpad/cadaver/level1_loaded.snap')}
ACTOR = 0xffff
VAR_N = 2458 - 2282          # VAR bytes 2282(A5) .. 2457(A5); the timer table starts at 2458
NATIVE_VAR_ADD = {17: 'timer-expiry handler 7 `addq.b #1,2299(A5)` (level-0 overlay $04d124, level-1 $04d0a2; find_field_writers.py)'}
MOVER_LEN = {0: 4, 1: 2, 2: 1, 3: 2, 4: 2}


# ------------------------------------------------------------------------------------------------ input normalisation
def _owner(o):
    if isinstance(o, tuple): return o[0][0], int(o[1])
    s = str(o).strip()
    if ' ' in s:
        k, n = s.split(None, 1); return k[0], int(n)
    return s[0], int(s[1:])


class B:
    """one block: kind 'o'/'r', owner id, event, keep, gate bytes, rows (depth, verb, typed args)"""
    def __init__(self, kind, owner, e, ops, keep=None):
        self.kind, self.owner = kind, owner
        self.event = e & 0x7f; self.keep = bool(e & 0x80) if keep is None else keep
        self.gate = []; self.rows = []
        for d, v, args, name in ops:
            if v == -1: self.gate = [int(x, 16) for x in args]; continue
            if v < 0: continue
            self.rows.append((d, v, typed(v, args)))

    @property
    def tag(self): return '%s %d' % ('obj' if self.kind == 'o' else 'room', self.owner)


def _decode(e, body):
    try: return vd.decode_block(e, body)
    except vd.Bad: return vd.decode_block(e, body[:-1])


def own_blocks(snap):
    """the snapshot's blocks with raw event bytes: object +$10 lists (collect(), the two +$20 aliases dropped) and room lists"""
    out = []
    for oid, start, e, body in vd.collect(snap):
        if start == 0x10: out.append((('obj', oid), e, _decode(e, body)))
    for slot, e, body, off in rb.room_blocks(snap)[0]:
        out.append((('room', slot), e, _decode(e, body)))
    return out


# ------------------------------------------------------------------------------------------------ level model
class Level:
    def __init__(self, snap, level, blocks):
        self.s = Snap(snap); self.level = level
        # lint.py's Block namedtuples carry the raw event byte as .ebyte; take (owner, ebyte, ops) from them
        raw = [(b.owner, b.ebyte, b.ops) if hasattr(b, 'ebyte') else b for b in blocks]
        if raw and all((e & 0x80) == 0 for _, e, _ in raw):
            # caller masked the keep bit: take the keep bits from the snapshot's own lists, matched in order per owner
            keep = collections.defaultdict(list)
            for o, e, ops in own_blocks(snap): keep[_owner(o)].append(bool(e & 0x80))
            seen = collections.defaultdict(int); self.blocks = []
            for o, e, ops in raw:
                k = _owner(o); i = seen[k]; seen[k] += 1
                self.blocks.append(B(k[0], k[1], e, ops, keep[k][i] if i < len(keep[k]) else True))
        else:
            self.blocks = [B(*_owner(o), e, ops) for o, e, ops in raw]
        s = self.s
        self.ids = set(s.obj_ids())
        self.max_id = max(self.ids)
        self.obj = {i: s.obj(i) for i in self.ids}
        self.rooms = s.rooms()
        self.lists = {r: s.roomlist(r) for r in self.rooms}
        self.room_of = collections.defaultdict(set)
        for r, lst in self.lists.items():
            for o in lst: self.room_of[o].add(r)
        n, ruck = s.rucksack(); self.ruck0 = {o for o, t in ruck}
        a = u32(s.ram, s.a5 + 1044); self.carry = set()
        # the level-start carry list read by $00e5c0 only after verb 51 (2525(A5) set): [id.w][n.w][n+1 bytes if n] ..., id < 0 ends
        while level > 0:
            i = u16(s.ram, a)
            if i & 0x8000: break
            k = u16(s.ram, a + 2); self.carry.add(i); a += 4 + (k + 1 if k else 0)
            if len(self.carry) > 64: break
        # who writes what
        self.cloned = set(); self.verb_rows = collections.defaultdict(list)
        for b in self.blocks:
            for d, v, a_ in b.rows:
                self.verb_rows[v].append((b, d, a_))
                if v in (36,): self.cloned.add(self.res(b, a_[0]))
                if v in (44, 84): self.cloned.add(self.res(b, a_[1]))

    def res(self, b, o):
        """an object operand: `actor` is the owner in an object block and any object in a room block (None)"""
        if o == ACTOR: return b.owner if b.kind == 'o' else None
        return o

    def tmpl_addr(self, oid):
        o = self.obj.get(oid)
        return None if o is None else self.s.tmpl2(o['tmpl'])

    def takeable(self, oid):
        """the TAKE icon 2 rule $0094c0: template +12 bit 1 and record +15 bit 2 (LOCK) clear; LOCK is undone by verb 55"""
        t = self.tmpl_addr(oid)
        return t is not None and bool(self.s.ram[t + 12] & 2)

    def can_hold(self, oid):
        if oid in self.ruck0 or oid in self.carry: return 'in the rucksack at load / level carry list'
        if self.takeable(oid): return 'TAKE icon (template +12 bit 1)'
        for b, d, a in self.verb_rows[35]:
            if self.res(b, a[0]) in (oid, None): return 'verb 35 in %s ev %d' % (b.tag, b.event)
        return None

    def body0(self, oid):
        a = self.obj[oid]['addr']; return self.s.ram[a + self.s.ram[a + 12]]

    def mover_ops4(self, oid):
        o = self.obj.get(oid)
        if o is None: return None
        r = self.s.ram; a = o['addr']; m, end = r[a + 13], r[a + 14]
        if not m or end - m <= 14: return set()
        p = m + 14; out = set()
        while p < end:
            op = r[a + p]
            if op not in MOVER_LEN: break
            if op == 4: out.add(r[a + p + 1])
            p += MOVER_LEN[op]
        return out

    def anim_f8(self, oid):
        t = self.tmpl_addr(oid)
        if t is None: return None
        r = self.s.ram; n = u16(r, t + 34) // 2
        return {r[t + 0x28 + 2 * i + 1] for i in range(n) if r[t + 0x28 + 2 * i] == 0xf8}

    # ---- state bits: (initial, writers)
    def bit_writers(self, oid, bit):
        setv = {0: (17, 24), 1: (20, 25)}[bit]; own = (32, 33) if bit == 0 else ()
        w = []
        for v in setv:
            for b, d, a in self.verb_rows[v]:
                t = self.res(b, a[0])
                if t == oid or t is None: w.append('%s ev %d verb %d%s' % (b.tag, b.event, v, '' if t == oid else ' (actor of a room block)'))
        for v in own:
            for b, d, a in self.verb_rows[v]:
                if (b.kind == 'o' and b.owner == oid) or b.kind == 'r':
                    w.append('%s ev %d verb %d (own bit)' % (b.tag, b.event, v))
        return w

    # ---- variables
    def var_model(self, n, prior=None):
        """-> (reachable value set, census text).  Over-approximation: safe for 'never' claims."""
        init = {self.s.var(n)} | (prior or set())
        sets = set(); adds = []; cen = []
        for b, d, a in self.verb_rows[38]:
            if a[0] == n: sets.add(a[1]); cen.append('%s ev %d VAR=%d' % (b.tag, b.event, a[1]))
        for b, d, a in self.verb_rows[39]:
            if a[0] == n:
                rep = b.keep or (b.kind == 'o' and b.owner in self.cloned)
                adds.append((a[1], rep)); cen.append('%s ev %d VAR+=%d%s' % (b.tag, b.event, a[1], ' keep' if rep else ' once'))
        for v in (62, 63):
            for b, d, a in self.verb_rows[v]:
                if 2282 <= a[0] < 2282 + VAR_N and a[0] - 2282 == n: return set(range(256)), cen + ['verb %d writes it' % v]
        if n in NATIVE_VAR_ADD:
            adds.append((1, True)); cen.append('native: ' + NATIVE_VAR_ADD[n])
        base = init | sets
        if any(rep and inc % 256 for inc, rep in adds):
            g = 256
            for inc, rep in adds:
                if rep: g = math.gcd(g, inc % 256)
            reach = set()
            for b0 in base:
                reach |= {(b0 + k * g) & 255 for k in range(256)}
            # the one-shot adds on top
            for inc, rep in adds:
                if not rep: reach |= {(x + inc) & 255 for x in reach}
            return reach, cen
        reach = set(base)
        for inc, rep in adds:
            reach |= {(x + inc) & 255 for x in reach}
        return reach, cen


OPS = {0: lambda x, v: x > v, 1: lambda x, v: x < v, 2: lambda x, v: x == v}


def cmp(op, x, v): return OPS.get(op, lambda x, v: x != v)(x, v)


# ------------------------------------------------------------------------------------------------ the rule
def rule(ctx, prior_vars=None):
    L = Level(ctx.snap, ctx.level, ctx.blocks)
    out = []

    def F(b, kind, detail, census, tag=''):
        out.append(dict(rule='e', level=ctx.level, owner=b.tag, event=b.event, kind=kind, detail=detail + tag, census=census))

    ids_cen = 'type-6 index: %d records, ids 0..%d, absent %s' % (len(L.ids), L.max_id, sorted(set(range(L.max_id + 1)) - L.ids))
    v9 = {a[0] for b, d, a in L.verb_rows[9]}; v42 = {a[0] for b, d, a in L.verb_rows[42]}
    for b in L.blocks:
        g = b.gate; w = (g[0] << 8 | g[1]) if len(g) == 2 else None
        # ---- (1) gates
        if b.event in (4, 9, 18, 26) and w is not None and not (b.event == 9 and w & 0x8000):
            if w not in L.ids:
                F(b, 'gate-id', 'gate word %d names no object (event %d)' % (w, b.event), ids_cen)
            elif b.event in (18, 26) and not L.can_hold(w):
                F(b, 'gate-item', 'gate word %d: the item can never be in the rucksack (template +12 bit 1 clear, not carried, no verb 35)' % w,
                  'TAKE rule $0094c0; rucksack writers $c42a callers $a14a TAKE, $e5ec level carry, $0107fa verb 35', ' [read]')
        if b.event == 1 and g:
            src = [o for o in L.ids if L.body0(o) == g[0] and L.can_hold(o)]
            if not src:
                F(b, 'gate-spell', 'gate byte %d: no holdable object has body byte 0 = %d' % (g[0], g[0]), ids_cen, ' [read]')
        if b.event == 12 and g and b.kind == 'o':
            ops = L.mover_ops4(b.owner)
            if g[0] not in (ops or set()):
                F(b, 'gate-mover', 'gate byte %d: the mover program of %d has op-4 operands %s' % (g[0], b.owner, sorted(ops) if ops is not None else 'none (no record)'),
                  'mover program at rec+rec[13]+14, ops 00/01/02/03/04 lengths 4/2/1/2/2 (mover_prog_census.py)')
        if b.event == 13 and g and b.kind == 'o':
            f8 = L.anim_f8(b.owner)
            if g[0] not in (f8 or set()):
                F(b, 'gate-anim', 'gate byte %d: the anim script of %d (template %s) has $f8 operands %s' % (g[0], b.owner, L.obj[b.owner]['tmpl'] if b.owner in L.obj else '?', sorted(f8) if f8 is not None else 'none'),
                  'anim script T+$28, word(T+34)/2 pairs; clones share the template')
        if b.event in (15, 17) and g and b.kind == 'r':
            n = len(L.rooms[b.owner]['regions']) if b.owner in L.rooms else 0
            if not 1 <= g[0] <= n:
                F(b, 'gate-region', 'region byte %d, room has %d regions' % (g[0], n), 'room region list (model.Snap.rooms)')
        if b.event == 19 and g and g[0] not in v9:
            F(b, 'gate-19', 'gate byte %d; verb 9 arguments in this level: %s' % (g[0], sorted(v9)),
              'event 19 is pushed only by verb 9 ($010c4e); verb 9 rows: %s' % ['%s ev %d' % (x.tag, x.event) for x, d, a in L.verb_rows[9]])
        if b.event == 20 and g and g[0] not in v42:
            F(b, 'gate-20', 'gate byte %d; verb 42 first operands in this level: %s' % (g[0], sorted(v42)),
              'event 20 is pushed only by the countdown $0090c2-$0090dc with word = 2462(A5); writers of 2462(A5): $010c78 verb 42 (first operand), '
              '$0069e0 and $0090c2 ($ff = off) (find_field_writers.py, both levels); verb 42 rows: %s' % ['%s ev %d %s' % (x.tag, x.event, a) for x, d, a in L.verb_rows[42]])
        if b.event in (2, 8):
            F(b, 'gate-2', 'event %d block can never run' % b.event, 'gate table $00fe84 entry 2 rejects; event 8 diverted at the consumer')
        if b.event in (3, 21) and STANDALONE:   # under lint.py, rule b reports these from the live push-site scan
            F(b, 'no-producer', 'event %d has no push site (secrets.md "Events 3 and 21 have no producer")' % b.event, 'push_sites_scan.py: 0 computed-opcode pushes')
        # ---- (2) conditions
        local_rand = None
        for d, v, a in b.rows:
            if v in (79, 81):
                new = set(range(a[0], a[1] + 1)) if v == 79 else L.var_model(a[0], (prior_vars or {}).get(a[0]))[0]
                local_rand = new if d == 0 else ((local_rand if local_rand is not None else rand_all) | new)
            if v not in CONDS: continue
            if v in (16, 19, 34, 43, 47, 56, 57):
                o = L.res(b, a[0])
                if o is not None and o not in L.ids:
                    F(b, 'cond-obj', 'COND %d names object %d, which has no record' % (v, o), ids_cen)
                    continue
                if v in (34, 57) and o is not None and not L.can_hold(o):
                    F(b, 'cond-item', 'COND %d: object %d can never be in the rucksack / selected' % (v, o),
                      'TAKE rule $0094c0; rucksack writers $c42a callers $a14a TAKE, $e5ec level carry, $0107fa verb 35', ' [read]')
                    continue
            if v in (16, 19, 30):
                o = L.res(b, a[0]) if v != 30 else (b.owner if b.kind == 'o' else None)
                if o is None: continue
                bit = 1 if v == 19 else 0
                init = (L.obj[o]['b3'] >> bit) & 1
                ws = L.bit_writers(o, bit)
                if not init and not ws:
                    F(b, 'cond-bit', 'COND %d: object %d state bit %d is clear at load and no verb of the level sets it' % (v, o, bit),
                      'setters searched: verbs %s over %d blocks (room-block actor writes count as any object); engine never writes +3 bits 0/1 (secrets.md)'
                      % ('17, 24, 32, 33' if bit == 0 else '20, 25', len(L.blocks)))
            if v == 40:
                n, op, val = a
                if n >= VAR_N:
                    F(b, 'cond-var', 'COND 40 VAR %d beyond the %d variables' % (n, VAR_N), ''); continue
                reach, cen = L.var_model(n, (prior_vars or {}).get(n))
                if not any(cmp(op, x, val) for x in reach):
                    F(b, 'cond-var', 'COND 40 VAR %d %s %d: reachable values %s' % (n, ['>', '<', '=='][op] if op < 3 else '!=', val, sorted(reach)),
                      'init %d%s; writers %s; lea 2282(A5) only in verbs 38/39/40/81' % (L.s.var(n), ' + prior level' if prior_vars else '', cen))
            if v == 80:
                if local_rand is not None: reach = local_rand; src = 'block-local writer'
                else: reach = rand_all; src = 'all writers'
                if a[0] not in reach:
                    F(b, 'cond-rand', 'COND 80 2520(A5) == %d: %s give %s' % (a[0], src, sorted(reach)), rand_cen)
            if v == 76 and a[0] > 6:
                F(b, 'cond-shield', 'COND 76 shield bit %d: writers set bits 0-6 only' % a[0], '$04ccf6 bset, $04cd18 #$7f')
            if v == 91:
                tm = {L.obj[o]['tmpl'] for o in L.ids}
                if b.kind == 'o':
                    own = L.obj[b.owner]['tmpl']
                    if own != a[0]: F(b, 'cond-tmpl', 'COND 91 template %d; the running object %d has template %d' % (a[0], b.owner, own), '')
                elif a[0] not in tm:
                    F(b, 'cond-tmpl', 'COND 91 template %d: no object of the level has it' % a[0], 'templates of %d records' % len(L.ids))
            if v == 43:
                o, rm = L.res(b, a[0]), a[1]
                if rm != 0xfe and rm not in L.rooms:
                    F(b, 'cond-room', 'COND 43 room %d is no room' % rm, 'type-3 slots %d' % len(L.rooms)); continue
                if o is None or rm == 0xfe: continue
                movers = [('%s ev %d v41' % (x.tag, x.event)) for x, dd, aa in L.verb_rows[41] if L.res(x, aa[0]) in (o, None) and aa[1] in (rm, 0xfe)]
                movers += [('%s ev %d v73' % (x.tag, x.event)) for x, dd, aa in L.verb_rows[73] if L.res(x, aa[1]) in (o, None)]
                t = L.tmpl_addr(o); cls = L.s.ram[t + 22] if t else None
                mov = L.obj[o]['b3'] & 0x10
                if rm not in L.room_of.get(o, ()) and not L.can_hold(o) and cls != 3 and not mov and not movers:
                    F(b, 'cond-room', 'COND 43 object %d in room %d: it is in %s at load and nothing can move it there' % (o, rm, sorted(L.room_of.get(o, ())) or 'no room list'),
                      'checked: type-5 lists, TAKE/carry, class 3, mover bit, verbs 41/73', ' [read]')
        # ---- (4) counter discipline (counter_census.py)
        since = collections.defaultdict(list)
        for d, v, a in b.rows:
            if v in CONDS: since[d].append((v, a))
            elif v in IFVERBS:
                k = a[0] if v in (58, 59) else None; cs = since[d]; since[d] = []
                if (v in (14, 48) and len(cs) != 1) or (v in (58, 59) and len(cs) != k):
                    F(b, 'counter', 'IF %d%s after %d condition(s) %s: %s' % (
                        v, '' if k is None else ' n=%d' % k, len(cs), ['%d %s' % (cv, ca) for cv, ca in cs],
                        'only the last decides' if v in (14, 48) else ('58 0 is true exactly when the last is false, so the earlier ones have no effect' if k == 0 else 'the count is not n')),
                      'counter_census.py rule: every COND clears 2270(A5) when false, every IF clears it ($01062c, $010660)', ' [read]')
    return out


def _rand_model(L, prior_vars=None):
    reach = {L.s.ram[L.s.a5 + 2520]}; cen = ['init %d' % L.s.ram[L.s.a5 + 2520]]
    for b, d, a in L.verb_rows[79]: reach |= set(range(a[0], a[1] + 1)); cen.append('%s ev %d RANDOM %d..%d' % (b.tag, b.event, a[0], a[1]))
    for b, d, a in L.verb_rows[81]:
        r, _ = L.var_model(a[0], (prior_vars or {}).get(a[0])); reach |= r; cen.append('%s ev %d 2520=VAR %d' % (b.tag, b.event, a[0]))
    return reach, 'writers of 2520(A5): $010f36 verb 79, $010c48 verb 81 (find_field_writers.py); ' + '; '.join(cen)


# rule() reads these two module globals for verb 80; set them per level
rand_all, rand_cen = set(range(256)), ''
_rule = rule


def rule(ctx, prior_vars=None):  # noqa: F811  (wrapper: compute the 2520 model first)
    global rand_all, rand_cen
    L = Level(ctx.snap, ctx.level, ctx.blocks)
    rand_all, rand_cen = _rand_model(L, prior_vars)
    return _rule(ctx, prior_vars)


class Ctx:
    def __init__(self, snap, level, blocks=None):
        self.snap, self.level = snap, level
        self.blocks = blocks if blocks is not None else own_blocks(snap)


def var_reach(snap, level):
    L = Level(snap, level, own_blocks(snap))
    return {n: L.var_model(n)[0] for n in range(VAR_N)}


if __name__ == '__main__':
    STANDALONE = True
    prior = None; allf = []
    for lev in (0, 1):
        ctx = Ctx(SNAPS[lev], lev)
        f = rule(ctx)
        # level 1 again with level 0's reachable variable values as possible initial values (whether the level start keeps
        # 2282(A5) is not established): a level-1 cond-var finding is reported only if it holds both ways
        if lev == 1:
            prior = var_reach(SNAPS[0], 0)
            f2 = {(x['owner'], x['event'], x['detail'].split(':')[0]) for x in rule(ctx, prior) if x['kind'] == 'cond-var'}
            for x in f:
                if x['kind'] == 'cond-var' and (x['owner'], x['event'], x['detail'].split(':')[0]) not in f2:
                    x['detail'] += '  (holds only if the level start resets the variables)'
        L = Level(ctx.snap, lev, ctx.blocks)
        kinds = collections.Counter(x['kind'] for x in f)
        print('== level %d  %s: %d blocks (%d object, %d room), %d findings %s' % (
            lev, Path(ctx.snap).name, len(L.blocks), sum(b.kind == 'o' for b in L.blocks), sum(b.kind == 'r' for b in L.blocks), len(f), dict(kinds)))
        for x in f:
            print('  [%s] %-9s ev %-2d %s' % (x['kind'], x['owner'], x['event'], x['detail']))
            if '--census' in sys.argv and x['census']: print('        census: %s' % x['census'])
        allf += f
