"""Reads census_scan.py's log: per scan, which behaviour the chosen record has, and whether homing records were present.
Behaviour = the long at +16 of a record.  Homing = $21d08 (Patrol_HomeOnQueue; its body switches the record to $21c64 after a
countdown, so $21c64 is reported separately).  Usage: uv run python <this> <census.log>"""
import re, struct, sys
from collections import Counter
txt = open(sys.argv[1]).read()
chunks = re.split(r'(?m)^(?=--- (?:breakpoint|gave up))', txt)[1:]
HEX = re.compile(r'^[0-9a-f]{2}( [0-9a-f]{2})*$')
n = 0; gave = 0
pres = Counter(); chosen = Counter(); poolh = Counter(); ticks = []; queue_hit = 0; homing_present = 0; homing_chosen = 0
hp_ticks = []; ever_after = Counter(); nrec = []; q_nonzero = 0; ch_idx_out = 0
for ch in chunks:
    if ch.startswith('--- gave up'): gave += 1; continue
    head, _, _ = ch.partition('--- breakpoint')
    regs = dict((k, int(v, 16)) for k, v in re.findall(r'\b([DA][0-7]):([0-9a-f]{8})', ch))
    rows = [bytes.fromhex(l.replace(' ', '')) for l in ch.split('\n') if HEX.match(l.strip())]
    if len(rows) < 5: continue
    tk, cnt, ship, q, pool = rows[:5]
    tk = struct.unpack('>H', tk)[0]; cnt = struct.unpack('>H', cnt)[0]; a0 = regs['A0']
    i = (a0 - 0x31d54) // 20
    if not (0 <= i < 128 and (a0 - 0x31d54) % 20 == 0): ch_idx_out += 1; continue
    recs = [pool[k * 20:k * 20 + 20] for k in range(cnt)]
    beh = [struct.unpack('>I', r[16:20])[0] for r in recs]
    cb = struct.unpack('>I', pool[i * 20 + 16:i * 20 + 20])[0]
    n += 1; ticks.append(tk); nrec.append(cnt)
    for b in beh: poolh[b] += 1
    chosen[cb] += 1
    hom = [k for k, b in enumerate(beh) if b == 0x21d08]
    if hom: homing_present += 1; hp_ticks.append(tk)
    if cb == 0x21d08: homing_chosen += 1
    if any(q[k:k + 6] != b'\0' * 6 for k in (0, 6, 12, 18)): q_nonzero += 1
    # does the chosen record sit at a queue position (is it the queue itself)?  the scan never reads $27134; compare anyway
    qs = [struct.unpack('>3h', q[k:k + 6]) for k in (0, 6, 12, 18)]
    pos = struct.unpack('>3h', pool[i * 20:i * 20 + 6])
    if pos in qs and pos != (0, 0, 0): queue_hit += 1
print('scans (bp $253a4 stops) read: %d   (bp gave up: %d, A0 outside pool: %d)   tick range %d..%d' % (n, gave, ch_idx_out, min(ticks), max(ticks)))
print('pool records per scan: min %d max %d' % (min(nrec), max(nrec)))
print('behaviour pointer (+16) of every record present across the scans:')
for b, c in poolh.most_common(): print('  $%06x  %d record-instances' % (b, c))
print('behaviour pointer of the CHOSEN record:')
for b, c in chosen.most_common(): print('  $%06x  %d scans' % (b, c))
print('PRECONDITION  scans with >=1 homing ($21d08) record in the pool: %d of %d  (ticks %s..%s)' % (homing_present, n, min(hp_ticks) if hp_ticks else '-', max(hp_ticks) if hp_ticks else '-'))
print('RESULT        scans whose chosen record is a homing ($21d08) record: %d' % homing_chosen)
print('homing chosen / homing present: %d/%d scans' % (homing_chosen, homing_present))
print('scans with a non-zero $27134 queue: %d;  chosen record at a queue position: %d' % (q_nonzero, queue_hit))
