"""Why the Virus demo pilot loses each life: one chain game run to its game over under its own stserver process.

    uv run python reversing/virus/py/deaths/death_census.py <game number> [out dir]

Loads scratchpad/virus/chain/long100/starts/main_gNNN.snap (unpoked), sets breakpoints on
  the four writers of $62a5d (ShipHitFlag): $20360 EnemyShot, $2083c Bomb_Fall, $21654 Pool_CommonTail, $225e6 Attractor_FuelDrain
  the crash entries $25ad2 (ground/object) and $25ad8 (death exit, also the flag path), the ground-branch instructions
  $25862 $25874 $25c3e $25c46 $25c4e (whichever precedes $25ad2 by a few steps is the branch taken),
  the life decrement $25ba0 and the game over $25bc0,
and non-stopping write watches (writer PC, step, value) on fuel $32a2e, the tick counter $32a44 and the flags $62a5d..e.
Stops within DEDUPE steps of the previous stop at the same PC are the interrupt re-stop (DEVELOPING.md) and are ignored.
Nothing is poked.  Writes <out dir>/g<NNN>.json (default $VIRUS_WORK/deaths/fresh, VIRUS_WORK defaulting to scratchpad/virus).
"""
import json, os, struct, sys, time

here = os.path.dirname(os.path.abspath(__file__))
ROOT = here
while not os.path.exists(os.path.join(ROOT, 'tools', 'rdis.py')):
    p = os.path.dirname(ROOT)
    if p == ROOT: raise SystemExit('repo root not found')
    ROOT = p
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from stclient import StServer

STARTS = os.path.join(ROOT, 'scratchpad', 'virus', 'chain', 'long100', 'starts')
DEDUPE = 2000
SETTERS = {0x20360: 'EnemyShot_borrow', 0x2083c: 'Bomb_borrow', 0x21654: 'Contact_CommonTail', 0x225e6: 'Attractor_empty'}
GROUND = {0x25862: 'object_cell', 0x25874: 'ground_fast', 0x25c3e: 'pad_fast', 0x25c46: 'pad_off_x', 0x25c4e: 'pad_off_z'}
BPS = [0x25ad2, 0x25ad8, 0x25ba0, 0x25bc0] + list(SETTERS) + list(GROUND)
FUEL_PC = {0x2569c: 'thrust', 0x25692: 'thrust', 0x2573e: 'fire', 0x25734: 'fire', 0x2036a: 'shot', 0x20846: 'bomb',
           0x225d6: 'attractor', 0x225e0: 'attractor',
           0x2311a: 'life_start', 0x23118: 'life_start', 0x23266: 'wave_start', 0x25aae: 'pad_refuel', 0x25af6: 'crash_zero'}
KIND = {0x21776: 'Seeder_Wait', 0x21792: 'Seeder_Fly', 0x21894: 'Seeder_Descend', 0x21976: 'Seeder_Landed', 0x219de: 'Seeder_TakeOff',
        0x21ae2: 'Chaser_Wait', 0x21afe: 'Chaser', 0x21c42: 'Patrol_Wait', 0x21c64: 'Patrol_Cruise', 0x21d08: 'Patrol_HomeOnQueue',
        0x21df6: 'Patrol_AttackShip', 0x21f00: 'Pursuer', 0x2200c: 'Pursuer2_Wait', 0x2202c: 'Pursuer2', 0x221ac: 'Pursuer2_Damaged',
        0x222dc: 'Bomber_Wait', 0x22316: 'Bomber', 0x22486: 'Attractor_Wait', 0x224a6: 'Attractor', 0x22688: 'Mothership_Wait',
        0x226ac: 'Mothership', 0x2279a: 'Mothership_Chaser', 0x228de: 'Rocket'}
OBJ = {0x20310: 'EnemyShot', 0x207d6: 'Bomb_Fall', 0x1feb0: 'PlayerShot'}


def hx(v): return int(str(v).lstrip('$'), 16)
def s16(v): return v - 0x10000 if v & 0x8000 else v


class G:
    def __init__(self, snap):
        self.s = StServer(ROOT)
        self.s('load', snapshot=snap)
        self.w = {n: self.s('watch_add', lo=lo, hi=hi, kind='w', max_events=8000000)['id']
                  for n, (lo, hi) in dict(fuel=(0x32a2e, 0x32a2f), tick=(0x32a44, 0x32a45), flag=(0x62a5d, 0x62a5e)).items()}
        self.ev = {n: [] for n in self.w}

    def u16(self, a): return int.from_bytes(self.s.read(a, 2), 'big')

    def drain(self):
        for n, i in self.w.items():
            r = self.s('watch_events', id=i, clear=True)
            r = r[0] if isinstance(r, list) else r
            if r.get('dropped'): print('DROPPED', n, r['dropped'], file=sys.stderr)
            for e in r['events']:
                self.ev[n].append((e['step'], hx(e['pc']), hx(e['value'])))

    def state(self):
        s = self.s
        ship = struct.unpack('>6h', s.read(0x270b0, 12))
        n = self.u16(0x32a3e)
        pool = s.read(0x31d54, 20 * n)
        acts = []
        for k in range(n):
            x, y, z, vx, vy, vz, life, pad = struct.unpack('>8h', pool[k*20:k*20+16]); beh = struct.unpack('>I', pool[k*20+16:k*20+20])[0]
            d = abs(s16(x & 0xffff) - ship[0]) + abs(y - ship[1]) + abs(z - ship[2])
            acts.append((d, KIND.get(beh, f'${beh:x}'), x, y, z, 'waiting' if y == -0xf00 else ''))
        acts.sort()
        no = self.u16(0x32a3c)
        ob = s.read(0x302f6, 18 * no)
        objs = []
        for k in range(no):
            x, y, z = struct.unpack('>3h', ob[k*18:k*18+6]); h = struct.unpack('>I', ob[k*18+14:k*18+18])[0]
            if h in OBJ and h != 0x1feb0:
                objs.append((abs(x - ship[0]) + abs(y - ship[1]) + abs(z - ship[2]), OBJ[h]))
        objs.sort()
        return dict(ship=ship, fuel=self.u16(0x32a2e), lives=self.u16(0x32a54), wave=self.u16(0x32a50), tick=self.u16(0x32a44),
                    flag5d=s.read(0x62a5d, 1)[0], flag62=s.read(0x62a62, 1)[0], nearest_actor=acts[:3], nearest_obj=objs[:3], n_actors=n)


def attribute(fuel_ev, lo, hi, init):
    """fuel drained and gained by writer class between steps lo and hi (events (step, pc, value)); init = the value before the first event"""
    prev = init; out = {}; hits = {'shot': 0, 'bomb': 0}
    for st, pc, v in fuel_ev:
        if st < lo: prev = v; continue
        if st > hi: break
        cls = FUEL_PC.get(pc, 'other')
        d = v - prev
        out[cls] = out.get(cls, 0) + d
        if cls in hits: hits[cls] += 1
        prev = v
    return out, hits


def approach(g, cps, dstep, dpc):
    """Replay the last chunk(s) from the older of the two checkpoints with per-tick stops: $255d4 (tick arrival: the pilot's D0..D2
    and the ship), $257f4 (ground height in D1).  Returns the per-tick list and whether the replay reached the same death
    stop at the same step (the determinism check); the machine is put back at the death stop."""
    s = g.s
    back = s('fork')['id']
    st0, cid = cps[0]
    s('restore', id=cid)
    s('bp_clear', addrs=BPS)
    s('bp_set', addrs=[0x255d4, 0x257f4, 0x25ad2, 0x25ad8, *SETTERS, *GROUND])
    ticks = []; lastp = {}; same = None; rb = None; sets = []
    while True:
        r = s('run', max_steps=20_000_000)
        if r['reason'] != 'breakpoint': same = ('reason', r['reason']); break
        regs = s('regs'); pc = hx(regs['pc']); step = regs['step'] if isinstance(regs['step'], int) else hx(regs['step'])
        if pc in lastp and step - lastp[pc] < DEDUPE: continue
        lastp[pc] = step
        if pc == 0x255d4:
            ship = struct.unpack('>6h', s.read(0x270b0, 12))
            ticks.append(dict(step=step, tick=g.u16(0x32a44), ship=ship, att=struct.unpack('>2h', s.read(0x32a32, 4)), fuel=g.u16(0x32a2e), d=[hx(regs['d0']) & 0xffff, hx(regs['d1']) & 0xffff, hx(regs['d2']) & 0xffff], gnd=None))
        elif pc == 0x257f4 and ticks:
            ticks[-1]['gnd'] = s16(hx(regs['d1']) & 0xffff)
        elif pc in GROUND:
            rb = (step, GROUND[pc])
        elif pc in SETTERS:
            sets.append((step, SETTERS[pc]))
        elif step < dstep - 100:
            continue
        else:
            same = (f'{pc:x}', step == dstep or abs(step - dstep) < 100); break
    s('restore', id=back); s('drop', id=back)
    s('bp_clear', addrs=[0x255d4, 0x257f4])
    s('bp_set', addrs=BPS)
    for n, i in g.w.items(): s('watch_events', id=i, clear=True)
    return dict(ticks=ticks[-120:], replay_end=same, from_step=st0, replay_branch=rb, replay_setters=sets[-3:])


def main():
    game = int(sys.argv[1]); outd = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.environ.get('VIRUS_WORK', os.path.join(ROOT, 'scratchpad', 'virus')), 'deaths', 'fresh')
    os.makedirs(outd, exist_ok=True)
    snap = os.path.join(STARTS, f'main_g{game:03d}.snap')
    g = G(snap); s = g.s
    s('bp_set', addrs=BPS)
    t0 = time.time(); step0 = s('regs')['step']
    last = {}                       # pc -> step of last accepted stop
    setters = []                    # setter stops since the last death
    ground_last = None              # (step, name) of the last ground-branch stop
    cur = None                      # death in progress
    deaths = []; prev_loss_step = step0; over = None
    budget = 1_500_000_000
    CH = 5_000_000
    cps = []                        # [(step, fork id)], the last two chunk boundaries
    while True:
        r = s('run', max_steps=CH)
        if r['reason'] == 'max_steps':
            budget -= CH
            if budget <= 0: print('budget out'); break
            cps.append((hx(s('regs')['step']) if isinstance(s('regs')['step'], str) else s('regs')['step'], s('fork')['id']))
            while len(cps) > 2: s('drop', id=cps.pop(0)[1])
            continue
        if r['reason'] != 'breakpoint': print('stop', r); break
        regs = s('regs'); pc = hx(regs['pc']); step = hx(regs['step']) if isinstance(regs['step'], str) else regs['step']
        if pc in last and step - last[pc] < DEDUPE: continue
        last[pc] = step
        if pc in SETTERS:
            setters.append(dict(writer=SETTERS[pc], step=step, tick=g.u16(0x32a44), fuel=g.u16(0x32a2e),
                                regs={k: regs[k] for k in regs if k[0] in 'da' and len(k) == 2},
                                stack=s.read(hx(regs['a7']), 32).hex()))
        elif pc in GROUND:
            ground_last = (step, GROUND[pc])
        elif pc in (0x25ad2, 0x25ad8):
            if cur is not None and step - cur['step'] < 100: continue    # 25ad2 falls into 25ad8
            st = g.state()
            if pc == 0x25ad2:
                via = ground_last[1] if ground_last and step - ground_last[0] < 60 else 'unknown'
                if st['flag62'] and via == 'unknown': via = 'model_below_ground'
                cause = 'ground:' + via
            else:
                cause = 'flag:' + (setters[0]['writer'] if setters else 'NO_SETTER_STOP')
            cur = dict(step=step, entry=f'{pc:x}', cause=cause, state=st, setters=setters, ground_branch_step=ground_last)
            setters = []
            g.drain()
            cur['approach'] = approach(g, cps, step, pc)
        elif pc == 0x25ba0:
            g.drain()
            ticks = g.ev['tick']
            # tick event values are the new counter value; find the step where the counter was tick-500
            d = cur or dict(cause='NO_DEATH_STOP', state=None, step=step)
            tk = d['state']['tick'] if d['state'] else None
            lo = prev_loss_step
            if tk is not None:
                for st_, _, v in ticks:
                    if v == max(tk - 500, 0) and st_ > prev_loss_step: lo = st_; break
            fe = g.ev['fuel']
            init = next((v for st_, _, v in fe if st_ <= lo), 0)
            init = max([(st_, v) for st_, _, v in fe if st_ <= lo], default=(0, 0))[1]
            a500, h500 = attribute(fe, lo, d['step'], init)
            a_life, h_life = attribute(fe, prev_loss_step, d['step'], 0)
            d.update(loss_step=step, lives_before=g.u16(0x32a54), a500=a500, hits500=h500, a_life=a_life, hits_life=h_life,
                     life_start_step=prev_loss_step, window_lo_step=lo, flag_events=[e for e in g.ev['flag'] if prev_loss_step < e[0] <= step])
            deaths.append(d); cur = None; prev_loss_step = step; setters = []
            g.ev = {n: [] for n in g.w}
            print(f'g{game} loss {len(deaths)}: tick {tk} wave {d["state"]["wave"] if d["state"] else None} {d["cause"]} fuel {d["state"]["fuel"] if d["state"] else None}', flush=True)
        elif pc == 0x25bc0:
            over = dict(step=step, tick=g.u16(0x32a44), wave=g.u16(0x32a50), score=int.from_bytes(s.read(0x2708e, 4), 'big')); break
    res = dict(game=game, step0=step0, end_step=s('regs')['step'], wall_s=round(time.time() - t0, 1), deaths=deaths, over=over)
    json.dump(res, open(os.path.join(outd, f'g{game:03d}.json'), 'w'), indent=1, default=str)
    s.close()
    print(f'g{game} done: {len(deaths)} losses, over={over}, {res["wall_s"]}s', flush=True)


if __name__ == '__main__':
    main()
