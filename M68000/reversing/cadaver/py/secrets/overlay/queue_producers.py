"""queue_producers.py [snap]: every site in the loaded image that pushes an event onto the ring-304 queue, with its opcode.

The push idiom (all 48 sites of `gameplay_empire.snap` fit it) is
    movea.l 304(A5),A0 / move.w #<op>,(A0)+ / move.l <obj>,(A0)+ / ... / addq.w #1,1154(A5)
so the script finds each `addq.w #1,1154(A5)` in a whole-image listing (`tools/disassemble.py --all`) and takes the first
`move.w ...,(An)+` after the preceding `movea.l 304(A5),An`.  The consumer `$00fdbc` compares the LOW BYTE of the opcode with
a script block's event byte; bit 14 selects the second script set (template +$20) and bit 15 adds a fourth longword to the
entry (mechanics.md 18a, secrets.md "Object scripts"), so `$4013` is event 19 for the +$20 set.

Static only: it names the producer, not what makes it run.  Prints one line per site (address, opcode, event, flags) and a
table event -> sites.  A site whose opcode is not an immediate is printed as `reg`.  Output also goes to
scratchpad/cadaver/secrets_out/overlay/queue_producers.txt.  Run from M68000/:
    uv run python reversing/cadaver/py/secrets/overlay/queue_producers.py [scratchpad/cadaver/gameplay_empire.snap]
Expected on gameplay_empire.snap: 48 sites, 25 distinct events (the script blocks of both levels use events 3 and 21, which have no
immediate-opcode producer)."""
import sys, re, subprocess, collections, os

snap = next((a for a in sys.argv[1:] if not a.startswith('-')), 'scratchpad/cadaver/gameplay_empire.snap')
lo, hi = '6000', '4d300'   # main code to the end of the level overlay (secrets.md: the image ends at $4d26a)

listing = subprocess.run([sys.executable, 'tools/disassemble.py', '--snap', snap, '--all', lo, hi],
                         capture_output=True, text=True, check=True).stdout
ins = []
for line in listing.splitlines():
    m = re.match(r'\s*\$([0-9a-f]+):\s*(.*)', line)
    if m:
        ins.append((int(m.group(1), 16), m.group(2)))

sites = []
for i, (addr, text) in enumerate(ins):
    if not text.startswith('addq.w #1,1154(A5)'):
        continue
    op = None
    for j in range(i - 1, max(i - 14, 0), -1):
        if re.match(r'movea\.l 304\(A5\),A\d', ins[j][1]):
            for k in range(j + 1, i):
                m = re.match(r'move\.w (#\$[0-9a-f]+|\S+),\(A\d\)\+', ins[k][1])
                if m:
                    op = m.group(1)
                    break
            break
    sites.append((addr, op))

by_event = collections.defaultdict(list)
out = []
for addr, op in sites:
    if op and op.startswith('#$'):
        v = int(op[2:], 16)
        ev, b14, b15 = v & 0xff, bool(v & 0x4000), bool(v & 0x8000)
        out.append('$%06x  op $%04x  event %2d%s%s' % (addr, v, ev, '  +$20 set' if b14 else '', '  4th long' if b15 else ''))
        by_event[ev].append(addr)
    else:
        out.append('$%06x  op reg (%s)' % (addr, op))
out.append('')
out.append('%d sites, %d distinct events' % (len(sites), len(by_event)))
for ev in sorted(by_event):
    out.append('event %2d: %s' % (ev, ' '.join('$%06x' % a for a in by_event[ev])))

dest = 'scratchpad/cadaver/secrets_out/overlay'
os.makedirs(dest, exist_ok=True)
open(os.path.join(dest, 'queue_producers.txt'), 'w').write('\n'.join(out) + '\n')
print('\n'.join(out))
