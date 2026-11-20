"""Model and gate of the attractor: `$22486` Attractor_Wait and `$224a6` Attractor (reversing/virus/behaviours.md).

    uv run python gate_attractor.py <cap.json> [...] [--control name]

Bodies read (listing of `$22460..$2264e`, helper `$22ebe`), one actor-walker pass, A0 = award `$3e8` (1000):

`$22486` wait: life bits 15 and 13 cleared (it cannot be hit), life word - 1 stored; while the result is >= 0 the record is
  otherwise unchanged (no move) and the pass ends without the common tail. When it goes negative: behaviour := `$224a6`,
  life word := 5 and the same pass runs `$224a6`.
`$224a6` fly, with the walker's life word lw (bit 15 = hit or ground at or above y, bit 13 = ground):
  lw bit 15 set (`$22460`): bit 13 -> kill; else life BYTE - 1, zero -> kill; else bit 15 cleared and the pass goes on.
  pos += vel; D1 = y - ground + $280; vy -= D1 >> 5; vy -= vy >> 4; clamp vy to [-$60, $60) (the seeder's spring, no vx/vz
  drag; `ground` is the walker's pre-move D7).
  D3 = saturating |dx| + |dy| + |dz| from the record (after its move) to the ship `$270b0` (after this tick's flight).
  D3 <= $b00: ship vel += (record - ship) >> 6 per axis (`$22ebe`, A3 = ship, D4 = 6, A2 = the record).
  D3 <= $700 and `$62a5e` clear: (sound and a beam draw record, not modelled) then fuel `$32a2e` -= 25 (`subi.w #$19`);
  negative -> fuel 0 and `$62a5d` := $ff.  The common tail `$215ea` then ORs $a000 into the life word of a record that
  touches the ship (event `ship_hit`), which kills it on the next pass through bit 13.

Ship after tick k = exact.step_full (the flight tick, gated elsewhere) then the pulls and drains in walker order.
Controls: pull5 / pull7 (>> 5, >> 7), pullold (ship position before its move), drain24 / drain26, drain800 (drain range
$800), pull_a00 (pull range $a00), noclamp (no fuel clamp), spring2c0, drag3, vclampa0, waitkeep (wait keeps bit 15/13), life4.
"""
import json, os, struct, sys, collections
here = os.path.dirname(os.path.abspath(__file__))
ROOT = here
while not os.path.exists(os.path.join(ROOT, 'tools', 'rdis.py')):
    p = os.path.dirname(ROOT)
    if p == ROOT:
        raise SystemExit('repo root (the directory holding tools/rdis.py) not found')
    ROOT = p
sys.path.insert(0, os.path.join(ROOT, 'reversing/virus/py/mpc'))
import shot as S
import exact as E
s16 = S.s16
WAIT, FLY = 0x22486, 0x224a6
EXER = collections.Counter()


def attractor_step(a, ship, control='none'):
    """a: [x y z vx vy vz life pad behaviour] before the pass (hit bit already or-ed into life by the shot or the walker's
    ground test is applied here), ship: ship position after this tick's flight.
    Returns (new record or None when it dies, info, D3): info 'wait', 'wait->fly', 'fly', 'hit', 'killed', 'grounded', 'killed:count'."""
    x, y, z, vx, vy, vz, life, pad, b = a
    lw = life & 0xffff
    pad &= 0xffff
    if b == WAIT:
        lw &= ~0xa000 if control != 'waitkeep' else 0xffff
        lw = (lw - 1) & 0xffff
        if not lw & 0x8000:
            return [x, y, z, vx, vy, vz, s16(lw), s16(pad), b], 'wait', None
        lw = 5
        info = 'wait->fly'
    else:
        gh = S.aground(x, z)
        if gh <= y:
            lw |= 0xa000
        info = 'fly'
        if lw & 0x8000:
            if lw & 0x2000:
                return None, 'grounded', None
            by = ((lw & 0xff) - (1 if control != 'life4' else 2)) & 0xff
            if by == 0:
                return None, 'killed:count', None
            lw = (lw & 0xff00) | by
            lw &= ~0x8000
            info = 'hit'
    gh = S.aground(x, z)
    x, y, z = s16(x + vx), s16(y + vy), s16(z + vz)
    d1 = s16(y - gh + (0x280 if control != 'spring2c0' else 0x2c0))
    vy = s16(vy - (d1 >> 5))
    vy = s16(vy - (vy >> (4 if control != 'drag3' else 3)))
    lim = 0x60 if control != 'vclampa0' else 0xa0
    if vy < 0:
        if not vy > -lim:
            vy = -lim
    elif vy >= lim:
        vy = lim
    d3 = S.man((x, y, z), ship)
    return [x, y, z, vx, vy, vz, s16(lw), s16(pad), FLY], info, d3


def ship_after(row, nxt, pulls, crashing, control='none'):
    """Ship vel and fuel after the flight tick of row k and the attractor effects.
    pulls: list of (record x, y, z, D3) in walker order. Returns (vel, fuel, hit_flag)."""
    f = E.step_full(row['pos'], row['vel'], row['att'], *row['d'], row['g'], row['fuel'])
    vel = list(f['vel']); fuel = f['fuel']; hit = False
    shipp = nxt['pos'] if control != 'pullold' else row['pos']
    sh = {'pull5': 5, 'pull7': 7}.get(control, 6)
    pr = 0xa00 if control == 'pull_a00' else 0xb00
    dr = 0x800 if control == 'drain800' else 0x700
    cost = {'drain24': 24, 'drain26': 26}.get(control, 25)
    for (x, y, z, d3) in pulls:
        if d3 <= pr:
            EXER['pull'] += 1
            for i, t in enumerate((x, y, z)):
                vel[i] = s16(vel[i] + (s16(t - shipp[i]) >> sh))
            if d3 <= dr and not crashing:
                EXER['drain'] += 1
                fuel -= cost
                if fuel < 0:
                    EXER['drain empties fuel'] += 1
                    fuel = 0 if control != 'noclamp' else fuel
                    hit = True
    return vel, fuel, hit


def walk_slots(n, kills):
    """Original index -> slot at which the walker processes it (a kill swap-removes the last record into the slot and
    walks it there at once). kills: kill-event slot indices in order."""
    cur = list(range(n)); slot = {}; j = 0; ki = 0; dead = {}
    while j < len(cur):
        if ki < len(kills) and kills[ki] == j:
            ki += 1; dead[cur[j]] = j
            cur[j] = cur[-1]; cur.pop()
            continue
        slot[cur[j]] = j; j += 1
    return slot, dead


def e_award(r, slot):
    for e in r['ev']:
        if e['e'] == 'kill' and e['idx'] == slot:
            return e['award']
    return None


def gate(paths, control):
    seen = set()
    tally = collections.OrderedDict(); ships = collections.OrderedDict(); bad = []; skipped = collections.Counter()

    def T(d, key, ok):
        t = d.setdefault(key, [0, 0]); t[1] += 1; t[0] += bool(ok)

    for path in paths:
        cap = json.load(open(path)); rows = cap['rows']
        hm = {int(k): bytes.fromhex(v) for k, v in cap['hmaps'].items()}
        for k in range(len(rows) - 1):
            r, nx = rows[k], rows[k + 1]
            if not r['pool']:
                continue
            if nx.get('poke'):
                skipped['tick before a poke (the next row is the poked state)'] += 1; continue
            if r['step'] in seen:
                skipped['row already gated (overlapping captures)'] += 1; continue
            P = S.unpack_pool(r['pool']); Q = S.unpack_pool(nx['pool']) if nx['pool'] else []
            has = [i for i, a in enumerate(P) if a[8] in (WAIT, FLY)]
            if not has:
                continue
            seen.add(r['step'])
            if any(e['e'] in ('dead', 'crash') for e in r['ev']):
                skipped['dead/crash tick'] += 1; continue
            if r['tick_steps'] < 5000 or nx['tick44'] == r['tick44']:
                skipped['re-arrival'] += 1; continue
            if r['hw'] != nx['hw']:
                skipped['wave change'] += 1; continue
            S._HMAP = hm[r['hw']]
            kills = [e['idx'] for e in r['ev'] if e['e'] == 'kill']
            hit_idx = {e['idx'] for e in r['ev'] if e['e'] == 'hit'}
            shipk = {e['idx'] for e in r['ev'] if e['e'] == 'ship_hit'}
            slot, dead = walk_slots(len(P), kills)
            crashing = bool(r['flags']['crashing_62a5e'])
            pulls = []; nrec = 0
            order = sorted(range(len(P)), key=lambda i: slot.get(i, dead.get(i, 999)))
            for i in order:
                a = P[i]
                if a[8] not in (WAIT, FLY) or (i not in slot and i not in dead):
                    continue
                aa = list(a)
                got, info, d3 = attractor_step(aa, nx['pos'], control)
                name = 'wait' if a[8] == WAIT else 'fly'
                if info in ('killed:count', 'grounded'):
                    ok = i in dead and e_award(r, dead[i]) == 0x3e8
                    T(tally, 'kill ' + info, ok)
                    if not ok and len(bad) < 8: bad.append((path, k, i, info, a))
                    continue
                if got is None:
                    continue
                if slot.get(i) in shipk and info != 'wait':
                    got[6] = s16(got[6] | 0xa000)
                    EXER['ship_hit store'] += 1
                if i in hit_idx and a[8] == FLY and control != 'nohitstore':
                    got[6] = s16(got[6] | 0x8000)      # the player's shot ($1ff06) runs after the actor walker: bit 15 for the next pass
                    EXER['shot hit bit stored'] += 1
                if d3 is not None:
                    pulls.append((got[0], got[1], got[2], d3))
                if kills:
                    cands = [q for q in Q if q == got]
                    ok = len(cands) >= 1
                else:
                    ok = i < len(Q) and Q[i] == got
                key = {'wait': 'wait $22486', 'wait->fly': 'wait->fly (hatch)', 'fly': 'fly $224a6', 'hit': 'fly, shot hit (count - 1)'}[info]
                T(tally, key, ok)
                if not ok and len(bad) < 8: bad.append((path, k, i, info, a, got, Q[i] if i < len(Q) else None))
            # the ship
            if kills and any(e['e'] == 'ship_hit' for e in r['ev']) and False:
                pass
            vel, fuel, hit = ship_after(r, nx, pulls, crashing, control)
            near = [p for p in pulls if p[3] <= 0xb00]
            drn = [p for p in pulls if p[3] <= 0x700 and not crashing]
            cls = ('drain %d' % min(len(drn), 3) if drn else 'pull only' if near else 'no pull')
            if len(near) > 1: cls += ' (multi)'
            okv = list(nx['vel']) == vel
            okf = nx['fuel'] == fuel
            if not okf and okv and (fuel - nx['fuel'] == 0x333 or (nx['fuel'] == 0 and 0 < fuel <= 0x333)):
                # an enemy shot ($20310) hit the ship this tick: $333 fuel, clamped at 0 (behaviours.md, "The helpers"); not the attractor's
                skipped['fuel -$333 (enemy shot $20310), vel as modelled'] += 1; okf = True; cls += ' + enemy shot'
            if 'fuelw' in nx:      # cpu watch on $32a2e (cap_poke.py): writes made by the instruction at $225d6 during tick k
                nobs = sum(1 for w_ in nx['fuelw'] if str(w_[0]).lstrip('$').lstrip('0').lower() == '225d6')
                T(ships, 'watch 32a2e: writes by $225d6 == predicted drains', nobs == len(drn))
                EXER['watch: $225d6 writes seen'] += nobs
            if hit:
                T(ships, 'fuel empty: $62a5d set', nx['flags']['hit_62a5d'] == 255 or nx['flags']['hit_62a5d'])
            T(ships, cls + ': ship vel (3 words)', okv)
            T(ships, cls + ': fuel', okf)
            if not (okv and okf) and len(bad) < 14:
                bad.append((path, k, cls, 'vel', nx['vel'], vel, 'fuel', nx['fuel'], fuel, 'u', r.get('u'), 'g', r['g']))
    return tally, ships, bad, skipped


def main():
    args = sys.argv[1:]
    control = 'none'
    if '--control' in args:
        i = args.index('--control'); control = args[i + 1]; del args[i:i + 2]
    tally, ships, bad, skipped = gate(args, control)
    print('control', control, 'captures', [os.path.basename(p) for p in args])
    print(' record at k+1 == model (all nine fields):')
    for key, (a, b) in tally.items():
        print(f'  {key:30s} {a}/{b}')
    print(' ship (pos untouched; vel and fuel at k+1 == flight + pulls + drains):')
    for key, (a, b) in sorted(ships.items()):
        print(f'  {key:40s} {a}/{b}')
    print(' exercised:', dict(EXER)); print(' skipped:', dict(skipped))
    for x in bad[:8]: print(' miss', x)


if __name__ == '__main__':
    main()
