"""gate_nat_an.py <T>... - analyse data/gate_nat_<T>.json: gate cycle phases and every drone branch event."""
from lt import *
from wptables import table, COUNT
import collections
for T in [int(a) for a in sys.argv[1:]] or [2, 4, 7]:
    d = json.load(open(os.path.join(DATA, 'gate_nat_%d.json' % T)))
    rows, ng = d['rows'], d['ng']
    tb = table(T); cnt = COUNT[T]
    print('=== Track %d (T=%d): %d gates, %d frames' % (T + 1, T, ng, len(rows)))
    # gate phase table: (pos, dir, route) -> frames
    for g in range(ng):
        c = collections.Counter((x['gpos'][g], x['gdir'][g], x['grt'][g]) for x in rows)
        print('  gate %d (pos,dir,route): frames' % g, sorted(c.items()))
        ch = [(i, x['gpos'][g], x['gdir'][g], x['grt'][g], x['gtim'][g]) for i, x in enumerate(rows) if i and (x['grt'][g] != rows[i - 1]['grt'][g])]
        print('  gate %d route changes (frame, pos, dir, route, timer):' % g, ch[:12])
    ev = []
    for i in range(1, len(rows)):
        for s in (0, 2, 3):
            p, q = rows[i - 1]['wp'][s], rows[i]['wp'][s]
            if p == q: continue
            n = (p + 2) % cnt
            rec = tb[n]
            if rec[3] & 0x200:
                g = rec[3] & 3
                exp_prev = (n + rows[i - 1]['grt'][g]) % cnt
                exp_cur = (n + rows[i]['grt'][g]) % cnt
                ev.append((i, s, p, q, g, rows[i - 1]['grt'][g], rows[i]['grt'][g], rows[i - 1]['gpos'][g], rows[i]['gpos'][g], q == exp_prev, q == exp_cur, rows[i]['gdir'][g]))
    print('  branch events:', len(ev), ' model match (route sampled before/after the crossing frame):', sum(e[9] for e in ev), '/', sum(e[10] for e in ev), 'either:', sum(e[9] or e[10] for e in ev))
    byroute = collections.Counter((e[4], e[3] if e[9] else e[6] if e[10] else None, e[3] == e[6]) for e in ev)
    print('  events by (gate, route used, route stable across the frame):', sorted(byroute.items(), key=str))
    for e in ev[:40]:
        print('   frame %4d slot %d wp %3d -> %3d gate %d route %d/%d pos %d/%d dir %d match %s/%s' % (e[0], e[1], e[2], e[3], e[4], e[5], e[6], e[7], e[8], e[11], e[9], e[10]))
    # which slots ever take the branch
    print('  slots with branch events:', sorted(collections.Counter(e[1] for e in ev).items()))
    # outcome of each route: crashes? flag/stun of the drone within 40 frames after the event
    for e in ev:
        pass
