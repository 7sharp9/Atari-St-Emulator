"""bsp_order_sum.py <dir> - totals over every order_*.json that bsp_order.py wrote (bsp_order_all.sh)."""
import json, glob, collections, sys
T = collections.Counter(); per = collections.Counter(); same = collections.Counter(); pats = collections.Counter(); runs = 0
for f in sorted(glob.glob(sys.argv[1] + '/order_*.json')):
    runs += 1
    for d in json.load(open(f))['draws']:
        c = d.get('cmp')
        if not c: T['not_compared'] += 1; continue
        T['draws'] += 1; T['identical'] += c['same']; per[d['model']] += 1; same[d['model']] += c['same']
        for k, g in (('items', 'items_ok'), ('polys', 'polys_ok'), ('faces', 'faces_ok')):
            T[k] += len(c['model_' + k]); T[g] += c[g]
        T['back_facing'] += sum(v < 0 for v in c['model_faces'])
        T['plane_flags'] += c['np']; T['plane_flags_ok'] += sum(a == b for a, b in zip(c['got_flags'], c['want_flags']))
        T['reentry_dropped'] += d.get('reentry', 0)
        T['clip_path_polys'] += sum(pc == 0x8f14 for _, pc in d['polys'])
        for b, v in c.get('pseudo', []): pats[('pseudo', d['model'], b, v)] += 1
        if c['np']:
            T['draws_with_planes'] += 1; T['reversed_walk_differs'] += c['rev_differs']
            pats[('planes', d['model'], tuple(c['got_flags']))] += 1
print('runs', runs); print(dict(T))
print('per model draws/identical:', {m: (per[m], same[m]) for m in sorted(per)})
print('plane-flag patterns (model, flags): draws', dict(sorted(pats.items(), key=str)))
