"""a3: push_sites_scan.py -- every writer of the ring-304 queue (write pointer 304(A5), count 1154(A5)) in the resident image and in every overlay listing, with the SOURCE of each opcode,
including register/memory (computed) sources.  Not the `addq.w #1,1154(A5)` idiom of queue_producers.py: this finds every instruction that mentions 304(A5), classifies it, and for every
pointer load `movea.l 304(A5),An` (or `move.l 304(A5),Dn/An`) lists the stores through An (`move.w src,(An)+`, `move.l ...`, `move.b ...`, and `d(An)` forms) up to the write-back `move.l An,304(A5)`.
Listings scanned: whole-image listings of gameplay_empire.snap and level1_loaded.snap ($001000-$04d300, made here with tools/disassemble.py --all, cached in this dir) and
scratchpad/cadaver/secrets_out/overlay/*.lst (the 9 overlay listings: level 0/1, one-disk pairs 0/5, Disk 2 pairs 0/7/14/21/28).
Outputs push_sites_scan.txt (every site) and prints the event table.  Usage (from M68000/): .venv/bin/python reversing/cadaver/py/secrets/overlay/events/push_sites_scan.py"""
import sys, os, re, glob, subprocess, collections
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../../..'))
OUTDIR = os.environ.get('OUTDIR') or os.path.join(ROOT, 'scratchpad/cadaver/s91_events'); os.makedirs(OUTDIR, exist_ok=True)   # scratch output (callcap json, caches, scan listings)
PY = sys.executable

def whole_image(snap, tag):
    cache = os.path.join(OUTDIR, 'whole_%s.asm' % tag)
    if not os.path.exists(cache):
        out = subprocess.run([PY, ROOT + '/tools/disassemble.py', '--snap', snap, '--all', '1000', '4d300'], capture_output=True, text=True, check=True, cwd=ROOT).stdout
        open(cache, 'w').write(out)
    return open(cache).read().splitlines()

def parse(lines):
    ins = []
    for l in lines:
        m = re.match(r'\s*\$([0-9a-f]+)(?: \(\+[0-9a-f]+\))?:\s*(.*)', l)
        if m: ins.append((int(m.group(1), 16), m.group(2).strip()))
    return ins

LISTINGS = [('resident+level0 (gameplay_empire.snap)', parse(whole_image(ROOT + '/scratchpad/cadaver/gameplay_empire.snap', 'l0'))),
            ('resident+level1 (level1_loaded.snap)', parse(whole_image(ROOT + '/scratchpad/cadaver/level1_loaded.snap', 'l1')))]
for f in sorted(glob.glob(ROOT + '/scratchpad/cadaver/secrets_out/overlay/*.lst')):
    LISTINGS.append((os.path.basename(f), parse(open(f).read().splitlines())))

LOAD = re.compile(r'(?:movea|move)\.l 304\(A5\),(A\d|D\d)$')
STORE_BACK = re.compile(r'move\.l (A\d|D\d),304\(A5\)$')
out = []; table = collections.defaultdict(set); computed = []; other304 = []

def reg_of(dst):
    m = re.match(r'\((A\d)\)\+?$', dst) or re.match(r'-?\d*\((A\d)[,)]', dst)
    return m.group(1) if m else None

def split_ops(text):
    # "move.w #$1,(A0)+" -> mnemonic, src, dst  (commas inside parentheses are kept together)
    m = re.match(r'(\S+)\s+(.*)$', text)
    if not m: return text, None, None
    mn, rest = m.group(1), m.group(2)
    depth = 0; cut = None
    for i, ch in enumerate(rest):
        if ch == '(': depth += 1
        elif ch == ')': depth -= 1
        elif ch == ',' and depth == 0: cut = i; break
    if cut is None: return mn, rest, None
    return mn, rest[:cut], rest[cut + 1:]

for name, ins in LISTINGS:
    n_load = n_push = 0
    for i, (addr, text) in enumerate(ins):
        if not re.search(r'(?<![\d-])304\(A5\)', text): continue
        mn, src, dst = split_ops(text)
        if LOAD.match(text) and not re.search(r'304\(A5\),336\(A5\)', text):
            n_load += 1
            reg = LOAD.match(text).group(1)
            # window: up to the write-back of the same register, max 40 instructions
            stores = []; wb = None
            regs = {reg}
            for j in range(i + 1, min(i + 41, len(ins))):
                a2, t2 = ins[j]
                m2 = STORE_BACK.match(t2)
                if m2 and m2.group(1) in regs: wb = a2; break
                mn2, s2, d2 = split_ops(t2)
                if t2.startswith('movea.l ') and s2 in regs and d2 and re.match(r'A\d$', d2): regs.add(d2)
                if d2 and reg_of(d2) in regs and mn2.startswith('move'):
                    stores.append((a2, mn2, s2, d2))
            # the count increment after the write-back
            inc = None
            if wb:
                for j in range(i, min(i + 60, len(ins))):
                    if ins[j][1].startswith('addq.w #1,1154(A5)'): inc = ins[j][0]; break
            first = stores[0] if stores else None
            opsrc = first[2] if first else None
            rec = dict(listing=name, load=addr, writeback=wb, count_inc=inc, stores=[(hex(a), mn2 + ' ' + s2 + ',' + d2) for a, mn2, s2, d2 in stores], opcode_src=opsrc)
            out.append(rec)
            if wb and inc and first and first[1].startswith('move.w'):
                n_push += 1
                if opsrc.startswith('#$'):
                    v = int(opsrc[2:], 16); table[v & 0xff].add((name, hex(inc), '%04x' % v))
                else:
                    computed.append(rec)
            else:
                other304.append(rec)
        elif STORE_BACK.match(text) or re.search(r'304\(A5\),336\(A5\)|336\(A5\),304\(A5\)|152\(A5\),304\(A5\)', text):
            continue   # write-back, save/restore of the cursor, ring reset
        else:
            other304.append(dict(listing=name, load=addr, writeback=None, count_inc=None, stores=[(hex(addr), text)], opcode_src='?'))
    print('%-45s instructions %6d  pointer loads %3d  pushes (load, move.w opcode, write-back, count++) %3d' % (name, len(ins), n_load, n_push))

print()
print('computed-opcode pushes (opcode not an immediate): %d' % len(computed))
for rec in computed: print('  ', rec)
print('pointer loads of 304(A5) that are not a recognised push (listing, load addr, stores): %d' % len(other304))
for rec in other304: print('  ', rec['listing'], hex(rec['load']), rec['stores'][:4])
print()
print('events pushed (immediate opcodes), by event, with sites:')
for ev in sorted(table):
    print('  event %2d: %s' % (ev, '; '.join('%s %s op=%s' % (a, b, c) for a, b, c in sorted(table[ev]))))

# writers of the count 1154(A5) and references to the ring storage by absolute address or through 152(A5)
cnt_writes = collections.Counter(); abs_refs = []; r152 = []
QLO, QHI = 0x39dbe, 0x39dbe + 200 * 8 + 16
for name, ins in LISTINGS:
    for addr, text in ins:
        if re.search(r'(?<![\d-])1154\(A5\)', text):
            mn, src, dst = split_ops(text)
            if dst and '1154(A5)' in dst or mn.startswith(('addq', 'subq', 'clr', 'neg', 'st')) and '1154(A5)' in (src or ''):
                cnt_writes[(name.split(' ')[0], re.sub(r'\s+', ' ', text))] += 1
        if re.search(r'(?<![\d-])152\(A5\)', text): r152.append((name.split(' ')[0], hex(addr), text))
        for m in re.finditer(r'\$([0-9a-f]{5,6})\b', text):
            v = int(m.group(1), 16)
            if QLO <= v < QHI: abs_refs.append((name.split(' ')[0], hex(addr), text))
print()
print('writes to the queue count 1154(A5) (listing family, instruction): occurrences')
for k, v in sorted(cnt_writes.items()): print('  ', k, v)
print('references to 152(A5):', sorted(set(r152)))
print('absolute references into the ring storage $%x-$%x: %d' % (QLO, QHI, len(abs_refs)), abs_refs[:10])

print('event 3 pushed anywhere:', 3 in table, '  event 21 pushed anywhere:', 21 in table)
open(os.path.join(OUTDIR, 'push_sites_scan.txt'), 'w').write('\n'.join(str(r) for r in out) + '\n')
