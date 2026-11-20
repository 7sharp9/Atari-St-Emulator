"""Gate for the two-hit pursuer's hit paths (pursuer2.py): first hit `$22164`, damaged `$221ac`, kill `$216d6`.

    uv run python gate_pursuer2.py <cap_nat.json> [...] [--control name]

Per tick k of a natural capture (cap_nat.py rows; the pool at arrival k, the ship and score at k+1), each field of the record at k+1
against the model, N/N per field. A shot's hit bit is set after the walker pass (the shot handler runs after it, `hit` event in the tick
that precedes the pass that reads it), so it is or-ed into the model's life word for the slots of this tick's `hit` events; a ship
contact (`ship_hit`) or-s $a000. Kill ticks: the killed record leaves, the pool shrinks by one, the score rises by the award less one
per `fire_post` (the shot's cost), the last record walked in the slot (matched on its first six words).
Controls (each must fail): count4, nofall, award100, stun4, killall, shift9, shift12, nohitbit.
"""
import json, os, struct, sys, collections
import pursuer2 as M
S = M.S; s16 = S.s16
FIELDS = ['x', 'y', 'z', 'vx', 'vy', 'vz', 'life', 'pad', 'beh']
STATS = collections.OrderedDict()
EX = collections.Counter(); SKIP = collections.Counter(); BAD = []


def tally(key, ok, info=None):
    t = STATS.setdefault(key, [0, 0]); t[1] += 1; t[0] += bool(ok)
    if not ok and len(BAD) < 8: BAD.append((key, info))


def fieldwise(kind, want, got, info):
    for f, w, g in zip(FIELDS, want, got):
        tally(f'{kind}.{f}', w == g, info if f == 'life' or w != g else None)
    tally(f'{kind}.ALL9', list(want) == list(got), (info, want, got))


def kills_other(ev):
    return False


def walk_last(rec, ship, g):
    if rec[8] == M.DAMAGED:
        got, _ = M.damaged_step(rec, ship, g, 0)
    elif rec[8] == 0x21f00:
        got, _ = M.GP.pursuer_step(rec, ship, g, 0)
    else:
        got, _ = M.GP.pursuer_step(rec, ship, g, 0, nearg=0x380)
    return got


def main():
    args = sys.argv[1:]; control = 'none'
    if '--control' in args:
        i = args.index('--control'); control = args[i + 1]; del args[i:i + 2]
    if control == 'unsigned_tilt': M.use_signed_tilt(False)
    for path in args:
        cap = json.load(open(path)); rows = cap['rows']
        hm = {int(k): bytes.fromhex(v) for k, v in cap['hmaps'].items()}
        pools = [S.unpack_pool(r['pool']) for r in rows]
        tag = os.path.basename(path)
        for k in range(len(rows) - 1):
            r, nx = rows[k], rows[k + 1]
            dead = any(e['e'] in ('dead', 'crash') for e in r['ev'])          # the walker still ran after the ship's death: only kills are compared
            if r['tick_steps'] < 5000 or nx['tick44'] == r['tick44']: SKIP['re-arrival'] += 1; continue
            if r['hw'] != nx['hw']: SKIP['wave change'] += 1; continue
            if nx.get('poked'): SKIP['next row carries the poke'] += 1; continue
            S._HMAP = hm[r['hw']]
            P, Q = pools[k], pools[k + 1]
            ev = r['ev']; names = [e['e'] for e in ev]
            kills = [e for e in ev if e['e'] == 'kill']
            hit_idx = {e['idx'] for e in ev if e['e'] == 'hit'} if control != 'nohitbit' else set()
            shipk = {e['idx'] for e in ev if e['e'] == 'ship_hit'}
            nfire = names.count('fire_post')
            ship = nx['pos']
            for i, a in enumerate(P):
                if a[8] == M.P2:
                    lw = (a[6] & 0xffff) | (0xa000 if S.aground(a[0], a[2]) <= a[1] else 0)
                    if not lw & 0x8000: continue                 # a normal pass: gate_pursuer.py
                    got, info = M.first_hit_step(a, r['g'], control)
                    kind = 'first'
                elif a[8] == M.DAMAGED:
                    got, info = M.damaged_step(a, ship, r['g'], 0, control)
                    kind = 'dmg-' + str(info[0]) + ('-' + str(info[1]) if info[0] == 'pursue' else '')
                    if info[0] == 'stunned': kind = 'dmg-stunned'
                    if info[0] == 'kill': kind = 'dmg-kill'
                else:
                    continue
                if dead and got is not None: SKIP['dead/crash tick, record not killed'] += 1; continue
                EX[kind] += 1
                if got is None:                                   # kill: the record leaves
                    ok = len(kills) == 1 and kills[0]['idx'] == i and kills[0]['award'] == info[1]
                    tally(f'{kind}.removed with award {info[1]} (kill event slot+award)', ok, (tag, k, i, info, [e.get('award') for e in kills]))
                    if len(kills) == 1:
                        tally('kill.pool count -1', r['npool'] - nx['npool'] == 1, (tag, k))
                        tally('kill.score = +award - fires', nx['score'] - r['score'] == info[1] - nfire, (tag, k, nx['score'] - r['score'], info, nfire))
                        newp, _ = M.kill_step(P, i, r['score'], info[1])
                        last = P[-1]
                        want = [x for x in P[:i] + P[i + 1:]]               # kill_step's pool, before any pass: beh multiset
                        qb = sorted(x[8] for x in Q); pb = sorted(x[8] for x in newp)
                        if not any(n in names for n in ('provoke_entry', 'p2_hit1')) and not kills_other(ev):
                            tally('kill.pool behaviours = kill_step (multiset)', qb == pb, (tag, k, i))
                        if i < len(P) - 1:
                            tally('kill.slot i holds the last record (its behaviour)', Q[i][8] == last[8], (tag, k, i, Q[i], last))
                            if last[8] in (M.P2, 0x21f00, M.DAMAGED) and not (last[6] & 0x8000) and not dead and i not in hit_idx:
                                w = walk_last(last, ship, r['g'])
                                if w is not None:
                                    tally('kill.slot i = the last record walked there (9 fields)', w == Q[i] or w[:6] == Q[i][:6] and False, (tag, k, i, w, Q[i]))
                    continue
                if got is not None:
                    if len(kills) == 0:
                        w = list(got)
                        if i in hit_idx: w[6] = s16(w[6] | 0x8000)
                        if i in shipk: w[6] = s16(w[6] | 0xa000)
                        fieldwise(kind, w, Q[i], (tag, k, i))
                    else:
                        cand = [q for q in Q if q[:6] == got[:6] and q[8] == got[8]]
                        tally(kind + '.(kill tick elsewhere) six words found once', len(cand) == 1, (tag, k, i))
                    if kind == 'first':
                        tally('first.score = +200 - fires', nx['score'] - r['score'] == 200 - nfire - sum(e['award'] for e in kills) + 0 if control != 'award100' else False, (tag, k, nx['score'] - r['score'], nfire))
    print('control', control, 'captures', len(args))
    for key, (a, b) in STATS.items(): print(f'  {key:62s} {a}/{b}')
    print('  exercised:', dict(EX)); print('  skipped:', dict(SKIP))
    for b in BAD[:6]: print('  miss', b)


if __name__ == '__main__':
    main()
