"""(promoted: reversing/captive/py/ai/ratt/gen_hits.py; outputs under scratchpad/captive/ratt/) Hits on the item-$66 writers during a generator call, and the writer PC of each $66 item stored (watch on the object list).
Run from a snapshot stopped at $b5c2 (jsr 32(A4) into fed_MapGen): land_mg.snap (D2 = 2, the compound) or in_mg.snap (D2 = 0, the base).
Usage: gen_hits.py <snap> <steps> [D0] [D2]   (optional D0/D2 are labelled register pokes at the $b5c2 stop, for controls)
$26946 word 1 (called only at $23f64 in $23e80), $268f8 word 0 and $2695e word 2 (base 0), $26682 the object-insert routine
(D0 = type, D3 = word), $24d7e cell address."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from objs import R, StServer, snappath, A6, objlist, OUT
s = StServer(R); s('load', snapshot=snappath(sys.argv[1]))
for i, r in enumerate(('d0', 'd2')):
    if len(sys.argv) > 3 + i: s('set_reg', name=r, value=sys.argv[3 + i]); print('POKE', r, '=', sys.argv[3 + i])
print('regs D0..D2', [hex(s.reg(r)) for r in ('d0', 'd1', 'd2')], 'pc', hex(s.reg('pc')))
wid = s('watch_add', lo='$1bf3a', hi='$1c739', kind='w', max_events=100000)['id']
addrs = ['$23e80', '$23f64', '$26946', '$268f8', '$2695e', '$26682']
r = s('hits', steps=int(sys.argv[2]), addrs=addrs)
for h in r['hits']:
    print(h['addr'], 'count', h['count'], 'first step', h['first'])
ev = s('watch_events', id=wid); ev = ev[0] if isinstance(ev, list) else ev
# writers of the item type byte $66 into the list: a long write whose high byte is $66
seen = {}
for e in ev['events']:
    seen.setdefault((e['pc'], e['value']), 0); seen[(e['pc'], e['value'])] += 1
print('watch events', len(ev['events']))
for (pc, v), n in sorted(seen.items()):
    if str(v).lower().startswith('$66') or str(v).lower().startswith('$0066'):
        print('  $66 write: pc', pc, 'value', v, 'x', n)
print('return pc', hex(s.reg('pc')))
p, recs = objlist(s)
for a, x, y, items in recs:
    for it in items:
        if it[0] == 0x66: print(f'item $66 at ${a:x} cell ({x},{y}) bytes {it.hex()} (word {int.from_bytes(it[1:3], "big")})')
s.close()
