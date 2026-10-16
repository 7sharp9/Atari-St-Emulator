"""census_cmp.py - read census_run.py's watch logs and judge, per disagreeing pair, the walker against the game.

Per man (record writes filtered to his 50 bytes, grouped into clusters with a gap > 40000 steps):
  own ticks      clusters whose writes all come from the walk handlers and leaves (trace_cmp.OWN); each is predicted
                 from the previous state with walker.tick() and compared on walker.CMP
  outside        clusters with any other writer (the pcs are kept: $3574 = $34f2 summons, $5f78 = $5cde stamp, ...)
  game arrival   an own cluster that leaves the walk modes standing on the target
Then the model verdicts:
  plain          walker.simulate from the start state, no outside writes (the old prediction, from the full state)
  replay         walker.tick() with each outside cluster's writes applied at the point it happened in the game
                 (the walker plus the dispatchers as observed)
Usage: census_cmp.py bc_full.json [--detail]
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
import os as _os
WORK = next(p for p in HERE.parents if (p / 'tools' / 'rdis.py').exists()) / _os.environ.get('CMD_WORK', 'scratchpad/cmd1') / 'walk'
WORK.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(HERE))
import walker  # noqa: E402
import census_run  # noqa: E402
from trace_cmp import own, RX  # noqa: E402

BASE = 0x51b66
HEX = re.compile(r'([0-9a-f]{2} ){49}[0-9a-f]{2}\s*')


def events(errf, objs):
    """per obj: list of clusters [(step, pc, off, n, v)], in order."""
    rng = {o: (BASE + 50 * o, BASE + 50 * o + 50) for o in objs}
    cl = {o: [] for o in objs}
    last = {o: None for o in objs}
    for ln in open(errf):
        m = RX.search(ln)
        if not m:
            continue
        a = int(m[4], 16)
        for o, (lo, hi) in rng.items():
            if lo <= a < hi:
                st = int(m[1])
                n = {'Byte': 1, 'Word': 2, 'Long': 4}[m[3]]
                if last[o] is None or st - last[o] > 40000:
                    cl[o].append([])
                cl[o][-1].append((st, int(m[2], 16), a - lo, n, int(m[5], 16)))
                last[o] = st
                break
    return cl


def judge(mp, rec0, clusters):
    rec = bytearray(rec0)
    ok = bad = skip = 0
    outside = []
    arrived = None
    first_bad = None
    rep = walker.decode(rec)          # replay state
    rep_arr = None
    rep_dead = None
    for i, c in enumerate(clusters):
        pre = walker.decode(rec)
        for (_st, _pc, off, n, v) in c:
            rec[off:off + n] = v.to_bytes(n, 'big')
        post = walker.decode(rec)
        is_own = all(own(pc) for (_s, pc, *_r) in c)
        if not is_own:
            outside.append((i, sorted({'%x' % pc for (_s, pc, *_r) in c if not own(pc)}), pre['mode'], post['mode'],
                            post['prev'], (post['tx'], post['ty'])))
            # replay: take the outside writes on top of the replay state (only the bytes they wrote)
            r = bytearray(_encode(rep, rec))
            for (_st, pc, off, n, v) in c:
                if not own(pc):
                    r[off:off + n] = v.to_bytes(n, 'big')
            rep = walker.decode(r)
            if rep_arr is None and rep_dead is None and not all(own(pc) for (_s, pc, *_r) in c):
                pass
            continue
        if not any(off not in (0, 1, 2, 3, 14) for (_s, _pc, off, _n, _v) in c):
            continue                                       # bucket links / anim byte only: not this man's tick
        oracle = None                                      # a moving entity's position, as the game copied it
        if (pre['mode'] == 0x10 and pre['prev'] == 0x2e) or (pre['mode'] == 0x4a and pre['w28'] != 0):
            oracle = (post['tx'], post['ty'])
        if pre['mode'] in walker.WALK:
            try:
                p2 = dict(pre)
                if oracle and pre['mode'] == 0x10:
                    p2['tx'], p2['ty'] = oracle
                pr = walker.tick(mp, p2, lead_pos=oracle, chase_static=True)
                if pr['mode'] == 0x100:
                    skip += 1
                elif any(pr[k] != post[k] for k in walker.CMP):
                    bad += 1
                    if first_bad is None:
                        first_bad = (i, {k: (pre[k], pr[k], post[k]) for k in walker.CMP if pr[k] != post[k]})
                else:
                    ok += 1
            except walker.Unmodelled:
                skip += 1
            if arrived is None and post['mode'] not in walker.WALK and (
                    (post['x'], post['y']) == (post['tx'], post['ty']) or (pre['mode'] == 0x10 and pre['prev'] == 0x2e)):
                arrived = i
        else:
            skip += 1
        # replay one tick
        if rep_arr is None and rep_dead is None:
            if rep['mode'] in walker.WALK:
                try:
                    if oracle and rep['mode'] == 0x10 and rep['prev'] == 0x2e:
                        rep['tx'], rep['ty'] = oracle
                    rep = walker.tick(mp, rep, lead_pos=oracle or (post['tx'], post['ty']), chase_static=True)
                except walker.Unmodelled as e:
                    rep_dead = str(e)
                if rep['mode'] == 0x100 or (rep['mode'] not in walker.WALK and (rep['x'], rep['y']) == (rep['tx'], rep['ty'])):
                    rep_arr = i
            else:
                rep_dead = 'mode %02x' % rep['mode']
    return dict(ok=ok, bad=bad, skip=skip, outside=outside, arrived=arrived, first_bad=first_bad, nclus=len(clusters),
                rep_arr=rep_arr, rep_dead=rep_dead, rep_state=rep)


def _encode(st, like):
    r = bytearray(like)
    for k, (o, n, sg) in walker.FIELDS.items():
        r[o:o + n] = (st[k] & ((1 << (8 * n)) - 1)).to_bytes(n, 'big')
    return r


def main(argv):
    d = json.load(open(argv[0]))
    detail = '--detail' in argv
    res = []
    T = Counter()
    mp_cache = {}
    for snap, grp in census_run.jobs(d):
        stem = '%s_%d' % (Path(snap).stem, grp[0]['obj'])
        out, err = WORK / os.environ.get('RUNS', 'runs') / (stem + '.out'), WORK / os.environ.get('RUNS', 'runs') / (stem + '.err')
        if not (out.exists() and out.read_text().rstrip().endswith('DONE')):
            continue
        hexl = [l for l in open(out) if HEX.fullmatch(l)]
        if snap not in mp_cache:
            mp_cache = {snap: walker.astar.Map(snap)}
        mp = mp_cache[snap]
        cls = events(err, [x['obj'] for x in grp])
        for k, x in enumerate(grp):
            rec0 = bytes.fromhex(hexl[k].replace(' ', '').strip())
            assert rec0.hex() == x['rec'], (stem, x['obj'])
            j = judge(mp, rec0, cls[x['obj']])
            first_out = j['outside'][0][0] if j['outside'] else None
            # the plain model's arrival, in cluster units ~ ticks: compare with the first outside write
            plain = x['full_arrives']
            pa, pt = x['full_arrives'], x['full_tick']
            if pa is None:
                verdict = 'plain-unmodelled/game-' + ('arrives' if j['arrived'] is not None else 'stuck')
            elif j['arrived'] is not None:
                verdict = 'agree: both arrive' if pa else 'DISAGREE: game arrives, plain stuck'
            elif not pa:
                verdict = 'agree: both stuck'
            elif first_out is not None and first_out < pt:
                verdict = 'plain arrives, game redispatched first'
            else:
                verdict = 'DISAGREE: plain arrives, game stuck, no redispatch before'
            T[verdict] += 1
            T[('replay', 'arrives' if j['rep_arr'] is not None else ('unmodelled' if j['rep_dead'] and j['rep_dead'].startswith(('chase', 'hand', '4a')) else 'stuck'),
               'game', 'arrives' if j['arrived'] is not None else 'stuck')] += 1
            T['own ticks match'] += j['ok']
            T['own ticks differ'] += j['bad']
            res.append(dict(snap=Path(snap).stem, obj=x['obj'], side=x['side'], prev=x['prev'], mode=x['mode'],
                            plain=(x['full_arrives'], x['full_tick']), verdict=verdict, ok=j['ok'], bad=j['bad'],
                            skip=j['skip'], nout=len(j['outside']), first_out=first_out,
                            out_pcs=sorted({p for o in j['outside'] for p in o[1]}), arrived=j['arrived'],
                            rep_arr=j['rep_arr'], rep_dead=j['rep_dead'], first_bad=j['first_bad']))
    json.dump(res, open(WORK / os.environ.get('CMP_OUT', 'census_cmp.json'), 'w'), indent=0)
    for k, v in sorted(T.items(), key=str):
        print(k, v)
    pcs = Counter()
    for r in res:
        for p in r['out_pcs']:
            pcs[p] += 1
    print('men with an outside write, by writer pc:', pcs.most_common(30))
    if detail:
        for r in res:
            print(r)


if __name__ == '__main__':
    main(sys.argv[1:])
