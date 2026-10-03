"""verb_decode.py [snap] [--dump] [--verbs]: the operand grammar of the 94 object-script verbs (table $00ffba), a script
disassembler, and a self-check over every script block of every type-6 object.

Operand lengths were read from each verb body in the listing (`(A1)+` reads, the helper `$010738` = 2-byte object id
then `$010740` = resolve, `$010914` = 2-byte object id + `A2` = A1 for the following reads, direct `addq.w #n,A1`).
The self-check is the proof: a script block is `[len][event | $80][verb bytes ...][$17]` (len counts itself), and a
correct grammar must consume exactly len-3 bytes and end on the `$17` (verb 23) for every block; the nested IF verbs
must also agree with their own length byte.

Operand kinds: `o` object id (word, big-endian; `$8xxx`/negative = the current actor for the `$010914` family, see the
handlers), `w` word, `b` byte.  `V` = variable-length record (verbs 62, 63, 64).  IF verbs (14, 48, 58, 59) are
`[verb][n?][len][then verbs .. $16]([$0f][len][else verbs .. $16])?` where `len` counts itself.

Prints: blocks parsed / blocks that fit, and (with --verbs) the grammar table, (with --dump) every script, (with --md) the
markdown verb table of secrets.md.  A second snapshot with another level loaded (`level1_loaded.snap`, from `level2_load.py`)
decodes that level's objects the same way."""
import sys, collections
sys.path.insert(0, 'reversing/cadaver/py'); sys.path.insert(0, 'tools')

# verb: (operands, name).  Operand string is the exact byte layout; names read from the handler body.
VERBS = {
    0:  ('o',      'DELETE object (pending-delete list 1386(A5))'),
    1:  ('o',      'SHOW object: clear hidden bit, place, draw'),
    2:  ('',       'DELETE the current object'),
    3:  ('o',      'GOANI: start the object animation'),
    4:  ('o',      'STOPANI'),
    5:  ('b',      'XP += 26 (operand read and ignored)'),
    6:  ('b',      'GOLD += n, XP += n/4'),
    7:  ('w',      'REGISTER creature id (list 396(A5), max 6)'),
    8:  ('w',      'UNREGISTER creature id (asserts if absent)'),
    9:  ('b',      'queue event $4013 for record 164(A5) with n'),
    10: ('b',      'CLEAR FLAG n (type-4 record +2), sound $2a'),
    11: ('o',      'GOMOVE'),
    12: ('o',      'STOPMOVE'),
    13: ('b',      'GOLD -= n'),
    14: ('IF',     'IF (2270 != 0)'),
    15: ('',       'ELSE marker (executing it asserts)'),
    16: ('o',      'COND obj state bit 0 set'),
    17: ('o',      'obj state bit 0 = 1'),
    18: ('o',      'obj state bit 0 = 0'),
    19: ('o',      'COND obj state bit 1 set'),
    20: ('o',      'obj state bit 1 = 1'),
    21: ('o',      'obj state bit 1 = 0'),
    22: ('',       'END of IF/ELSE part ($16)'),
    23: ('',       'END of script ($17)'),
    24: ('o',      'obj state bit 0 ^= 1'),
    25: ('o',      'obj state bit 1 ^= 1'),
    26: ('o',      'HIDE object'),
    27: ('bw',     'SET FLAG n = word (type-4 record +2), sound'),
    28: ('w',      'MESSAGE n (fade, text, wait)'),
    29: ('',       'mark this block spent (event byte = $ff)'),
    30: ('',       'COND current obj state bit 0 set'),
    31: ('',       'current obj state bit 0 = 0'),
    32: ('',       'current obj state bit 0 = 1'),
    33: ('',       'current obj state bit 0 ^= 1'),
    34: ('w',      'COND object id in the type-8 list'),
    35: ('o',      'PUT IN RUCK (rucksack; asserts if full)'),
    36: ('oXXXX',  'CREATE object o at fixed (x, y, z, facing)'),
    37: ('bbbb',   'TELEPORT room, x, y, z'),
    38: ('bb',     'VAR n = v (bytes at 2282(A5))'),
    39: ('bb',     'VAR n += v'),
    40: ('bbb',    'COND VAR n op v (bytes n, op, v; op 0 >, 1 <, 2 ==, 3+ !=)'),
    41: ('obbbb',  'PLACE object in room r at (x, y, z) ($fe = this room)'),
    42: ('bb',     'set 2462(A5) = a, 2461(A5) = b'),
    43: ('ob',     'COND object in room n ($fe = this room)'),
    44: ('oobb',   'CREATE object o2 next to o1 (offset slot, facing)'),
    45: ('w',      'HEALTH += signed word (0 or less: death)'),
    46: ('',       'no-op'),
    47: ('o',      'COND object exists'),
    48: ('IF',     'IF (2270 == 0): then-part when the counter is zero'),
    49: ('bb',     'ARM TIMER n = v ticks'),
    50: ('o',      'KILL creature (queue event 23)'),
    51: ('b',      'START LEVEL n+1 (n <= 9)'),
    52: ('w',      'no-op (reads a word)'),
    53: ('o',      'REVEAL NAME (clear hidden-name bits)'),
    54: ('o',      'LOCK'),
    55: ('o',      'UNLOCK'),
    56: ('ob' + 'bbbbbb', 'COND object in box (room; x0 x1 y0 y1 z0 z1)'),
    57: ('w',      'COND selected object 1262(A5) == id'),
    58: ('IFn',    'IF (2270 == n)'),
    59: ('IFn',    'IF (2270 != n)'),
    60: ('ww',     'COND $df46(a, b)'),
    61: ('b',      'COND FLAG n set'),
    62: ('V',      'SET (A5)+off = value (word, or byte if off bit 15)'),
    63: ('V',      'ADD (A5)+off += value'),
    64: ('Vb',     'COND (A5)+off op value (ops as verb 40)'),
    65: ('ob',     'obj field +1 += signed n (clamped 0..255)'),
    66: ('ob',     'queue [type][sub][obj] record into 1266(A5)'),
    67: ('o',      'GOACTI (object state bit 6 of +15 = 0)'),
    68: ('o',      'STOPACTI (bit 6 = 1)'),
    69: ('obbb',   'MOVE: set the +3,+4,+5 bytes of the object record'),
    70: ('b',      'PLAY SOUND n'),
    71: ('',       'no-op'),
    72: ('w',      'DESCRIBE: examine text n with the object details'),
    73: ('oo',     'MOVE o2 to the position and room of o1 (o1 stays)'),
    74: ('o',      'WAKE creature'),
    75: ('o',      'SLEEP creature'),
    76: ('b',      'COND shield bit n of 2436(A5)'),
    77: ('o',      'UNLOCK CHEST'),
    78: ('o',      'UNTRAP CHEST'),
    79: ('bb',     'RANDOM lo..hi -> 2520(A5)'),
    80: ('b',      'COND 2520(A5) == n'),
    81: ('b',      '2520(A5) = VAR n'),
    82: ('b',      'delete type-8 list entries whose word +2 == n'),
    83: ('b',      'no-op (reads a byte)'),
    84: ('oo' + 'bbbb', 'CREATE object o2 relative to o1 (dx, dy, z, facing)'),
    85: ('w',      'word > 0: XP += 26; word < 0: XP = 0'),
    86: ('w',      'GOLD += word, XP += word/4'),
    87: ('b',      'sound op $015ae0(n)'),
    88: ('b',      'COND n == 2489(A5)'),
    89: ('o',      'UNINV (clear bit 0 of +6)'),
    90: ('bbb',    'POISON strength, duration, interval'),
    91: ('b',      'COND current obj word +6 == n'),
    92: ('o',      'CLEAR CHEST'),
    93: ('o',      'DIRTY POTION'),
}
SIZE = {'o': 2, 'w': 2, 'b': 1, 'X': 1}


class Bad(Exception):
    pass


def parse(bs, p, end, term, out, depth=0):
    """Parse verbs from bs[p:end] until byte `term` ($16 or $17).  Returns the position after the terminator."""
    while True:
        if p >= end:
            raise Bad('ran off the block')
        v = bs[p]; p += 1
        if v not in VERBS:
            raise Bad('verb %d not in the table' % v)
        ops, name = VERBS[v]
        if v == term:
            out.append((depth, v, [], name)); return p
        if v in (22, 23):
            raise Bad('unexpected terminator %d' % v)
        if ops in ('IF', 'IFn'):
            arg = []
            if ops == 'IFn':
                arg = [bs[p]]; p += 1
            ln = bs[p]; lstart = p; p += 1
            out.append((depth, v, ['%x' % a for a in arg] + ['len %d' % ln], name))
            p = parse(bs, p, end, 0x16, out, depth + 1)
            if p != lstart + ln:
                raise Bad('IF len %d disagrees (then part ends +%d)' % (ln, p - lstart))
            if p < end and bs[p] == 0x0f:
                p += 1; ln = bs[p]; lstart = p; p += 1
                out.append((depth, 15, ['len %d' % ln], 'ELSE'))
                p = parse(bs, p, end, 0x16, out, depth + 1)
                if p != lstart + ln:
                    raise Bad('ELSE len %d disagrees' % ln)
            continue
        args = []
        kinds = ops
        if ops in ('V', 'Vb'):
            if p + 1 >= end: raise Bad('short V')
            idx = (bs[p] << 8) | bs[p + 1]; p += 2
            n = 1 if idx & 0x8000 else 2
            args.append('%s A5+%d' % ('byte' if idx & 0x8000 else 'word', idx & 0x7fff))
            args.append('%x' % int.from_bytes(bs[p:p + n], 'big')); p += n
            if ops == 'Vb': args.append('op %d' % bs[p]); p += 1
        else:
            for k in ops:
                n = SIZE[k]
                if p + n > end: raise Bad('operand past block')
                x = int.from_bytes(bs[p:p + n], 'big'); p += n
                args.append(('#%d' % x if x < 0x8000 else 'actor' if x == 0xffff else '#%x' % x) if k == 'o' else '%x' % x)
        out.append((depth, v, args, name))


# Event gates: the precondition routines of table $00fe84 (indexed by the event opcode) read their operand bytes from
# the script stream (A1) before the verbs run.  Bytes consumed per event, read from each gate body ($00fece 1, $00ff26 2,
# $00ff38 2, $00ff10 2, $00fefc 2, $00feea 1, $00ff98 1, $00febe 1; the others read none).
GATE = {1: 1, 4: 2, 9: 2, 10: 2, 12: 1, 13: 1, 15: 1, 17: 1, 18: 2, 19: 1, 20: 1, 24: 1, 26: 2}


def decode_block(event, body):
    """body = the bytes after [len][event]: gate operand bytes, verbs, the verb-23 terminator, and possibly padding $17s."""
    out = []
    g = GATE.get(event & 0x7f, 0)
    if (event & 0x7f) > 28:
        raise Bad('event %d beyond the gate table' % (event & 0x7f))
    out.append((0, -1, ['%02x' % b for b in body[:g]], 'GATE for event %d' % (event & 0x7f)))
    p = parse(body, g, len(body), 0x17, out)
    if any(b != 0x17 for b in body[p:]):
        raise Bad('bytes after $17')
    if p != len(body):
        out.append((0, -2, ['%d' % (len(body) - p)], 'padding $17 after the terminator (ignored by the consumer)'))
    return out


TEXT = {}


def load_text(snap):
    from gfxview import load_ram, snapshot_regs
    import struct
    from name_strings import decode_index
    ram, base = load_ram(snap); a5 = snapshot_regs(snap)[0]['a5']
    u32 = lambda a: struct.unpack_from('>I', ram, a)[0]
    for i in range(390):
        TEXT[i] = decode_index(ram, 0, u32(a5 + 168), u32(a5 + 172), i).split(b'\0')[0].decode('latin1').replace('\r', ' / ')


def fmt(out):
    lines = []
    for d, v, args, name in out:
        txt = ''
        if TEXT and v in (28, 72): txt = '   "%s"' % TEXT.get(int(args[0], 16), '?')
        lines.append('  ' + '  ' * d + '%2s %-38s %s%s' % (v if v >= 0 else '-', name, ' '.join(args), txt))
    return '\n'.join(lines)


def collect(snap):
    from gfxview import load_ram, snapshot_regs
    from room_object_census import resource_type, resolve
    ram, base = load_ram(snap); regs, _ = snapshot_regs(snap); a5 = regs['a5']
    t6i, t6d, n6 = resource_type(ram, base, a5, 6)
    res = []
    for oid in range(1000):
        a = resolve(ram, base, t6i, t6d, oid)
        if a is None: continue
        for cntoff, start in ((11, 0x10), (31, 0x20)):
            cnt = ram[a + cntoff]
            if not 0 < cnt < 12: continue
            p = a + start; ok = True; bl = []
            for _ in range(cnt):
                ln = ram[p]
                if ln < 3 or ln > 120: ok = False; break
                # a block whose content through the $17 has odd length is followed by one pad byte: `$17` for 11 level-0 blocks, uninitialised for the
                # rest (LEVER 472's is `$32`); requiring `$17` at len-1 dropped 49 level-0 objects (door `$22`'s opener among them)
                if ram[p + ln - 1] == 0x17: end = p + ln
                elif ln >= 4 and ram[p + ln - 2] == 0x17: end = p + ln - 1
                else: ok = False; break
                bl.append((ram[p + 1], bytes(ram[p + 2:end]))); p += ln
            if ok:
                for e, body in bl: res.append((oid, start, e, body))
    return res


def md_table(snaps):
    """markdown rows for secrets.md: verb, handler, operand layout, effect, and the script-use count in each snapshot"""
    from gfxview import load_ram
    ram, base = load_ram(snaps[0])
    tab = [0xffba + ((ram[0xffba + 2 * i] << 8) | ram[0xffba + 2 * i + 1]) for i in range(94)]
    use = []
    for sp in snaps:
        c = collections.Counter()
        for oid, start, e, body in collect(sp):
            for d, v, a, n in decode_block(e, body):
                if v >= 0: c[v] += 1
        use.append(c)
    lay = {'IF': 'len', 'IFn': 'n len', 'V': 'off, value (word; byte if off bit 15)', 'Vb': 'off, value, op'}
    rows = ['| verb | handler | operand bytes | effect | uses (L0 / L1) |', '|---|---|---|---|---|']
    for v in range(94):
        ops, name = VERBS[v]
        n = lay.get(ops) or ('-' if not ops else ' '.join({'o': 'obj:2', 'w': 'word:2', 'b': 'b', 'X': 'b'}[k] for k in ops))
        rows.append('| %d | `$%06x` | %s | %s | %s |' % (v, tab[v], n, name, ' / '.join(str(u[v]) for u in use)))
    return '\n'.join(rows)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    snap = args[0] if args else 'scratchpad/cadaver/gameplay_empire.snap'
    if '--md' in sys.argv:
        print(md_table([snap, 'scratchpad/cadaver/level1_loaded.snap'])); sys.exit(0)
    if '--verbs' in sys.argv:
        for v in range(94): print('%2d  %-8s %s' % (v, VERBS[v][0], VERBS[v][1]))
    if '--dump' in sys.argv: load_text(snap)
    blocks = collect(snap)
    good = 0; bad = []; used = collections.Counter(); objs = set()
    for oid, start, e, body in blocks:
        try:
            out = decode_block(e, body)
        except Bad as ex:
            bad.append((oid, e, body.hex(), str(ex))); continue
        good += 1; objs.add(oid)
        for d, v, a, n in out:
            if v >= 0: used[v] += 1
        if '--dump' in sys.argv:
            print('object %d  +$%02x  event $%02x' % (oid, start, e & 0x7f)); print(fmt(out))
    print('blocks: %d  decode exactly to their length and end on $17: %d  objects: %d' % (len(blocks), good, len(objs)))
    for b in bad: print('  BAD', b)
    print('verbs used in scripts (%d distinct):' % len(used), dict(sorted(used.items())))
