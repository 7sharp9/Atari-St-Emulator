"""Gate for the chaser `$21afe` (and its wait `$21ae2`): one actor-walker pass, record at arrival k -> record at arrival k+1,
predicted from the closed form read in `$21ae2..$21c3e`, against a shot_capture.capture run (every $255d4 arrival's pool).

    python3 gate_chaser.py <snapshot> <ticks> [--control drag|pull|clamp|period|oldship] [--json out.json]
    python3 gate_chaser.py --capture <shot_capture/mothership_drive json> [--control ...]   (gate an existing capture)

Model (per pass, record x y z vx vy vz life pad b; ship = the ship point AFTER this tick's move, words $270b0..$270b4):
  wait ($21ae2): life bit 15 cleared, life - 1; while >= 0 only the life word changes; at < 0 vector := $21afe, life := $1ff and the
                 body below runs in the same pass.
  body ($21afe): bit 15 of life (hit, or ground at or above y: the walker or-s $a000) -> kill path, no move.
                 life - 1; at < 0 velocity negated and life := $1ff.   pos += vel.
                 d = gh - y - $100 (words); when negative vy += d.   v += (ship - pos) >> 7 each axis.   v -= v >> 6.
                 clamp each axis to -$80 .. $7f ... as coded: v >= 0 -> min(v, $80), v < 0 -> max(v, -$80).
The mothership's chaser `$2279a` is the same body with clamp +$70/-$70 and reversal every $a9 ticks, no wait state; its kill path
`$22784` has one award (150) for a hit and for the ground. A record the ship box flagged this pass ($21654, event ship_hit) gets
life bits 15 and 13 set after its pass (`$21648..$21650`), so its record at k+1 is compared with those two bits or-ed in.
Controls: drag (>> 5), pull (>> 6), clamp ($7f), period ($1fe), oldship (ship before the move).
The scripts import reversing/virus/py/mpc modules by path. Writes only the --json file.
"""
import json, os, struct, sys, time

import bh
R = bh.ROOT
import shot as S
import shot_capture as C

CHASER, WAIT, MC = 0x21afe, 0x21ae2, 0x2279a
PARAM = {CHASER: (0x80, 0x1ff), MC: (0x70, 0xa9)}
s16 = S.s16
import collections
EXER = collections.Counter()

def chaser_step(a, ship, control='none'):
    x, y, z, vx, vy, vz, life, pad, b = a
    gh = S.aground(x, z)
    lw = life & 0xffff
    if gh <= y:
        lw |= 0xa000
    if b == WAIT:
        lw &= 0x7fff
        n = s16(lw - 1)
        if n >= 0:
            return [x, y, z, vx, vy, vz, n, pad, WAIT], None
        lw = 0x1ff; b = CHASER
    if lw & 0x8000:
        return None, ('grounded' if lw & 0x2000 else 'killed')
    hi, period = PARAM[b]
    if control == 'period':
        period -= 1
    n = s16(lw - 1)
    if n < 0:
        vx, vy, vz = s16(-vx), s16(-vy), s16(-vz); n = period
        EXER['reversal'] += 1
    sp = list(ship)
    if control == 'oldship':
        sp = list(ship)  # replaced by the caller
    x, y, z = s16(x + vx), s16(y + vy), s16(z + vz)
    d = s16(gh - y - 0x100)
    if d < 0:
        vy = s16(vy + d)
    ps = 6 if control == 'pull' else 7
    vx = s16(vx + (s16(sp[0] - x) >> ps)); vy = s16(vy + (s16(sp[1] - y) >> ps)); vz = s16(vz + (s16(sp[2] - z) >> ps))
    ds = 5 if control == 'drag' else 6
    vx = s16(vx - (vx >> ds)); vy = s16(vy - (vy >> ds)); vz = s16(vz - (vz >> ds))
    if control == 'clamp':
        hi -= 1
    def cl(v):
        if v > hi or v < -hi:
            EXER['clamped axis'] += 1
        return min(v, hi) if v >= 0 else max(v, -hi)
    return [x, y, z, cl(vx), cl(vy), cl(vz), n, pad, b], None


def main():
    args = sys.argv[1:]
    control = 'none'; out = None
    if '--control' in args:
        i = args.index('--control'); control = args[i + 1]; del args[i:i + 2]
    if '--json' in args:
        i = args.index('--json'); out = args[i + 1]; del args[i:i + 2]
    t0 = time.time()
    if args[0] == '--capture':
        snap = args[1]; cap = json.load(open(snap))
    else:
        snap, N = args[0], int(args[1])
        cap = C.capture('auto', N, snap=snap)
    S.load_hmap(cap['snap'])           # the actor walker's height map of THIS capture's landscape ($42a58 of the start snapshot)
    rows = cap['rows']
    pools = [S.unpack_pool(r['pool']) for r in rows]
    tot = [0, 0]; byb = {}; bad = []
    for k in range(len(rows) - 1):
        r, nx = rows[k], rows[k + 1]
        if any(e['e'] in ('dead', 'crash') for e in r['ev']):
            continue
        if r['tick_steps'] < 5000 or nx['tick44'] == r['tick44']:   # a re-arrival at $255d4 (an interrupt at the breakpoint): no walker pass
            continue
        if nx.get('poked'):                                         # a labelled poke changed the records between the two reads
            continue
        kills = [e['idx'] for e in r['ev'] if e['e'] == 'kill']
        hit_idx = {e['idx'] for e in r['ev'] if e['e'] == 'hit'}
        P, Q = pools[k], pools[k + 1]
        for i, a in enumerate(P):
            if a[8] not in (CHASER, WAIT, MC):
                continue
            ship = nx['pos'] if control != 'oldship' else r['pos']
            got, info = chaser_step(a, ship, control)
            key = {WAIT: 'wait', CHASER: '21afe', MC: '2279a'}[a[8]]
            t = byb.setdefault(key, [0, 0]); t[1] += 1
            if got is None:
                t[0] += i in kills
                if i not in kills and len(bad) < 8: bad.append((k, i, 'predicted dead, not killed', a, info, [e['e'] for e in r['ev']]))
                continue
            # a kill swap-removes the last record into the killed slot and walks it there this pass: its events carry that slot
            swapped = len(kills) == 1 and kills[0] < i == len(P) - 1 and control != 'noswap'
            slot = kills[0] if swapped else i
            if slot in hit_idx:                    # the shot's hit bit is set before the pass: the record dies instead (not counted)
                t[1] -= 1
                continue
            if slot in {e['idx'] for e in r['ev'] if e['e'] == 'ship_hit'}:
                got[6] = s16(got[6] | 0xa000)
            if swapped:                            # exact: the record at k+1 in the killed slot is the model's, all nine fields
                EXER['swap-walked'] += 1
                ok = list(Q[slot]) == got
                t[0] += ok
                if not ok and len(bad) < 8: bad.append((k, i, 'swap-walked', a, got, list(Q[slot])))
                continue
            if kills:
                cand = [q for q in Q if q[8] == got[8] and q[:6] == got[:6]]
                t[0] += len(cand) == 1
                if len(cand) != 1 and len(bad) < 8: bad.append((k, i, 'reordered pool, candidates', len(cand), a, got))
                continue
            q = list(Q[i])
            ok = q == got
            t[0] += ok
            if not ok and len(bad) < 5:
                bad.append((k, i, a, got, q))
    print('source', snap, 'ticks', len(rows), 'control', control, f'{time.time() - t0:.0f}s')
    for key, (a, b) in sorted(byb.items()):
        print(f'  chaser {key:5s} record at k+1 == model (all nine fields): {a}/{b}')
    print('  exercised by the model:', dict(EXER))
    for x in bad:
        print('  miss', x)
    if out:
        json.dump({'snap': snap, 'control': control, 'tally': byb, 'bad': bad}, open(out, 'w'))

if __name__ == '__main__':
    main()
