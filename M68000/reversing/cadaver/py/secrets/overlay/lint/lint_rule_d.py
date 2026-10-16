"""lint_rule_d.py [snap level] ...: rule (d), messages of the packed text table that nothing can show.

Universe.  The text table is level data: resource 4 of the level's directory record (one-disk image: L0 8096 bytes, L1 7639),
`[long][word count][count+1 offset words][6-bit stream]`; the loader puts the offset words at (A5)+168 ($075876) and the stream at
(A5)+172 ($076046).  The count is not kept in RAM, and the level-1 load leaves level 0's tail in place (L1 offset words 387-391 and
stream bytes from $1ad0 on are level 0's), so the bound comes from the disk image when it is present and otherwise from
COUNT = {0: 392, 1: 387} (read from that image).  An index is a message when its first NUL-terminated piece is non-empty; the empty
slots (L0 390, 391; L1 386) are listed separately.  Text is decoded from the snapshot (name_strings.decode_index) to the first NUL.

Shown sets (each source is *read* unless marked):
  script   verbs 28 MESSAGE (word), 72 DESCRIBE (word), 60 PAY-PROMPT (second word: $010df2 passes it in D2 to $00df46, which
           decodes it, appends the gold and message 62) in every block of ctx.blocks; blocks of events 3 and 21 (no producer) are
           tracked separately.
  peek     the rucksack description $009b04: walks a type-6 record's +$10 blocks, and for the first `$90` block byte-scans
           for 72 (`$9ba8`) or for a `$85` block of a class-template-byte-23 = 6 object scans for 28, and shows the word after the
           match when it is < 1000.  Emulated byte for byte on every type-6 record (the scan can match an operand byte).
  code     (a) raw byte scan of main code $006e00-$0172c8 and the level overlay for `move.w #N,2142(A5)` (3b7c NNNN 085e);
           (b) in the disassembly of the same ranges, a literal load of the operand register before a call of a text routine
           ($fd2c, $11770 D0; $a82c D0; $df46 D2) found by walking back to the first write of that register (8 instructions) or
           forward from a literal load across at most one `bra` (4 instructions); (c) direct ring pushes of op 8
           (`move.w #$8,(An)+` / `move.l D0,(An)+`) with a literal D0 ($007326: 48); (d) the counter 2242(A5) of $1175c:
           `move.b #N,2242(A5)` followed by k calls of $1175c before the next unconditional transfer shows N .. N+k-1.
  tables   rank (A5)+176 (20 x 6, word +0), spells (A5)+108 and potions (A5)+112 (100 x 8, word +0, nonzero entries), room-name
           suffix (A5)+116 (word table indexed by room byte 26 >= 0, `$00eb6c`), room word 24 >= 0 (`$00eb54`), type-2 class
           template word +10 >= 0 (object names: `$009478`, `$00a06e`, `$009bde`, `$011152`).

Cannot see: text chosen by a register path the scan does not follow (a non-literal operand: every such call site is listed in
the notes), callers that reach a text routine by a computed jump, overlay code outside the level's overlay bytes, the Disk 2
levels, which spell/potion/room-suffix/type-2 entries are reachable in play (a table entry counts as shown), and whether a
script block can actually fire (only events 3 and 21 are treated as dead; spent `$ff` blocks count as shown, they ran).

Standalone: .venv/bin/python reversing/cadaver/py/secrets/overlay/lint/lint_rule_d.py  (both snapshots) [--grep] [--all]"""
import sys, os, re, struct, subprocess, collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ['M68000_ROOT']) if os.environ.get('M68000_ROOT') else next(p for p in HERE.parents if (p / 'tools/rdis.py').exists())
for p in ('reversing/cadaver/py/secrets/overlay', 'reversing/cadaver/py/secrets', 'reversing/cadaver/py', 'tools'):
    if str(ROOT / p) not in sys.path: sys.path.insert(0, str(ROOT / p))

RULE_ID = 'd'
COUNT = {0: 392, 1: 387}                       # entries in the level's text resource (header word), one-disk image
OVERLAY = {0: (0x04c65e, 0x04d26a), 1: (0x04c65e, 0x04d1aa)}   # secrets.md: $c0c and $b4c bytes from 2534(A5)
MAIN = (0x006e00, 0x0172c8)
DISK = ROOT.parent / 'Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st'   # the level directory (stamp 12.9.1990 21:14)
T168, T172 = 0x075876, 0x076046
DEAD_EVENTS = (3, 21)
TEXT_CALLS = {'$fd2c': 'D0', '$11770': 'D0', '$a82c': 'D0', '$df46': 'D2'}
CACHE = ROOT / 'scratchpad/cadaver/lint/d_cache'


def u16(r, a): return struct.unpack_from('>H', r, a)[0]
def s16(r, a): return struct.unpack_from('>h', r, a)[0]
def u32(r, a): return struct.unpack_from('>I', r, a)[0]


def disk_count(level):
    """count word of resource 4 of directory record `level` in the one-disk image, or None"""
    try:
        from cad_lzh import decode_block
        d = DISK.read_bytes()
        if d[400 * 512:400 * 512 + 6] != b'881990': return None
        s, c = struct.unpack_from('>HH', d, 400 * 512 + 0x10 + 4 * (level * 5 + 4))
        data, _ = decode_block(d[s * 512:(s + c) * 512])
        return u16(data, 4), data
    except Exception:
        return None


def load_texts(ram, level, notes):
    """-> {index: first piece} for 0..count-1, and the set of empty slots (offset at or past the level's own stream end, or a
    zero-length first piece).  Text is decoded from RAM; the disk image only bounds it."""
    from name_strings import decode_index
    dc = disk_count(level)
    n = COUNT.get(level); slen = None
    if dc:
        n_disk, data = dc
        slen = len(data) - (6 + 2 * (n_disk + 1))
        same = sum(u16(data, 6 + 2 * i) == u16(ram, T168 + 2 * i) for i in range(n_disk))
        notes.append('d L%d: text resource from the disk image (%s): %d entries + end word, stream %d bytes; %d of %d offset words equal RAM'
                     % (level, DISK.name, n_disk, slen, same, n_disk))
        n = n_disk
    else:
        notes.append('d L%d: disk image not readable, text count %s from the constant table (stream end not known: stale tail not detected)' % (level, n))
    texts, empty = {}, set()
    for i in range(n):
        texts[i] = decode_index(ram, 0, T168, T172, i, maxlen=400).split(b'\0')[0].decode('latin1').replace('\r', ' / ')
        if texts[i] == '' or (slen is not None and u16(ram, T168 + 2 * i) >= slen): empty.add(i)
    return texts, empty


# ------------------------------------------------------------------ code scan

def listing(snap, lo, hi):
    CACHE.mkdir(exist_ok=True)
    f = CACHE / ('%s_%x_%x.lst' % (Path(snap).stem, lo, hi))
    if not f.exists() or f.stat().st_mtime < Path(snap).stat().st_mtime:
        out = subprocess.run([sys.executable, str(ROOT / 'tools/disassemble.py'), '--snap', str(snap), '--all', '%x' % lo, '%x' % hi],
                             capture_output=True, text=True, cwd=ROOT).stdout
        f.write_text(out)
    rows = []
    for l in f.read_text().splitlines():
        m = re.match(r'\s+\$([0-9a-f]+):\s+(.*)$', l)
        if m: rows.append((int(m.group(1), 16), m.group(2).strip()))
    return rows


def num(s): return int(s[1:], 16) if s.startswith('$') else int(s)


def code_refs(snap, ram, level, notes):
    refs = collections.defaultdict(list)          # index -> ['$addr how']
    nonlit = []                                   # call sites whose operand is not a literal
    olo, ohi = OVERLAY.get(level, (0x04c65e, 0x04e200))
    # (a) raw move.w #N,2142(A5)
    b = bytes(ram)
    n2142 = 0
    for lo, hi in (MAIN, (olo, ohi)):
        for m in re.finditer(rb'\x3b\x7c..\x08\x5e', b[lo:hi], re.S):
            n2142 += 1; refs[u16(ram, lo + m.start() + 2)].append('$%06x 2142' % (lo + m.start()))
    # (b)-(d) on the listing
    rows = listing(snap, *MAIN) + listing(snap, olo, ohi)
    calls = 0; push8 = 0; c2242 = 0
    for i, (a, t) in enumerate(rows):
        m = re.match(r'(?:bsr|jsr|bra|jmp) (\$[0-9a-f]+)(?:\.l)?$', t)
        if m and m.group(1) in TEXT_CALLS:
            calls += 1; reg = TEXT_CALLS[m.group(1)]; found = False
            for j in range(i - 1, max(i - 9, -1), -1):
                tj = rows[j][1]
                if re.search(r',%s$' % reg, tj):
                    mm = re.match(r'(?:moveq|move\.w|move\.l) #(\$?[0-9a-f]+),%s$' % reg, tj)
                    if mm: refs[num(mm.group(1))].append('$%06x %s' % (a, m.group(1))); found = True
                    else: nonlit.append('$%06x %s %s <- $%06x %s' % (a, m.group(1), reg, rows[j][0], tj)); found = True
                    break
                if re.match(r'(rts|bra|jmp|rte)\b', tj): break
            if not found: nonlit.append('$%06x %s %s <- (entry: set by the caller)' % (a, m.group(1), reg))
        # forward from a literal load across one bra
        mm = re.match(r'(?:moveq|move\.w|move\.l) #(\$?[0-9a-f]+),(D0|D2)$', t)
        if mm:
            k = i + 1; hops = 0; steps = 0
            while k < len(rows) and steps < 4:
                tk = rows[k][1]; steps += 1
                mc = re.match(r'(?:bsr|jsr) (\$[0-9a-f]+)(?:\.l)?$', tk)
                if mc and TEXT_CALLS.get(mc.group(1)) == mm.group(2):
                    s = '$%06x %s (fwd)' % (a, mc.group(1))
                    if not any(x.startswith('$%06x' % rows[k][0]) for x in refs[num(mm.group(1))]): refs[num(mm.group(1))].append(s)
                    break
                mb = re.match(r'bra (\$[0-9a-f]+)$', tk)
                if mb and hops == 0:
                    tgt = int(mb.group(1)[1:], 16); hops = 1
                    k = next((q for q, (aa, _) in enumerate(rows) if aa == tgt), len(rows)); continue
                if re.search(r',%s$' % mm.group(2), tk) or re.match(r'(rts|bra|jmp|bsr|jsr)\b', tk): break
                k += 1
        # (c) op-8 ring push
        if t == 'move.w #$8,(A0)+' and i + 1 < len(rows):
            push8 += 1
            nxt = rows[i + 1][1]
            if nxt == 'move.l D0,(A0)+':
                for j in range(i - 1, max(i - 6, -1), -1):
                    mm2 = re.match(r'(?:moveq|move\.w) #(\$?[0-9a-f]+),D0$', rows[j][1])
                    if mm2: refs[num(mm2.group(1))].append('$%06x op8 push' % a); break
                    if re.search(r',D0$', rows[j][1]): break
            elif nxt.startswith('move.l #'):
                notes.append('d L%d: op-8 push at $%06x queues a literal long %s as the message index (a pointer to %r: decoded as text index $%04x, garbage)'
                             % (level, a, nxt.split()[1].rstrip(',(A0)+'), bytes(ram[int(nxt.split('#$')[1].split(',')[0], 16):][:34]).split(b'\0')[0].decode('latin1'),
                                int(nxt.split('#$')[1].split(',')[0], 16) & 0xffff))
        # (d) 2242 counter
        mm = re.match(r'move\.b #(\$?[0-9a-f]+),2242\(A5\)$', t)
        if mm:
            c2242 += 1; base = num(mm.group(1)); k = 0
            for j in range(i + 1, min(i + 40, len(rows))):
                tj = rows[j][1]
                if re.match(r'bsr \$1175c$', tj):
                    refs[base + k].append('$%06x 2242+%d' % (a, k)); k += 1
                if re.match(r'(rts|bra|jmp)\b', tj): break
    notes.append('d L%d: code scan main $%06x-$%06x + overlay $%06x-$%06x: %d instructions, %d `move.w #N,2142(A5)` (raw bytes), %d text-routine call sites, '
                 '%d op-8 pushes, %d 2242(A5) counter sets; %d call sites with a non-literal operand'
                 % (level, MAIN[0], MAIN[1], olo, ohi, len(rows), n2142, calls, push8, c2242, len(nonlit)))
    for s in nonlit: notes.append('d L%d:   non-literal text site %s' % (level, s))
    notes.append('d L%d: non-literal sites resolved by reading (main image, same in both levels): $9494/$9bee/$a074/$11156 type-2 +10; '
                 '$9bcc the peek; $a3a0 rank; $eb5a/$eb7c room word 24 and suffix table; $111fe/$1122a spell/potion tables; $11768 the 2242 '
                 'counter; $11004/$11238/$10e02 verbs 72/28/60; $df5c D2 = 60 ($b64a) or verb 60; $a830 = $a82c (59, 61); $a83c the op-8 '
                 'consumer (2142 and pushes); $a664 decodes D0 = 2 * icon 9 = 18 into the buffer and returns without drawing; $e020 '
                 '(index in A0) has no direct caller in the listing: cannot see' % level)
    return refs


# ------------------------------------------------------------------ tables and records

def table_refs(ram, base, a5, notes, level):
    from room_object_census import resource_type, resolve
    refs = collections.defaultdict(list)
    for off, n, st, name in ((176, 20, 6, 'rank'), (108, 100, 8, 'spell'), (112, 100, 8, 'potion')):
        t = u32(ram, a5 + off); z = 0
        for i in range(n):
            w = u16(ram, t + st * i)
            if w == 0 and name != 'rank': z += 1; continue
            refs[w].append('%s %d' % (name, i))
        notes.append('d L%d: table %s (A5)+%d = $%06x, %d records, %d zero (name 0 if ever indexed)' % (level, name, off, t, n, z))
    i3, d3, n3 = resource_type(ram, base, a5, 3)
    t116 = u32(ram, a5 + 116); nr = 0
    for k in range(n3):
        a = resolve(ram, base, i3, d3, k)
        if a is None: continue
        nr += 1
        w = s16(ram, a + 24)
        if w >= 0: refs[w].append('room %d word 24' % k)
        sb = struct.unpack_from('>b', ram, a + 26)[0]
        if sb >= 0: refs[u16(ram, t116 + 2 * sb)].append('room %d byte 26 -> suffix %d' % (k, sb))
    i2, d2, n2 = resource_type(ram, base, a5, 2); nt = 0
    for k in range(n2):
        a = resolve(ram, base, i2, d2, k)
        if a is None: continue
        nt += 1; w = s16(ram, a + 10)
        if w >= 0: refs[w].append('class template %d +10' % k)
    notes.append('d L%d: %d room records (word 24, byte 26 via (A5)+116 = $%06x), %d type-2 class templates (+10) read' % (level, nr, t116, nt))
    return refs


def peek_refs(ram, base, a5, notes, level):
    """$009b04 emulated on every type-6 record"""
    from room_object_census import resource_type, resolve
    refs = collections.defaultdict(list)
    i6, d6, n6 = resource_type(ram, base, a5, 6); i2, d2, n2 = resource_type(ram, base, a5, 2)
    nrec = 0
    for oid in range(n6):
        a = resolve(ram, base, i6, d6, oid)
        if a is None: continue
        nrec += 1
        tpl = resolve(ram, base, i2, d2, u16(ram, a + 6))
        cnt = ram[a + 11]; p = a + 0x10
        for _ in range(cnt):
            e = ram[p + 1]
            if e == 0x90 or (e == 0x85 and tpl is not None and ram[tpl + 23] == 6):
                want = 72 if e == 0x90 else 28
                q = p + 2; d1 = (ram[p] - 1) & 0xff
                while True:
                    if ram[q] == want:
                        w = u16(ram, q + 1)
                        if w < 1000: refs[w].append('peek obj %d ev $%02x' % (oid, e)); break
                    q += 1
                    if d1 == 0: break
                    d1 -= 1
                break
            if ram[p] == 0: break
            p += ram[p]
    notes.append('d L%d: rucksack peek $009b04 emulated on %d type-6 records' % (level, nrec))
    return refs


# ------------------------------------------------------------------ the rule

def arg_word(s): return int(s, 16)


def rule(ctx):
    from gfxview import load_ram, snapshot_regs
    notes = ctx.notes if hasattr(ctx, 'notes') else []
    ram, base = load_ram(ctx.snap); a5 = snapshot_regs(ctx.snap)[0]['a5']
    lv = ctx.level
    texts, empty = load_texts(ram, lv, notes)
    live = collections.defaultdict(list); dead = collections.defaultdict(list)
    nb = collections.Counter(); nverb = collections.Counter()
    for b in ctx.blocks:
        owner, event, ops = b[0], b[1], b[2]
        nb['dead' if event in DEAD_EVENTS else 'live'] += 1
        for d, v, args, name in ops:
            idx = None
            if v in (28, 72): idx = arg_word(args[0])
            elif v == 60: idx = arg_word(args[1])
            if idx is None: continue
            nverb[v] += 1
            (dead if event in DEAD_EVENTS else live)[idx].append((owner, event, v))
    notes.append('d L%d: %d blocks walked (%d live, %d of events 3/21); text operands: verb 28 %d, verb 72 %d, verb 60 %d'
                 % (lv, len(ctx.blocks), nb['live'], nb['dead'], nverb[28], nverb[72], nverb[60]))
    code = code_refs(ctx.snap, ram, lv, notes)
    tabs = table_refs(ram, base, a5, notes, lv)
    peek = peek_refs(ram, base, a5, notes, lv)
    notes.append('d L%d: text indices 0-%d, %d empty (%s)' % (lv, len(texts) - 1, len(empty), ', '.join('%d %r' % (i, texts[i]) for i in sorted(empty))))
    out_of_range = sorted({i for src in (live, dead, code, tabs, peek) for i in src if i not in texts})
    if out_of_range:
        notes.append('d L%d: indices named but beyond the level table: %s' % (lv, [(i, (live.get(i) or dead.get(i) or code.get(i) or tabs.get(i) or peek.get(i))[:2]) for i in out_of_range]))
    ctx.d_sources = {'live': live, 'dead': dead, 'code': code, 'tables': tabs, 'peek': peek, 'texts': texts}
    for i, s in sorted(texts.items()):
        if i in empty: continue
        if i in live or i in code or i in tabs or i in peek: continue
        kind = 'UI' if i < 128 else 'script'
        if i in dead:
            for owner, event, v in dead[i]:
                yield {'rule': 'd', 'level': lv, 'owner': owner, 'event': event,
                       'detail': 'message %d (%s) shown only by a dead block (event %d has no producer), verb %d: "%s"' % (i, kind, event, v, s)}
        else:
            yield {'rule': 'd', 'level': lv, 'owner': 'msg %d' % i, 'event': -1, 'detail': 'message %d (%s) shown by nothing: "%s"' % (i, kind, s)}


# ------------------------------------------------------------------ standalone

def load_ctx(snap, level):
    import verb_decode as vd
    from room_blocks import room_blocks
    class C: pass
    c = C(); c.snap, c.level, c.notes, c.blocks = snap, level, [], []
    for oid, start, e, body in vd.collect(snap):
        c.blocks.append(('obj %d' % oid, e & 0x7f, vd.decode_block(e, body)))
    rows, problems, nrooms = room_blocks(snap)
    for slot, e, body, off in rows:
        try: ops = vd.decode_block(e, body)
        except vd.Bad: ops = vd.decode_block(e, body[:-1])
        c.blocks.append(('room %d' % slot, e & 0x7f, ops))
    return c


def image_grep(snap, idxs):
    """word hits of each index in the loaded image, located in the resource data areas where possible"""
    from gfxview import load_ram, snapshot_regs
    from room_object_census import resource_type, resolve
    ram, base = load_ram(snap); a5 = snapshot_regs(snap)[0]['a5']
    spans = []
    for t in range(10):
        ip, dp, n = resource_type(ram, base, a5, t)
        for k in range(n):
            e = u32(ram, ip + 4 * k)
            if e >> 17: spans.append((dp + (e & 0x1ffff), dp + (e & 0x1ffff) + (e >> 17), t, k))
    def where(a):
        for lo, hi, t, k in spans:
            if lo <= a < hi: return 'type%d #%d +%d' % (t, k, a - lo)
        if MAIN[0] <= a < MAIN[1]: return 'main $%06x' % a
        if T168 <= a < T172 + 0x2000: return 'text table $%06x' % a
        return '$%06x' % a
    b = bytes(ram[:0x80000]); res = {}
    for i in idxs:
        pat = struct.pack('>H', i)
        hits = [m.start() for m in re.finditer(re.escape(pat), b)]
        typed = [w for w in (where(h) for h in hits) if w.startswith('type') and not w.startswith('type0')]
        tabs = []
        for off, n, st, name in ((176, 20, 6, 'rank'), (108, 100, 8, 'spell'), (112, 100, 8, 'potion'), (116, 20, 2, 'suffix')):
            t = u32(ram, a5 + off)
            tabs += ['%s +%d' % (name, h - t) for h in hits if t <= h < t + n * st]
        res[i] = (len(hits), typed + tabs)
    return res


if __name__ == '__main__':
    pairs = [a for a in sys.argv[1:] if not a.startswith('--')]
    runs = [(pairs[i], int(pairs[i + 1])) for i in range(0, len(pairs), 2)] if pairs else [
        (str(ROOT / 'scratchpad/cadaver/gameplay_empire.snap'), 0), (str(ROOT / 'scratchpad/cadaver/level1_loaded.snap'), 1)]
    os.chdir(ROOT)
    for snap, level in runs:
        ctx = load_ctx(snap, level)
        fs = list(rule(ctx))
        for n in ctx.notes: print('note ' + n)
        src = ctx.d_sources
        nui = sum(1 for f in fs if f['owner'].startswith('msg') and int(f['owner'][4:]) < 128)
        print('L%d findings: %d (unshown UI %d, unshown script %d, dead-block-only %d)'
              % (level, len(fs), nui, sum(1 for f in fs if f['owner'].startswith('msg')) - nui, sum(1 for f in fs if not f['owner'].startswith('msg'))))
        for f in fs: print('d L%d %-9s ev %2d  %s' % (f['level'], f['owner'], f['event'], f['detail']))
        if '--grep' in sys.argv:
            idx = sorted({int(f['detail'].split()[1]) for f in fs})
            for i, (n, w) in image_grep(snap, idx).items():
                print('  grep L%d %3d ($%04x): %d word hits in $0-$7ffff; in type 1-9 records or the name tables: %d %s' % (level, i, i, n, len(w), '; '.join(w[:12]) + (' ...' if len(w) > 12 else '')))
        if '--all' in sys.argv:
            for i, s in sorted(src['texts'].items()):
                why = (['script %s' % ('/'.join('%s ev%d v%d' % x for x in src['live'][i][:3]))] if i in src['live'] else []) + \
                      (['code ' + ' '.join(src['code'][i][:3])] if i in src['code'] else []) + \
                      (['tab ' + ' '.join(src['tables'][i][:3])] if i in src['tables'] else []) + \
                      (['peek ' + ' '.join(src['peek'][i][:2])] if i in src['peek'] else []) + \
                      (['DEAD ' + str(src['dead'][i][:2])] if i in src['dead'] else [])
                print('  all L%d %3d %-40.40s %s' % (level, i, s, ' | '.join(why) or '-'))
