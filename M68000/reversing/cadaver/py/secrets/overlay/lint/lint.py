"""lint.py [--rule ID ...] [--level 0|1] [--plugin-dir DIR ...] [--no-scan]: a rule-registry linter over every shipped script
block of the two Cadaver level snapshots (level 0 `scratchpad/cadaver/gameplay_empire.snap`, level 1 `scratchpad/cadaver/level1_loaded.snap`).

Blocks: object blocks from `verb_decode.collect()` and room blocks from `room_blocks.room_blocks()`, decoded with `verb_decode.decode_block()`
(a room block whose content has odd length carries one uninitialised pad byte; it is decoded without it, as `counter_census.py` does).
`collect()` walks 315 (level 0) / 442 (level 1) entries; two per level are aliases (the `+$20` probe of a 16-byte header-only record lands
in the next record's `+$10` list: object 69 -> 70, object 3 -> 4; `events/second_list_alias.py`). The context keeps every walked entry in
`ctx.walked` and the distinct blocks (aliases dropped: a `+$20` list verified byte-equal to a prefix of another object's `+$10` list) in `ctx.blocks`; rules use `ctx.blocks`.

Rule interface: `rule(ctx) -> iterable of Finding` (or of 5-tuples / dicts with keys rule, level, owner, event, detail).
ctx fields: snap, level, blocks = [Block(owner, event, ops, kind, oid, start, ebyte, body)], walked (same, aliases included),
producers (set of event numbers some push site queues, from push_sites_scan.py; None with --no-scan), notes (list a rule may append to).
`owner` is 'obj N' or 'room N'; `event` is `ebyte & 0x7f` (bit 7 is the keep bit); `ops` is decode_block()'s list of (depth, verb, args, name)
with verb -1 = the gate, -2 = $17 padding, and an attached ELSE part as (depth, 15, ['len n'], 'ELSE').
Built-in rules: a (verb 5 / 85 reward sites), b (blocks answering an event no push site queues), f (bare verb 15 outside an IF).
Plug-ins: every `lint_rule_*.py` next to this file and in each --plugin-dir, exposing `rule(ctx)` and optionally `RULE_ID` (default: the
part of the file name after `lint_rule_`).

Run from anywhere:  M68000/.venv/bin/python M68000/reversing/cadaver/py/secrets/overlay/lint/lint.py [--rule a]"""
import sys, os, glob, re, subprocess, importlib.util, collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ['M68000_ROOT']) if os.environ.get('M68000_ROOT') else next(p for p in HERE.parents if (p / 'tools/rdis.py').exists())
os.chdir(ROOT)
for p in ('reversing/cadaver/py/secrets/overlay', 'reversing/cadaver/py', 'tools'):
    sys.path.insert(0, str(ROOT / p))
import verb_decode as vd
from room_blocks import room_blocks

SNAPS = [(0, str(ROOT / 'scratchpad/cadaver/gameplay_empire.snap')), (1, str(ROOT / 'scratchpad/cadaver/level1_loaded.snap'))]
PUSH_SCAN = ROOT / 'reversing/cadaver/py/secrets/overlay/events/push_sites_scan.py'
SCAN_OUT = ROOT / 'scratchpad/cadaver/lint/push_scan'   # whole-image listings and the scan's output

Finding = collections.namedtuple('Finding', 'rule level owner event detail')
Block = collections.namedtuple('Block', 'owner event ops kind oid start ebyte body')


class Ctx:
    def __init__(self, snap, level, walked, blocks, producers):
        self.snap, self.level, self.walked, self.blocks, self.producers = snap, level, walked, blocks, producers
        self.notes = []


def compact(ops):
    """one-line body: gate then verbs, `v(args)`, IF parts in [ ], padding dropped"""
    s = []; depth = 0
    for d, v, args, name in ops:
        while depth > d: s.append(']'); depth -= 1
        if v == -2: continue
        if v == -1:
            if args: s.append('gate(%s)' % ' '.join(args))
            continue
        s.append('%d(%s)' % (v, ' '.join(args)) if args else str(v))
        if v in (14, 48, 58, 59) or (v == 15 and name == 'ELSE'): s.append('['); depth = d + 1
    s += [']'] * depth
    return ' '.join(s).replace('[ ', '[').replace(' ]', ']')


def decode_room(e, body):
    try: return vd.decode_block(e, body)
    except vd.Bad: return vd.decode_block(e, body[:-1])   # odd content length: one uninitialised pad byte


def load_level(level, snap, producers):
    raw = vd.collect(snap)
    walked = []
    for oid, start, e, body in raw:
        walked.append(Block('obj %d' % oid, e & 0x7f, vd.decode_block(e, body), 'obj', oid, start, e, body))
    # aliases: a +$20 list of object N whose blocks equal object M's +$10 list (M the next record)
    lists = collections.defaultdict(list)
    for b in walked: lists[(b.oid, b.start)].append((b.ebyte, b.body))
    alias = {}
    for (oid, start), bl in lists.items():
        if start != 0x20: continue
        for (o2, s2), bl2 in lists.items():
            # a prefix, not equality: byte 31 of the header-only record is the neighbour's byte 15, which need not equal its count
            # (level 0: object 69 reads 2 of object 70's 5 blocks)
            if s2 == 0x10 and o2 != oid and bl2[:len(bl)] == bl: alias[(oid, start)] = o2
    blocks = [b for b in walked if (b.oid, b.start) not in alias]
    rows, problems, nrooms = room_blocks(snap)
    for slot, e, body, off in rows:
        b = Block('room %d' % slot, e & 0x7f, decode_room(e, body), 'room', slot, off, e, body)
        walked.append(b); blocks.append(b)
    ctx = Ctx(snap, level, walked, blocks, producers)
    ctx.notes.append('L%d: %d object entries walked by collect(), %d aliased (%s), %d distinct object blocks; %d room blocks; room_blocks problems %d'
                     % (level, len(raw), sum(1 for b in walked if b.kind == 'obj' and (b.oid, b.start) in alias),
                        ', '.join('obj %d +$20 = obj %d +$10' % (k[0], v) for k, v in sorted(alias.items())),
                        sum(1 for b in blocks if b.kind == 'obj'), len(rows), len(problems)))
    return ctx


def scan_producers():
    """run push_sites_scan.py (cached whole-image listings under SCAN_OUT) and parse its 'event NN:' table"""
    env = dict(os.environ, OUTDIR=str(SCAN_OUT), M68000_ROOT=str(ROOT))
    out = subprocess.run([sys.executable, str(PUSH_SCAN)], capture_output=True, text=True, check=True, cwd=ROOT, env=env).stdout
    SCAN_OUT.mkdir(parents=True, exist_ok=True); (SCAN_OUT.parent / 'push_sites_scan.out').write_text(out)
    ev = {int(m.group(1)) for m in re.finditer(r'^\s+event\s+(\d+):', out, re.M)}
    census = [l.strip() for l in out.splitlines() if 'instructions' in l and 'pointer loads' in l]
    computed = re.search(r'computed-opcode pushes.*?: (\d+)', out).group(1)
    other = re.search(r'not a recognised push.*?: (\d+)', out).group(1)
    return ev, census, computed, other


# ---------------------------------------------------------------- built-in rules

def rule_a(ctx):
    """a: every verb 5 / verb 85 site; the handler pays 26 XP whatever the operand (secrets.md "Two corrections"), so operand != 26 is flagged"""
    asked = collections.Counter(); sites = collections.Counter(); kinds = collections.Counter()
    for b in ctx.blocks:
        for d, v, args, name in b.ops:
            if v not in (5, 85): continue
            n = int(args[0], 16)
            if v == 85 and n >= 0x8000: n -= 0x10000
            pays = 26 if (v == 5 or n > 0) else 'XP := 0'
            sites[v] += 1; asked[v] += n; kinds[(v, b.kind)] += 1
            yield Finding('a', ctx.level, b.owner, b.event, 'verb %d operand %d, pays %s%s' % (v, n, pays, '' if n == 26 else '  [operand != 26]'))
    ctx.notes.append('a L%d: verb 5 sites %d (obj %d, room %d) asking %d XP; verb 85 sites %d (obj %d, room %d) asking %d XP; pays %d'
                     % (ctx.level, sites[5], kinds[(5, 'obj')], kinds[(5, 'room')], asked[5], sites[85], kinds[(85, 'obj')], kinds[(85, 'room')],
                        asked[85], 26 * (sites[5] + sites[85])))
    walked5 = sum(1 for b in ctx.walked for o in b.ops if o[1] in (5, 85))
    ctx.notes.append('a L%d: sites counted over walked entries (aliases included): %d' % (ctx.level, walked5))


def rule_b(ctx):
    """b: a block whose event no push site queues (producers from push_sites_scan.py)"""
    if ctx.producers is None:
        ctx.notes.append('b L%d: skipped (--no-scan)' % ctx.level); return
    ev = collections.Counter(b.event for b in ctx.blocks)
    orphan = sorted(e for e in ev if e not in ctx.producers)
    ctx.notes.append('b L%d: block events %s; with no producer: %s' % (ctx.level, dict(sorted(ev.items())), orphan))
    spent = [b.owner for b in ctx.blocks if b.ebyte == 0xff]
    if spent: ctx.notes.append('b L%d: spent ($ff) blocks: %s' % (ctx.level, spent))
    for b in ctx.blocks:
        if b.event not in ctx.producers:
            yield Finding('b', ctx.level, b.owner, b.event, 'no producer for event %d (keep=%d): %s' % (b.event, b.ebyte >> 7, compact(b.ops)))


def rule_f(ctx):
    """f: verb 15 reached as a verb (not the $0f right after an IF's then part); executing it asserts ELSE SHOULDNT BE CALLED"""
    attached = bare = ifs = 0
    for b in ctx.blocks:
        for d, v, args, name in b.ops:
            if v in (14, 48, 58, 59): ifs += 1
            if v != 15: continue
            if name == 'ELSE' and args and args[0].startswith('len'): attached += 1
            else:
                bare += 1
                yield Finding('f', ctx.level, b.owner, b.event, 'bare verb 15 at depth %d: %s' % (d, compact(b.ops)))
    # independent check: re-decode every block with verb 15 removed from the grammar; parse() then raises on any $0f read as a verb,
    # while an attached ELSE is consumed by the IF branch before the verb lookup
    saved = vd.VERBS.pop(15); fail = []
    try:
        for b in ctx.blocks:
            try: (decode_room if b.kind == 'room' else vd.decode_block)(b.ebyte, b.body)
            except vd.Bad as ex: fail.append('%s: %s' % (b.owner, ex))
    finally: vd.VERBS[15] = saved
    ctx.notes.append('f L%d: IF verbs %d, ELSE parts attached to an IF %d, bare verb 15 %d; re-decode without verb 15 in the grammar: %d of %d blocks fail %s'
                     % (ctx.level, ifs, attached, bare, len(fail), len(ctx.blocks), fail))


RULES = collections.OrderedDict([('a', rule_a), ('b', rule_b), ('f', rule_f)])


def load_plugins(dirs):
    for d in dirs:
        for f in sorted(glob.glob(str(Path(d) / 'lint_rule_*.py'))):
            spec = importlib.util.spec_from_file_location(Path(f).stem, f)
            m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
            rid = getattr(m, 'RULE_ID', Path(f).stem[len('lint_rule_'):])
            if rid in RULES: raise SystemExit('rule id %r from %s already registered' % (rid, f))
            RULES[rid] = m.rule


def norm(rid, x):
    if isinstance(x, Finding): return x
    if isinstance(x, dict): return Finding(x.get('rule', rid), x['level'], x['owner'], x['event'], x['detail'])
    return Finding(*x)


def main(argv):
    want = [argv[i + 1] for i, a in enumerate(argv) if a == '--rule']
    levels = [int(argv[i + 1]) for i, a in enumerate(argv) if a == '--level'] or [0, 1]
    plug = [HERE] + [Path(argv[i + 1]) for i, a in enumerate(argv) if a == '--plugin-dir']
    load_plugins(plug)
    run = [r for r in RULES if not want or r in want]
    producers = None
    if 'b' in run and '--no-scan' not in argv:
        producers, census, computed, other = scan_producers()
        print('push_sites_scan.py census (listing, instructions, pointer loads, pushes):')
        for c in census: print('  ' + c)
        print('  computed-opcode pushes %s, unrecognised 304(A5) loads %s; events pushed: %s' % (computed, other, sorted(producers)))
        print('  events never pushed in 0..28: %s' % [e for e in range(29) if e not in producers])
    counts = collections.Counter(); allf = []
    for level, snap in SNAPS:
        if level not in levels: continue
        ctx = load_level(level, snap, producers)
        for rid in run:
            for x in RULES[rid](ctx) or []:
                f = norm(rid, x); allf.append((f, ctx)); counts[(rid, level)] += 1
        for n in ctx.notes: print('note ' + n)
    print('\nper-rule findings:')
    for rid in run: print('  %-6s %s  total %d' % (rid, '  '.join('L%d %4d' % (l, counts[(rid, l)]) for l in levels), sum(counts[(rid, l)] for l in levels)))
    print('\nfindings:')
    for f, ctx in allf:
        print('%s L%d %-9s ev %2d  %s' % (f.rule, f.level, f.owner, f.event, f.detail))


if __name__ == '__main__':
    main(sys.argv[1:])
