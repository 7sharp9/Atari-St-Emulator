"""graph.py [outdir]: A1 (Cadaver 91st pass).  Whole-corpus dataflow graph of the level-1 scripts, static, from the decode that
verb_decode.collect() and room_blocks.room_blocks() already produce against scratchpad/cadaver/level1_loaded.snap
(initial level-1 state) and the lineage state scratchpad/cadaver/s90/run1/end_room90.snap (room 90, health 60).
Writes into <outdir>:
  blocks.txt     every script block (440 object + 90 room), its trigger, gate, guard context and verb effects
  xref.txt       per node (flag/door, var, timer, item, item template, state bits, existence, anim/mover/acti, lock,
                 q66, room events 19/20, teleport targets, gold/xp/health) every WRITER and READER block with owner, event, gate, guard
  teleports.txt  every verb 37 (room -> room, coords, owner, event, gate, guard) and every PLACE into another room
  locations.txt  where every object sits (type-5 room lists, hidden bit, template idx), key/item census, who moves it
  notes.txt      decode-vs-doc disagreements and the proof lines of the static checks
Run from M68000/:  .venv/bin/python reversing/cadaver/py/secrets/overlay/graph/graph.py [outdir]   (outdir: argv, else $OUTDIR, else scratchpad/cadaver/s91_graph;
snapshots: $CAD_LEVEL1_SNAP, $CAD_LINEAGE_SNAP; see model.py)"""
import sys, os, collections, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from model import *
import effects as fx

# ---------------------------------------------------------------- build
class World:
    def __init__(self, init_path=L1, lin_path=LINEAGE):
        self.s = Snap(init_path); self.l = Snap(lin_path) if lin_path else None
        vd.load_text(init_path)
        self.text = dict(vd.TEXT)
        self.blocks, self.skipped = load_blocks(self.s)
        self.rooms = self.s.rooms()
        self.flags = self.s.flags()
        self.lists = {r: self.s.roomlist(r) for r in self.rooms}
        self.objs = {o: self.s.obj(o) for o in self.s.obj_ids()}
        self.loc = collections.defaultdict(list)
        for r, lst in self.lists.items():
            for o in lst:
                if o: self.loc[o].append(r)
        self.spent = self._spent()
        self.lineage = self._lineage() if self.l else {}
        # node tables
        self.W = collections.defaultdict(list); self.R = collections.defaultdict(list)
        for b in self.blocks:
            ow = b.owner if b.kind == 'obj' else None
            for gi, (node, det) in enumerate(fx.gate_reads(b.event, b.gate)):
                self.R[node].append((b, None, det, ()))
            for row in b.rows:
                d, v, a, name, ctx = row
                for rw, node, det in fx.effects(ow, v, a):
                    (self.W if rw == 'W' else self.R)[node].append((b, row, det, ctx))
        # examine text of each object (first DESCRIBE of its event-16 block)
        self.label = {}
        for b in self.blocks:
            if b.kind == 'obj' and b.event == 16:
                for d, v, a, name, ctx in b.rows:
                    if v == 72: self.label.setdefault(b.owner, self.text.get(a[0], '?')); break

    # ------------------------------------------------------------ lineage (live-state snapshot reads)
    def _spent(self):
        """blocks whose event byte reads $ff in the lineage snapshot but not in the initial one (consumed non-keep blocks)"""
        out = set()
        if not self.l: return out
        init = collections.defaultdict(list); lin = collections.defaultdict(list)
        for oid, st, e, body in vd.collect(self.s.path): init[oid].append(e)
        for oid, st, e, body in vd.collect(self.l.path): lin[oid].append(e)
        for oid, es in init.items():
            ls = lin.get(oid)
            if ls and len(ls) == len(es):
                for i, (a, b) in enumerate(zip(es, ls)):
                    if a != b: out.add(('obj', oid, i))
        ri = collections.defaultdict(list); rl = collections.defaultdict(list)
        for slot, e, body, off in rb.room_blocks(self.s.path)[0]: ri[slot].append(e)
        for slot, e, body, off in rb.room_blocks(self.l.path)[0]: rl[slot].append(e)
        for slot, es in ri.items():
            ls = rl.get(slot)
            if ls and len(ls) == len(es):
                for i, (a, b) in enumerate(zip(es, ls)):
                    if a != b: out.add(('room', slot, i))
        return out

    def _lineage(self):
        L = self.l
        n, ruck = L.rucksack()
        d = dict(room=L.cur_room(), vars={i: L.var(i) for i in range(20)}, ruck=ruck[:n], nruck=n,
                 flags={k: v['word'] for k, v in L.flags().items()},
                 lists={r: L.roomlist(r) for r in L.rooms()},
                 health=u16(L.ram, L.a5 + 1174), gold=u32(L.ram, L.a5 + 1188), xp=u32(L.ram, L.a5 + 1192))
        d['loc'] = collections.defaultdict(list)
        for r, lst in d['lists'].items():
            for o in lst:
                if o: d['loc'][o].append(r)
        return d

    # ------------------------------------------------------------ naming helpers
    def oname(self, o):
        if o in ('ACTOR', None): return 'ACTOR'
        t = self.label.get(o)
        return '%d' % o + (' "%s"' % t[:34] if t else '')

    def icon(self, b):
        """static icon rule ($0094c0-$009538 object panel, $009f80-$009fba item panel) for the player events 0, 5, 16, 18, 26; '' for the others"""
        if b.kind != 'obj' or b.event not in (0, 5, 16, 18, 26): return ''
        c = self.s.cls(b.owner)
        if c is None: return ' icon?'
        tab = bytes(self.s.ram[0x5c1c:0x5c1c + 0x100])
        if b.event == 0: ok = bool(c['b12'] & 2)
        elif b.event == 5: ok = tab[c['b23']] in (3, 4, 7, 8, 9)
        elif b.event == 16: ok = c['b23'] != 6 and not (c['b22'] & 0x80)
        elif b.event == 18: ok = c['b22'] == 11 or c['b22'] == 8
        else: ok = c['b22'] == 12
        return ' icon-ok' if ok else ' icon-NO'

    def bid(self, b): return '%s%d.%d@%d' % ('o' if b.kind == 'obj' else 'r', b.owner, b.idx, b.event)

    def where(self, b):
        if b.kind == 'room': return 'room %d' % b.owner
        rs = self.loc.get(b.owner, [])
        return 'in ' + ','.join(map(str, rs)) if rs else 'not in a type-5 list'

    def fmtnode(self, node):
        k, key = node[0], node[1]
        if k == 'flag':
            f = self.flags.get(key); w = ' ($%04x)' % f['word'] if f else ''
            return 'flag %d=$%02x%s' % (key, key, w)
        return '%s(%s)' % (k, key)

    def cond_text(self, v, ta, ow):
        e = fx.effects(ow, v, list(ta))
        return ' '.join('%s' % self.fmtnode(n) + ':' + det for rw, n, det in e) or 'cond%d' % v

    def guard(self, b, ctx):
        ow = b.owner if b.kind == 'obj' else None
        parts = []
        for v, n, conds, br in ctx:
            ct = ' & '.join(self.cond_text(cv, cta, ow) for cv, cta in conds) or '?'
            if v == 14: t = ('if [%s]' if br == 'then' else 'if NOT [%s]') % ct
            elif v == 48: t = ('if NOT [%s]' if br == 'then' else 'if [%s]') % ct
            elif v == 58: t = ('count==%d of [%s]' if br == 'then' else 'count!=%d of [%s]') % (n, ct)
            else: t = ('count!=%d of [%s]' if br == 'then' else 'count==%d of [%s]') % (n, ct)
            parts.append(t)
        return '; '.join(parts)

    def head(self, b, row=None, ctx=None, det=''):
        """one line: block id, owner (+label, rooms), event, keep, gate, spent in lineage, guard, effect"""
        ev = '%d%s' % (b.event, '+' if b.keep else '')
        g = fx.gate_text(b.event, b.gate)
        sp = ' SPENT@lineage' if (b.kind, b.owner, b.idx) in self.spent else ''
        s = '%-12s %s%s  %s ev %s%s gate[%s]%s' % (self.bid(b), 'obj ' if b.kind == 'obj' else 'room ',
                                                 self.oname(b.owner) if b.kind == 'obj' else b.owner, self.where(b), ev,
                                                 ' ' + fx.EVENT[b.event][1] + self.icon(b), g, sp)
        if ctx is not None:
            gd = self.guard(b, ctx)
            if gd: s += ' | ' + gd
        if det: s += ' => ' + det
        return s


# ---------------------------------------------------------------- reports
def write_blocks(w, path):
    out = []
    for b in sorted(w.blocks, key=lambda b: (b.kind, b.owner, b.idx)):
        out.append(w.head(b) + '  [%s]' % fx.EVENT[b.event][0])
        for d, v, a, name, ctx in b.rows:
            if v in (22, 23): continue
            effs = fx.effects(b.owner if b.kind == 'obj' else None, v, a)
            txt = '; '.join('%s %s' % (rw, det) if False else '%s %s: %s' % (rw, w.fmtnode(n), det) for rw, n, det in effs)
            if v in (28, 72): txt = 'text %d "%s"' % (a[0], w.text.get(a[0], '?'))
            out.append('    %s%2d %-34s %s%s' % ('  ' * d, v, name[:34], ' '.join(map(str, a)), '   -> ' + txt if txt else ''))
    Path(path).write_text('\n'.join(out) + '\n')


KINDS = [('flag', 'FLAGS AND DOORS (type-4 record +2 word)'), ('var', 'SCRIPT VARIABLES (bytes at 2282(A5)+n)'),
         ('timer', 'TIMERS (verb 49)'), ('item', 'TYPE-8 ITEMS by OBJECT id (record word +0)'),
         ('item_used', 'EVENT 18 / 26 GATE WORDS (item object id the block is waiting for)'),
         ('itemtmpl', 'TYPE-8 ITEMS by TEMPLATE idx (verb 82, record word +2)'),
         ('state0', 'OBJECT STATE BIT 0'), ('state1', 'OBJECT STATE BIT 1'), ('exist', 'OBJECT EXISTENCE / PLACEMENT'),
         ('lock', 'LOCK (+15 bit 2)'), ('anim', 'ANIMATION (GOANI/STOPANI)'), ('mover', 'MOVER (GOMOVE/STOPMOVE)'),
         ('acti', 'ACTI (GOACTI/STOPACTI)'), ('q66', 'VERB 66 CLASS QUEUE'), ('ev23', 'KILL (event 23)'), ('ev0', 'event 0 queued by verb 35'),
         ('roomev19', 'ROOM EVENT 19 (verb 9)'), ('roomev20', 'ROOM EVENT 20 (verb 42 countdown)'), ('tele', 'TELEPORT TARGETS'),
         ('roomlist', 'ROOM LISTS (verb 41 targets)'), ('gold', 'GOLD'), ('xp', 'XP'), ('health', 'HEALTH'), ('creature', 'CREATURE REGISTRY'),
         ('rand', 'RANDOM'), ('shield', 'SHIELD'), ('level', 'LEVEL START'), ('region', 'REGION GATES (events 15/17)'), ('spell', 'SPELL GATES (event 24)')]

NATIVE = {
    ('flag', None): ['native R: portal crossing ($00716e): word 0 opens, $ffff blocks (sound cue only), a positive word is an item OBJECT id looked up by $011256 in the rucksack; descriptor byte +7 bit 1 consumes the key and clears the word, bit 2 clears it and keeps the key',
                     'native W: overlay spell 8 UNLOCK DOOR (word := 0 unless descriptor +7 bit 5) and spell 16 LOCK DOOR (word := $ffff); the key-consume path above'],
    ('var', 17): ['native W: timer-expiry handler 7 (`addq.b #1,2299(A5)` at $04d0a2 in the level-1 overlay) increments var 17 (unused by any level-1 script)'],
    ('timer', None): ['native R: timer tick $00904e dispatches the overlay table-3 handler: 0 poison end, 1 poison tick, 2-5 clear shield bit n, 6 clear all shields, 7 var 17 += 1'],
    ('item', None): ['native W: TAKE icon 2 ($00c42a) appends the record [object id][template idx]; DROP/THROW and icon $c apply ($00c3d4) remove it; event-18 on a class-8 container moves the id into the container'],
    ('state0', None): ['native R/W: operate icons toggle bit 0 of the record (+3) of levers/chests; class handlers read it'],
}


def kindsort(n):
    k, key = n[0], n[1]
    return (0, key) if isinstance(key, int) else (1, 0 if key is None else 0)


def write_xref(w, path):
    out = []
    for kind, title in KINDS:
        nodes = sorted({n for n in list(w.W) + list(w.R) if n[0] == kind}, key=lambda n: (str(type(n[1])), n[1] if isinstance(n[1], int) else 0))
        if not nodes: continue
        out.append('=' * 100); out.append(title); out.append('=' * 100)
        for n in nodes:
            hd = w.fmtnode(n)
            if kind in ('item', 'exist', 'state0', 'state1', 'lock', 'anim', 'mover', 'acti', 'q66', 'ev23', 'ev0') and isinstance(n[1], int):
                hd += '   ' + w.oname(n[1]).split(' ', 1)[1] if ' ' in w.oname(n[1]) else ''
                o = w.objs.get(n[1])
                if o: hd += '   [in %s; template %d; hidden=%d]' % (','.join(map(str, w.loc.get(n[1], []))) or '-', o['tmpl'], (o['b3'] >> 7) & 1)
            if kind == 'flag':
                fl = w.flags.get(n[1])
                if fl:
                    lw = w.lineage['flags'].get(n[1]) if w.lineage else None
                    owners = [r for r, rr in w.rooms.items() if n[1] in rr['doors']]
                    hd += '   initial $%04x, lineage $%s, door of rooms %s, desc +7=$%02x' % (fl['word'], '%04x' % lw if lw is not None else '?', owners or '-', fl['b7'])
            if kind == 'var' and w.lineage:
                hd += '   initial 0, lineage %d' % w.lineage['vars'].get(n[1], -1)
            out.append(hd)
            nat = NATIVE.get((kind, n[1])) or NATIVE.get((kind, None)) if kind in ('flag', 'var', 'timer', 'item', 'state0') else None
            if kind == 'var' and n[1] != 17: nat = None
            for t in (nat or []): out.append('      * ' + t)
            for tag, tab in (('W', w.W), ('R', w.R)):
                for (b, row, det, ctx) in sorted(tab.get(n, []), key=lambda t: (t[0].kind, t[0].owner, t[0].idx)):
                    out.append('   %s %s' % (tag, w.head(b, row, ctx, det)))
            if not w.W.get(n) and kind in ('flag', 'var', 'timer', 'item', 'state0', 'state1', 'item_used'):
                out.append('   (no script writer%s)' % ('' if not (nat) else '; native writers above'))
            if not w.R.get(n) and kind in ('flag', 'var', 'timer', 'state0', 'state1'):
                out.append('   (no script reader)')
        out.append('')
    Path(path).write_text('\n'.join(out) + '\n')


def write_teleports(w, path):
    out = ['TELEPORTS (verb 37) and cross-room PLACEs (verb 41 into room r) in level 1; guards are the COND verbs in front of the IF that contains the verb',
           'initial state = level1_loaded.snap; "block spent" means the lineage snapshot (room 90) already shows the block consumed', '']
    for (rw, tab) in (('TELEPORT', w.W),):
        rows = []
        for n in sorted({n for n in w.W if n[0] == 'tele'}, key=lambda n: n[1]):
            for (b, row, det, ctx) in w.W[n]:
                rows.append((n[1], b, row, det, ctx))
        for dest, b, row, det, ctx in sorted(rows, key=lambda t: (t[1].kind, t[1].owner, t[1].idx)):
            a = row[2]
            src = ('room %d' % b.owner) if b.kind == 'room' else ','.join(map(str, w.loc.get(b.owner, []))) or '?'
            out.append('%-8s -> room %-3d at (%d,%d,%d)   %s' % ('from ' + src, a[0], a[1], a[2], a[3], w.head(b, row, ctx)))
    out.append('')
    out.append('PLACE (verb 41) into a different room, and objects moved by verb 73 (position and room of the first operand):')
    for n in sorted({n for n in w.W if n[0] == 'roomlist'}, key=lambda n: str(n[1])):
        for (b, row, det, ctx) in w.W[n]:
            out.append('  %s: %s' % (n[1], w.head(b, row, ctx, '%s %s' % ('', row[2]))))
    Path(path).write_text('\n'.join(out) + '\n')


def write_locations(w, path):
    out = ['OBJECT LOCATIONS (type-5 lists of level1_loaded.snap; lineage = end_room90.snap).  template = record word +6 (the second word of a rucksack record)', '']
    keyobj = sorted({n[1] for n in list(w.R) + list(w.W) if n[0] in ('item', 'item_used', 'itemtmpl') and isinstance(n[1], int)})
    items = [n[1] for n in w.R if n[0] == 'item' and isinstance(n[1], int)] + [n[1] for n in w.R if n[0] == 'item_used']
    out.append('items named by a gate (verb 34/57, event 18/26 gate word) or a door word:')
    names = set(items) | {f['word'] for f in w.flags.values() if 0 < f['word'] < 0x8000}
    for o in sorted(names):
        ob = w.objs.get(o)
        lin = w.lineage['loc'].get(o, []) if w.lineage else []
        ruck = [r for r in w.lineage['ruck'] if r[0] == o] if w.lineage else []
        users = sorted({(b.kind, b.owner, b.event) for t in (w.R,) for n in (('item', o), ('item_used', o)) for (b, row, det, ctx) in t.get(n, [])})
        doors = [k for k, f in w.flags.items() if f['word'] == o]
        movers = sorted({(b.kind, b.owner, b.event) for n in (('exist', o), ('item', o)) for (b, row, det, ctx) in w.W.get(n, [])})
        out.append('  item %-4d %-40s template %-4s room list %-8s hidden %s lineage list %s ruck %s | gates in %s | doors %s | script-placed by %s' % (
            o, (w.label.get(o) or '')[:40], ob['tmpl'] if ob else '-', w.loc.get(o, '-'), ((ob['b3'] >> 7) & 1) if ob else '-', lin or '-', ruck or '-',
            users[:6], doors or '-', movers[:6]))
    out.append('')
    out.append('ALL objects by room (initial type-5 lists); h = hidden bit set; * = has script blocks:')
    have = {b.owner for b in w.blocks if b.kind == 'obj'}
    for r in sorted(w.lists):
        cell = []
        for o in w.lists[r]:
            if not o: continue
            ob = w.objs.get(o)
            cell.append('%d%s%s' % (o, 'h' if ob and ob['b3'] & 0x80 else '', '*' if o in have else ''))
        out.append('  room %-3d rect %-18s doors %-22s %s' % (r, w.rooms[r]['rect'], ','.join('$%02x' % d for d in w.rooms[r]['doors']), ' '.join(cell)))
    Path(path).write_text('\n'.join(out) + '\n')


def write_notes(w, path):
    s = w.s; L = w.l
    out = ['DECODE vs DOC vs BRIEF (each line: claim, evidence, label)', '']
    art = object3_artifact(s, w.skipped)
    out.append('1. "object 3 +$20 event $1a": object 3 is a 16-byte template (record bytes 0..15, count byte 11 = %d); verb_decode.collect() also tries a second list at +$20 with the count at +31, which for a 16-byte record lies in the NEXT record (object 4, record start = object 3 + $10): its +$10 list. Evidence: %s = (object, neighbour whose record starts at +$10, blocks, identical to the neighbour own +$10 blocks, count byte 11, count byte 31). secrets.md "No object block uses the second list at +$20" is RIGHT; the 442 count of level 1 is 440 real object blocks + 2 artifacts. PROVEN (static, 2 of 2 artifacts, level 1; level 0 shows the same two).' % (art[0][4], art))
    t6 = [i for i in s.obj_ids()]
    out.append('2. type-8 item ids: the brief says a type-8 id is the TEMPLATE index. Verb 34, verb 57, the event-18/26 gate word and the positive door words are all compared with the record word +0 = OBJECT id ($011256 `cmp.w 0(A0,D3.w),D2`, $00ff38/$00ff26 compare 1156(A5) = the queue word 4(A1) = object id: 1262(A5) = $00a8 for the pickaxe 168). Only verb 82 compares word +2 (template idx, $010f5c). Live: edges_live.py checks verb 34 (object id 680 found, template 93 not found) and 720 event 18 (word 690 object id matches, word 45 = its template idx does not). PROVEN (listing + 4 live rows).')
    out.append('3. verb 40 operand order is (n, op, value) ($010c06-$010c12: D0 = n, D1 = op, D2 = value), the order verb_decode names it ("VAR n op v") but NOT the order of this pass first reading; every table here uses (n, op, value). Live rows in edges_live.py. PROVEN.')
    out.append('4. verb 48 runs its then-part when the condition counter is ZERO ($010606 `tst.b 2270(A5); bne skip`), verb 14 when non-zero; verb_decode.VERBS[48] and the secrets.md verb table name 48 "IF NOT (2270 == 0)", which reads as the opposite. Live rows (callcap, both counter values) in edges_live.py. PROVEN. (The prose of secrets.md "48 when it is zero" is right.)')
    out.append('5. verb 73: the first operand is the position source (stays), the SECOND operand moves ($010a7c: first $010738 result -> A2 = source, second -> the object placed); verb_decode.VERBS[73] says "MOVE object o1 to the position of o2" (reversed); secrets.md table says "MOVE o2 to the position and room of o1" (right). Static + verbs2 proof (#12 moved to the room of #107). PROVEN.')
    out.append('6. room_object_census.resolve() used to keep only 16 bits of the 17-bit offset of a resource index entry (entry long & $1ffff, size = entry >> 17); fixed in the 91st pass. Type 2 (class templates, data $5115a, 255 slots) has 155 entries with bit 16 set (index 100-254), so every class/template read through resolve() for those had been taken $10000 too low (41 of the 135 populated level-1 templates, 32 with a different class byte); types 3-6 are below $10000 and were unaffected. Corrected item_census.py / class_census.py / potion_amounts.py outputs are in secrets.md "Dead and unreferenced content". model.Snap.tmpl2()/cls() read type 2 from the whole offset. PROVEN (live: the placement entry of object 719 in room 2 has live record $63df8 = template 111 at $53df8 + $10000, class 11, name SLOT).')
    n, ruck = L.rucksack()
    out.append('7. Handoff says the lineage rucksack "holds only the scroll 378"; end_room90.snap holds count %d record %s (object 680 DISPELL TRAP, template 93, from the start room 96); 378 (MIND BLAST) still lies in room 31. PROVEN (snapshot read, edges_live row).' % (n, ruck))
    out.append('8. Doors: a type-4 record names the destination only through its candidate coordinate; every door is listed by exactly two rooms and is used here as an undirected link of its two owners (door_walk.py agrees for level 0). Door $79 owners [53, 90], $74 [17, 87], $67 [76, 82]. INFERRED for direction (no crossing driven in this pass); the lineage passed $7b (12-90) and $7a (12-31) naturally.')
    out.append('9. Room entry deletes: room 87 entry block r87.1@6 runs verb 82 for template idx 51, 52, 53, 93, 115, 140; scroll class-1 objects are template 93, so entering room 87 removes the UNLOCK DOOR scroll 407 (and 680): everything that needs the spell must be done before the first entry (plan_full.py does). Static; sim only.')
    out.append('10. Room 4 re-closes door $01 on every entry (r4.0@6 SET FLAG $01 = $ffff); with the opener 27 in room 89 only, rooms 4-8 are a pocket: exits are door $10 (opener 698 apply key 251, both in room 6) or the pit (region 1, event 15 -> room 94). Live row: injected event 6 for room 4 sets door $01 back to $ffff. PROVEN.')
    out.append('11. Events with block content but no or unread producer: events 3 and 21 none (3 blocks of event 21, 4 of event 3 in level 0); events 1, 10, 11, 12, 13, 25: producer sites exist, conditions unread; event 4 = a thrown/launched object hits object X (queue [4][projectile][word = id of the object hit], $00f2d8-$00f328; blocks answer on the PROJECTILE with gate word = target id): 17 blocks (the urn 611 and emerald 730/731 at Captain Axel 413 in room 87, gold bags at 334, bottles at 476). INFERRED from the listing, not driven.')
    out.append('12. Native writers outside the script verbs: VAR 17 by timer handler 7 (addq.b #1,2299(A5) at $04d0a2, no level-1 script uses VAR 17); door words by the overlay spells UNLOCK DOOR (8, scroll 407/542) and LOCK DOOR (16) and by the key-consuming door crossing; type-8 by TAKE/drop/throw/give. A whole-image + overlay grep finds `lea 2282(A5)` only in verbs 38, 39, 40, 81 ($010be6, $010bf4, $010c08, $010c42). PROVEN (static, cad_all.asm and overlay_level1.lst).')
    Path(path).write_text('\n'.join(out) + '\n')


def main():
    outdir = Path(sys.argv[1]) if len(sys.argv) > 1 else OUTDIR
    outdir.mkdir(exist_ok=True)
    w = World()
    write_blocks(w, outdir / 'blocks.txt')
    write_xref(w, outdir / 'xref.txt')
    write_teleports(w, outdir / 'teleports.txt')
    write_locations(w, outdir / 'locations.txt')
    write_notes(w, outdir / 'notes.txt')
    nobj = sum(1 for b in w.blocks if b.kind == 'obj'); nroom = len(w.blocks) - nobj
    print('blocks: %d object + %d room; skipped +$20 object hits: %d' % (nobj, nroom, len(w.skipped)))
    print('nodes with a writer: %d, with a reader: %d' % (len(w.W), len(w.R)))
    print('object3 artifact:', object3_artifact(w.s, w.skipped))
    print('wrote', outdir)
    return w


if __name__ == '__main__':
    main()
