"""Gate for the pursuer `$21f00` (Pursuer) and, with the same body, the patrol states `$21c42/$21c64/$21d08/$21df6`, one actor-walker pass:
the record at arrival k predicted from its nine fields, the ship after tick k's move and the tick counter, compared with the record at
arrival k+1 of a natural capture (cap_nat.py).

    uv run python reversing/virus/py/behaviours/gate_pursuer.py <cap_nat.json> [...] [--control name]

Pursuer model (body read at `$21f00..$22008`), per pass, A0 = award 500, ship = words $270b0..$270b4 AFTER this tick's move:
  life bit 15 (hit, or ground at or above y: the walker or-s $a000) -> kill path `$216d6`, no move.
  pos += vel; vy += g ($32a3a); v -= v >> 5 on every axis.
  steer `$22c1e` toward the ship EVERY tick (the patrol's attack steers only when $32a48 & 3 = 0): the patrol's steer function.
  thrust `$22d5e` once unless life bit 11 is set (nose down), and TWICE when the ground is within $280 below the record
  (the patrol attack thrusts once there).
  pull `$22ebe`: v += (ship - pos) >> 9 when |dx|+|dy|+|dz| (saturating) <= $1900, else >> 13.
  fires `$22e38` every other tick within $900 (spawns an object; the record is unchanged); no state change, it never returns to the patrol.
Patrol states are shot.actor_step (gated on demo flight 1 by gate_actor.py); here they are gated again on later waves.
Controls: thrust1 (one near-ground thrust), shift (pull >> 8 near), far (pull >> 12 far), steer4 (steer only when the tick counter's
low 2 bits are 0), oldship (the ship before its move), nopull.
"""
import json, os, struct, sys, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import vcommon
ROOT = vcommon.ROOT
sys.path.insert(0, os.path.join(ROOT, 'reversing/virus/py/mpc'))
import shot as S
s16 = S.s16
PURSUER = 0x21f00
EXER = collections.Counter()

def pursuer_step(a, ship, g, tick48=None, control='none', nearg=0x280):
    """a: [x y z vx vy vz life pad behaviour] -> (new record or None, info)."""
    x, y, z, vx, vy, vz, life, pad, b = a
    gh = S.aground(x, z)
    lw = life & 0xffff
    pad &= 0xffff
    if gh <= y:
        lw |= 0xa000
    if lw & 0x8000:
        return None, ('grounded' if lw & 0x2000 else 'killed')
    x, y, z = s16(x + vx), s16(y + vy), s16(z + vz)
    vy = s16(vy + g)
    vx, vy, vz = (s16(v - (v >> 5)) for v in (vx, vy, vz))
    if control != 'steer4' or (tick48 & 3) == 0:
        m, lw, pad = S.patrol_steer((x, y, z), ship, lw, pad, gh)
    else:
        m, lw, pad = S.patrol_hold(lw, pad)
    if not lw & 0x800:
        vx, vy, vz = S.patrol_thrust(m, (vx, vy, vz)); EXER['thrust (bit 11 clear)'] += 1
    if s16(gh - y) <= nearg:
        EXER['near ground'] += 1
        vx, vy, vz = S.patrol_thrust(m, (vx, vy, vz))
        if control != 'thrust1':
            vx, vy, vz = S.patrol_thrust(m, (vx, vy, vz))
    d = S.man((x, y, z), ship)
    near = d <= 0x1900
    sh = 9 if near else 13
    if control == 'shift' and near: sh = 8
    if control == 'far' and not near: sh = 12
    EXER['pull near' if near else 'pull far'] += 1
    if control != 'nopull':
        vx = s16(vx + (s16(ship[0] - x) >> sh)); vy = s16(vy + (s16(ship[1] - y) >> sh)); vz = s16(vz + (s16(ship[2] - z) >> sh))
    return [x, y, z, vx, vy, vz, s16(lw), s16(pad), b], None


def main():
    args = sys.argv[1:]
    control = 'none'
    if '--control' in args:
        i = args.index('--control'); control = args[i + 1]; del args[i:i + 2]
    names = {b: v[0] + '/' + v[1] for b, v in S.KINDS.items() if v[0] in ('patrol', 'pursuer')}
    names[0x2202c] = 'pursuer2/live'
    tally = collections.OrderedDict(); bad = []; skipped = collections.Counter()
    for path in args:
        cap = json.load(open(path)); rows = cap['rows']; hm = {int(k): bytes.fromhex(v) for k, v in cap['hmaps'].items()}
        pools = [S.unpack_pool(r['pool']) for r in rows]
        for k in range(len(rows) - 1):
            r, nx = rows[k], rows[k + 1]
            if any(e['e'] in ('dead', 'crash') for e in r['ev']):
                skipped['dead/crash tick'] += 1; continue
            if r['tick_steps'] < 5000 or nx['tick44'] == r['tick44']:      # a re-arrival at $255d4 (interrupt at the breakpoint): no walker pass
                skipped['re-arrival'] += 1; continue
            if r['hw'] != nx['hw']:
                skipped['wave change'] += 1; continue
            S._HMAP = hm[r['hw']]
            kills = [e['idx'] for e in r['ev'] if e['e'] == 'kill']
            hit_idx = {e['idx'] for e in r['ev'] if e['e'] == 'hit'}
            shipk = {e['idx'] for e in r['ev'] if e['e'] == 'ship_hit'}
            q0 = list(struct.unpack('>3h', bytes.fromhex(r['queue'])[:6]))
            P, Q = pools[k], pools[k + 1]
            for i, a in enumerate(P):
                if a[8] not in names:
                    continue
                t48 = r['tick44'] + i + 1 + sum(1 for x in kills if x < i)
                if len(kills) == 1 and kills[0] < i == len(P) - 1 and control != 'nomove':
                    t48 = r['tick44'] + kills[0] + 2       # swap-remove: the last record is walked in the killed slot, one counter step later
                ship = nx['pos'] if control != 'oldship' else r['pos']
                if control == 'nophase' and a[8] != PURSUER:
                    t48 -= 1
                if a[8] == PURSUER:
                    got, info = pursuer_step(a, ship, r['g'], t48, control)
                elif a[8] == 0x2202c:                    # $2202c: the same body, near-ground test $380 (read); not claimed unless it matches
                    got, info = pursuer_step(a, ship, r['g'], t48, control, nearg=0x380)
                else:
                    got, info = S.actor_step(a, ship=ship, g=r['g'], tick48=t48, queue0=q0)
                if info == 'unmodelled':
                    skipped['unmodelled ' + names[a[8]]] += 1; continue
                key = names[a[8]]
                t = tally.setdefault(key, [0, 0])
                if i in hit_idx:                         # the shot's hit bit is set before the pass: not counted
                    skipped['hit this tick'] += 1; continue
                t[1] += 1
                if got is None:
                    t[0] += i in kills
                    if i not in kills and len(bad) < 6: bad.append((path, k, i, 'predicted dead, not killed', a, info))
                    continue
                if i in shipk:
                    got[6] = s16(got[6] | 0xa000)
                prov = any(e['e'] == 'provoke' for e in r['ev']) and a[8] != PURSUER
                conv = None
                if kills:
                    cand = [q for q in Q if q[:6] == got[:6] and q[8] in (got[8], PURSUER)]
                    t[0] += len(cand) == 1
                    if len(cand) != 1 and len(bad) < 6: bad.append((path, k, i, 'reordered pool, candidates', len(cand), a, got))
                    if len(cand) == 1 and prov and cand[0][8] == PURSUER:
                        conv = cand[0]
                else:
                    q = list(Q[i])
                    if prov and q[8] == PURSUER:        # $201b4 (the provoking scan) ran after this record's pass this tick
                        conv = q
                    elif list(Q[i]) == got:
                        t[0] += 1
                    else:
                        t[0] += 0
                        if len(bad) < 6: bad.append((path, k, i, names[a[8]], a, got, Q[i]))
                if conv is not None:                    # the stored conversion: life bit 14 cleared, behaviour $21f00, the rest as the pass left it
                    t[1] -= 1
                    t2 = tally.setdefault('conversion $201b4', [0, 0]); t2[1] += 1
                    want = list(got); want[6] = s16(want[6] & ~0x4000) if control != 'keepbit' else want[6]; want[8] = PURSUER
                    t2[0] += conv == want
                    if conv != want and len(bad) < 6: bad.append((path, k, i, 'conversion', a, want, conv))
    print('control', control, 'captures', [os.path.basename(p) for p in args])
    for key, (a, b) in sorted(tally.items()):
        print(f'  {key:16s} record at k+1 == model (all nine fields): {a}/{b}')
    print('  exercised:', dict(EXER)); print('  skipped:', dict(skipped))
    for x in bad[:6]: print('  miss', x)

if __name__ == '__main__':
    main()
