"""parse.py <capture.out>... : one row per $117b0 call from capture.sh output:
cumulative step, A3, byte5/6/7 (from the pool dump), D4.b at $117b4 (= byte 7 as read), $57fec, frame D2.w at $1184c.
Then per-record counts and the frame == $100 + byte7 (+ $57fec & 3 when byte7 == $12) check."""
import sys, re
from collections import Counter, defaultdict
for path in sys.argv[1:]:
    L = open(path).read().split('\n'); rows = []; i = 0; step = 0; cur = None
    while i < len(L):
        l = L[i]
        m = re.match(r'--- breakpoint \$(\w+) hit .* after (\d+) step', l)
        if m:
            pc = int(m.group(1), 16); step += int(m.group(2))
            regs = {}
            j = i + 1
            while j < len(L) and not L[j].startswith('PC:'):
                for k, v in re.findall(r'([AD]\d):(\w{8})', L[j]): regs[k] = int(v, 16)
                j += 1
            if pc == 0x117b0:
                cur = {'step': step, 'a3': regs['A3']}
                # following: s 1 register block, then m 57fec 2, then m 4cff8 600
                k = j + 1; blocks = []
                while k < len(L) and len(blocks) < 3:
                    if L[k].startswith('D4:'): blocks.append(('d4', int(L[k].split()[0][3:], 16)))
                    elif re.match(r'^([0-9a-f]{2} )+[0-9a-f]{2}$', L[k].strip()): blocks.append(('m', bytes.fromhex(L[k].replace(' ', ''))))
                    k += 1
                cur['b7read'] = blocks[0][1] & 0xff; cur['fec'] = int.from_bytes(blocks[1][1], 'big'); pool = blocks[2][1]
                o = cur['a3'] - 0x4cff8
                cur['b5'], cur['b6'], cur['b7'] = (pool[o+5], pool[o+6], pool[o+7]) if 0 <= o < 600 else (None, None, None)
                step += 1
            elif pc == 0x1184c and cur:
                cur['frame'] = regs['D2'] & 0xffff; rows.append(cur); cur = None
            i = j
        i += 1
    print('==', path, len(rows), 'calls, steps', rows[0]['step'] if rows else 0, '..', rows[-1]['step'] if rows else 0)
    per = defaultdict(Counter); bad = 0
    for r in rows:
        exp = 0x100 + r['b7read'] + ((r['fec'] & 3) if r['b7read'] == 0x12 else 0)
        if exp != r['frame'] or r['b7'] != r['b7read']: bad += 1
        per[(r['a3'], r['b5'], r['b6'], r['b7'])][r['frame']] += 1
    for k, c in sorted(per.items()):
        print('  rec %x side %s byte6 %s byte7 %s:' % (k[0], k[1], k[2], '%02x' % k[3] if k[3] is not None else '?'),
              ', '.join('$%x x%d' % fc for fc in sorted(c.items())), '(%d calls)' % sum(c.values()))
    print('  formula mismatches:', bad, 'of', len(rows))
    lit = [r for r in rows if r['b7read'] == 0x12]
    if lit:
        print('  lit draws, (step, $57fec, frame):', ' '.join('%d:%02x:%x' % (r['step'], r['fec'] & 0xff, r['frame']) for r in lit[:24]))
