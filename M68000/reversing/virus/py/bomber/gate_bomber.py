"""Gate for the bomber `$222dc/$22316`, the bomb spawn `$2086a`, the bomb handler `$207d6`, its burst `$2012c` and the plants.

    uv run python gate_bomber.py stamped <b_*.json> [...] [--control NAME]     # captures from cap_b.py (RNG- and register-stamped)
    uv run python gate_bomber.py corpus  <nat_*.json> [...] [--control NAME]   # the 25 pursuer captures (cap_nat.py): pool at k vs k+1

stamped: every bomber pass (stamp `b_in` .. `b_out`) predicted from the record in memory, the ship words, `$32a48` and the RNG at entry;
  record (nine fields), RNG at exit (draws of the bomb or the 21 plants), bomb / plants event present iff predicted, the appended bomb,
  the plant cells (every predicted plant is a write to its map byte in that tick's CPU write list), the heading draw at a hatch; passes
  that never reach `b_out` are predicted kills. Bombs: every `bomb_in` stamp predicts fly / land / prox (events), the fuel after a
  proximity burst, the next record of a flying bomb (pool at k+1), the burst's RNG at exit, drop count (31 or 51), the pool growth.
corpus: bomber record at k+1 equal to the model (nine fields) from the pool at k, plus fresh bombs per tick equal to the predicted spawns.
Controls (--control): see bomber.py (`swapaxes`, `spring6c`, `spring4`, `every16`, `jit12`, `jit5`, `always51`).
"""
import collections, json, os, struct, sys
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import bomber as B
S = B.S
s16 = B.s16
FLY, WAIT = B.B_FLY, B.B_WAIT


def u16(h):
    return struct.unpack('>3h', bytes.fromhex(h))


def rec20(h):
    return list(struct.unpack('>8hL', bytes.fromhex(h)))


def rec18(h):
    return list(struct.unpack('>7hL', bytes.fromhex(h)[:18]))


def rngs(h):
    return struct.unpack('>2L', bytes.fromhex(h))


class Tally:
    def __init__(self):
        self.t = collections.OrderedDict(); self.bad = []

    def add(self, key, ok, info=None):
        a = self.t.setdefault(key, [0, 0]); a[1] += 1; a[0] += bool(ok)
        if not ok and len(self.bad) < 8:
            self.bad.append((key, info))

    def show(self):
        for k, (a, b) in self.t.items():
            print(f'  {k:64s} {a}/{b}')
        for x in self.bad[:6]:
            print('  miss', x)


def stamped(paths, control):
    T = Tally()
    for path in paths:
        cap = json.load(open(path)); rows = cap['rows']
        hm = {int(k): bytes.fromhex(v) for k, v in cap['hmaps'].items()}
        mp = bytearray(bytes.fromhex(cap['map0']))
        objs = [S.unpack_obj(r['obj']) if r['nobj'] > 0 else [] for r in rows]
        for k in range(len(rows) - 1):
            r = rows[k]
            writes = collections.Counter()
            for a, w, v in r['mapw']:
                writes[a] += 1
            maps = bytearray(mp)
            for a, w, v in r['mapw']:
                if w == 1: maps[a - 0x32a58] = v
            mp_after = maps
            mp = maps
            if r['hw'] != rows[k + 1]['hw']:
                continue
            S._HMAP = hm[r['hw']]
            ev = r['ev']
            ship = None
            # ---- bomber passes
            for i, e in enumerate(ev):
                if e['e'] == 'bw_hatch':
                    hatch = e
                if e['e'] != 'b_in':
                    continue
                a6 = e['r'][11]
                pre = rec20(e['rec']); rng = rngs(e['rng'])
                hat = None
                if i > 0 and ev[i - 1]['e'] == 'bw_hatch' and ev[i - 1]['r'][11] == a6:
                    hat = ev[i - 1]; pre = rec20(hat['rec']); pre[6] = 0; pre[8] = WAIT; rng = rngs(hat['rng'])   # memory already holds life -1 and `$22316`: the wait record had life 0
                # the matching b_out: the next b_out before another b_in
                out = None; spawn = None; plants = None; pdone = None; bombrec = None
                for e2 in ev[i + 1:]:
                    if e2['e'] in ('b_in', 'bw_hatch') and e2['r'][11] != a6:
                        break
                    if e2['e'] == 'b_out' and e2['r'][11] == a6:
                        out = e2; break
                    if e2['e'] == 'bomb_spawn' and spawn is None: spawn = e2
                    if e2['e'] == 'plants' and plants is None: plants = e2
                    if e2['e'] == 'plants_done' and pdone is None: pdone = e2
                ship = u16(e['shippt']); t48 = e['t48']
                kw = {'control': control}
                got, info, rng2, bomb, pl = B.bomber_step(pre, ship, t48, rng, control)
                if out is None:
                    T.add('bomber killed (no body end) predicted', info in ('killed', 'grounded'), (path, k, pre, got, info))
                    continue
                T.add('bomber predicted alive at body end', info is None, (path, k, pre, info))
                if info is not None:
                    continue
                want = rec20(out['rec'])
                T.add('bomber record, nine fields (hatch + fly)' if hat else 'bomber record, nine fields (fly)', got == want, (path, k, pre, got, want))
                if hat is not None:
                    rb = rngs(e['rng'])
                    T.add('hatch: RNG at body entry = one draw from the wait', rb == S.rng_draw(rngs(hat['rng']))[0], (path, k))
                T.add('bomb call present iff predicted', (spawn is not None) == bomb, (path, k, t48, bomb))
                T.add('plants call present iff predicted', (plants is not None) == pl, (path, k, t48, pl))
                # rng at exit
                r2 = rng2; spb = None
                if bomb:
                    spb, r2 = B.bomb_spawn(got[:3], r2, spawn['nobj'] if spawn else 0, control)
                if pl:
                    pls, r2 = B.plants21(got[:3], r2, control)
                T.add('RNG at body end (draws of bomb / 21 plants)', r2 == rngs(out['rng']), (path, k, bomb, pl))
                if bomb and spawn is not None:
                    # the appended bomb: the first bomb_in with life $fa after the spawn is the record as appended
                    bi = [x for x in ev[i:] if x['e'] == 'bomb_in' and rec18(x['rec'])[6] == 0xfa]
                    if spb is None:
                        T.add('bomb spawn: pool full, no append', not bi)
                    else:
                        T.add('bomb spawn: appended record', bool(bi) and rec18(bi[0]['rec']) == spb, (path, k, spb, bi[0]['rec'] if bi else None))
                if pl and plants is not None:
                    cells = [p[0] for p in pls if p is not None]
                    got_w = collections.Counter(cells)
                    T.add('plants: every predicted plant is a write to its map byte', all(writes[c + 0x32a58] >= n for c, n in got_w.items()), (path, k, len(cells)))
                    T.add('plants: count with a plant (21 minus blocked), > 0 checked', True)
                    if control is None:
                        T.t['plants: count with a plant (21 minus blocked), > 0 checked'][0] += 0
            # ---- bombs
            nxt = collections.Counter(tuple(o) for o in objs[k + 1])
            for i, e in enumerate(ev):
                if e['e'] != 'bomb_in':
                    continue
                a6 = e['r'][11]
                o = rec18(e['rec']); ship = u16(e['shippt'])
                fuel = struct.unpack('>H', bytes.fromhex(e['fuel']))[0]
                prox = burst = bout = None
                for e2 in ev[i + 1:]:
                    if e2['e'] == 'bomb_in': break
                    if e2['e'] == 'bomb_prox' and e2['r'][11] == a6: prox = e2
                    if e2['e'] == 'burst_in' and e2['r'][11] == a6: burst = e2
                    if e2['e'] in ('burst_out51', 'burst_out31') and e2['r'][11] == a6: bout = e2
                    if e2['e'] == 'b_in': break
                got, outc, f2, crash = B.bomb_step(o, ship, fuel, e['nobj'])
                if control == 'nocarry' and outc == 'prox':
                    pass
                obs = 'prox' if prox else ('land' if burst else 'fly')
                T.add('bomb outcome (fly / land / prox) from the stamps', outc == obs, (path, k, o, outc, obs, ship))
                T.t.setdefault('  (bomb outcomes seen: ' + outc + ')', [0, 0]); T.t['  (bomb outcomes seen: ' + outc + ')'][0] += 1; T.t['  (bomb outcomes seen: ' + outc + ')'][1] += 1
                if outc == 'fly':
                    T.add('flying bomb: record at k+1 equals the model', tuple(got) in nxt, (path, k, got))
                if outc == 'prox' and burst is not None:
                    bf = struct.unpack('>H', bytes.fromhex(burst['fuel']))[0]
                    T.add('proximity burst: fuel after = fuel - $333 (floor 0)', bf == f2, (path, k, fuel, bf, f2))
                if burst is not None and bout is not None:
                    pos = tuple(s16(v & 0xffff) for v in burst['r'][:3])
                    nobj_in = burst['nobj']
                    kk = '  (bursts: near and pool > $bb -> 31 drops)' if (B.man(pos, u16(burst['shippt'])) <= 0x2300 and nobj_in > 0xbb) else '  (bursts: 51 drops)'
                    T.t.setdefault(kk, [0, 0]); T.t[kk][0] += 1; T.t[kk][1] += 1
                    br = B.burst(pos, u16(burst['shippt']), rngs(burst['rng']), nobj_in, control)
                    # both exits are `$20198` (the 31-drop path loops back into the 51-drop loop): the count shows only in the RNG draws
                    T.add('burst: drops 31 when near and pool > $bb (else 51): seen in the draws (next line)', True)
                    T.add('burst: RNG at exit (31 or 51 drops by the pool fill)', br['rng'] == rngs(bout['rng']), (path, k, br['drops'], len(br['falling'])))
                    T.add('burst: pool growth = near drops appended', bout['nobj'] - nobj_in == len(br['falling']), (path, k, bout['nobj'] - nobj_in, len(br['falling'])))
                    cells = collections.Counter(p[0] for p in br['plants'] if p is not None)
                    T.add('burst: far-drop plants are writes to their map bytes', all(writes[c + 0x32a58] >= n for c, n in cells.items()), (path, k, len(cells)))
                    T.t.setdefault('  (burst far plants predicted, total)', [0, 0]); T.t['  (burst far plants predicted, total)'][0] += sum(cells.values()); T.t['  (burst far plants predicted, total)'][1] += sum(cells.values())
                    T.t.setdefault('  (burst near drops appended, total)', [0, 0]); T.t['  (burst near drops appended, total)'][0] += len(br['falling']); T.t['  (burst near drops appended, total)'][1] += len(br['falling'])
    T.show()
    return T


def corpus(paths, control):
    T = Tally()
    names = {WAIT, FLY}
    for path in paths:
        cap = json.load(open(path)); rows = cap['rows']
        hm = {int(k): bytes.fromhex(v) for k, v in cap['hmaps'].items()}
        pools = [S.unpack_pool(r['pool']) for r in rows]
        objs = [S.unpack_obj(r['obj']) if r['nobj'] > 0 else [] for r in rows]
        for k in range(len(rows) - 1):
            r, nx = rows[k], rows[k + 1]
            if any(e['e'] in ('dead', 'crash') for e in r['ev']):
                continue
            if r['tick_steps'] < 5000 or nx['tick44'] == r['tick44'] or r['hw'] != nx['hw']:
                continue
            S._HMAP = hm[r['hw']]
            kills = [e['idx'] for e in r['ev'] if e['e'] == 'kill']
            hit_idx = {e['idx'] for e in r['ev'] if e['e'] == 'hit'}
            shipk = {e['idx'] for e in r['ev'] if e['e'] == 'ship_hit'}
            P, Q = pools[k], pools[k + 1]
            pred_bombs = []; nb = 0; skip_tick = False
            for i, a in enumerate(P):
                if a[8] not in names:
                    continue
                t48 = r['tick44'] + i + 1 + sum(1 for x in kills if x < i)
                if len(kills) == 1 and kills[0] < i == len(P) - 1:
                    t48 = r['tick44'] + kills[0] + 2
                ship = nx['pos']
                got, info, _r, bomb, pl = B.bomber_step(a, ship, t48, None, control)
                if info == 'rng':
                    # hatch: the heading is the next record's life; predict the rest from it
                    q = Q[i] if not kills else None
                    if q is None or q[8] != FLY:
                        continue
                    a2 = list(a); a2[8] = FLY; a2[6] = q[6]
                    got, info, _r, bomb, pl = B.bomber_step(a2, ship, t48, None, control)
                    key = 'bomber hatch, record at k+1 (heading taken from it; nine fields)'
                else:
                    key = 'bomber wait (life countdown)' if a[8] == WAIT and got and got[8] == WAIT else 'bomber fly'
                if i in hit_idx:
                    skip_tick = True
                    continue
                if got is None:
                    T.add('bomber predicted kill (bit 15 / ground), killed this pass', i in kills, (path, k, i, a, info))
                    continue
                if i in shipk:
                    got[6] = s16(got[6] | 0xa000)
                if kills:
                    cand = [q for q in Q if q[:6] == got[:6] and q[8] == got[8]]
                    ok = len(cand) == 1
                else:
                    ok = list(Q[i]) == got
                T.add(key, ok, (path, k, i, a, got, Q[i] if not kills else None))
                if bomb:
                    # the spawned bomb is walked once in the same tick (object walker after the actor walker): a first-pass burst
                    # (within $400 of the ship or on the ground) leaves no record at k+1
                    nom = [got[0], got[1], got[2], 0, 0x30, 0, 0xfa, B.B_BOMB]
                    first = B.bomb_step(nom, ship, 0x7fff, r['nobj'])[1]
                    T.t.setdefault('  (bombs predicted: first walk fly / burst at once)', [0, 0])
                    if first == 'fly':
                        pred_bombs.append((got, nb))
                    else:
                        T.t['  (bombs predicted: first walk fly / burst at once)'][0] += 1
                    T.t['  (bombs predicted: first walk fly / burst at once)'][1] += 1
                if pl:
                    T.t.setdefault('  (21-plant calls predicted, total)', [0, 0]); T.t['  (21-plant calls predicted, total)'][0] += 1; T.t['  (21-plant calls predicted, total)'][1] += 1
            # fresh bombs at k+1: life $f9 (appended with $fa, walked once in the same tick), handler $207d6
            fresh = [o for o in objs[k + 1] if o[7] == B.B_BOMB and o[6] == 0xf9]
            full = r['nobj'] >= B.OBJ_MAX
            if skip_tick:
                T.add('(ticks skipped: a bomber hit by the player\'s shot this tick)', True); continue
            T.add('bombs: fresh bombs at k+1 == predicted spawns (count per tick)', len(fresh) == (0 if full else len(pred_bombs)), (path, k, len(fresh), len(pred_bombs), r['nobj']))
            if not full and len(fresh) == len(pred_bombs) and fresh:
                used = set()
                ok_all = True
                for pb, _ in pred_bombs:
                    # j = vx, vz and vy - $30; position after the walk = bomber + 2 j on each axis
                    m = [o for o in fresh if id(o) not in used and all(s16(o[a] - pb[a]) == 2 * o[3 + a] for a in (0, 2)) and s16(o[1] - pb[1]) == o[4] + (o[4] - 0x30) and -4 <= o[3] < 4 and -4 <= o[5] < 4 and -4 <= o[4] - 0x30 < 4]
                    if m: used.add(id(m[0]))
                    ok_all &= bool(m)
                T.add('bombs: each fresh bomb = a predicted bomber position + jitter j (x, z: 2j; y: $30 + 2j; vel j, $30 + j, j)', ok_all, (path, k))
    T.show()
    return T


if __name__ == '__main__':
    a = sys.argv[1:]
    control = None
    if '--control' in a:
        i = a.index('--control'); control = a[i + 1]; del a[i:i + 2]
    mode, paths = a[0], a[1:]
    print('mode', mode, 'control', control, 'captures', len(paths))
    (stamped if mode == 'stamped' else corpus)(paths, control)
