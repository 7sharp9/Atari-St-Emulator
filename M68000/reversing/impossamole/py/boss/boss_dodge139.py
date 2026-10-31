"""The Amazon boss with no pokes: `boss_unpoked.py`'s `DodgeFight` plus a jump over the aimed type-139 shot (handler `$014790`).

    uv run python reversing/impossamole/py/boss/boss_dodge139.py <boss-room snap> [--delay N] [--out name] [--record f.repl]
        [--reach PX] [--t-lo F] [--t-hi F] [--no-dodge] [--left-fight] [--max-iter N]

Best setting: `--reach 100 --t-lo 4 --t-hi 10 --max-iter 12000` from `agents/unpoked/hop4s/none/shop/seg5_pit_exit.snap` (health 16): 13 kills in 24 start
delays (0..1,100,000 and 50,000..1,150,000 in steps of 100,000), against 3 of 24 for `--no-dodge` at reach 80 (= `boss_unpoked.py`, which it reproduces
run for run). Reach 100 alone gives 2 of 12, the dodge alone at reach 80 0 of 12, reach 110 6 of 24, window 3-10 11 of 24. `--left-fight` (fight the boss at
x 64 from its right) loses: a hero walking left stops at x 118, 2 px short of a left swipe reaching the boss, and the up+left hop's latched push lands it at
x 84, inside the boss's contact box, where it takes repeated contact hits (4 of 12 on the first delay set, against 9 without it). `--delay 700000 --record` gives a kill with health 6 that replays byte-identically (5141 commands).

The 140 lob reaches farther than `boss_unpoked.py`'s 80 px where the floor left of the platform step is 8 px lower (7-point hits at hero x 152-154 while
retreating), hence `--reach 100`.

The 139 (12x12, damage 1) flies in a straight line toward where the hero stood when it spawned. Each time the loop reads a grounded hero it
predicts every live 139 forward from its last two positions (one read per 6,000 steps, a quarter frame) and finds the first frame at which its
box overlaps the hero's box `(x + 8, y, 16, 24)` if the hero stays put. When that frame is between `--t-lo` and `--t-hi` frames away, the hero
jumps straight up (`kbd 01` held one frame plus a quarter, then released): the apex is 40 px, so the shot passes under it. A walk is cut short
as soon as such a shot is due (`key`), the same way the 140 retreat cuts it.
"""
import argparse, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boss_fight as bf
import boss_unpoked as bu
from boss_fight import FRAME, slot, w, sw, OUT
from repl import Repl

SHOT139 = 0x14790
QF = FRAME // 4          # the loop's read interval when it only waits
LEFT_STEP_X = 118        # measured: a hero walking left from the platform stops at x 118 (a step), 2 px short of a left swipe reaching the boss at x 64


def overlap(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


class Dodge139Fight(bu.DodgeFight):
    def __init__(self, *a, t_lo=3, t_hi=8, dodge=True, left_fight=False, **kw):
        super().__init__(*a, **kw)
        self.t_lo, self.t_hi, self.dodge, self.left_fight = t_lo, t_hi, dodge, left_fight
        self.left_jumps = 0
        self.prev139 = {}        # slot -> (steps, x, y)
        self.dodges = 0
        self.log139 = []

    def shots139(self):
        """Live 139s as (slot, x, y, vx, vy) with the velocity in px per frame from the previous read of that slot (None until two reads)."""
        out, seen = [], set()
        for n in range(8, 16):
            b = slot(self.r, n)
            if w(b, 0) and int.from_bytes(b[86:90], 'big') == SHOT139 and b[101] == 0 and b[103] != 254:
                x, y = sw(b, 2), sw(b, 4)
                seen.add(n)
                p = self.prev139.get(n)
                v = None
                if p and self.steps > p[0] and (x, y) != (p[1], p[2]):
                    k = (self.steps - p[0]) / FRAME
                    v = ((x - p[1]) / k, (y - p[2]) / k)
                    self.prev139[n] = (self.steps, x, y, v)
                elif p and len(p) > 3:
                    v = p[3]
                else:
                    self.prev139[n] = (self.steps, x, y)
                out.append((n, x, y) + (v or (None, None)))
        for n in list(self.prev139):
            if n not in seen:
                del self.prev139[n]
        return out

    def due139(self, hx, hy):
        """Frames until the first live 139 overlaps a hero standing at (hx, hy), or None (no shot on course within 30 frames)."""
        hero = (hx + 8, hy, 16, 24)
        best = None
        for n, x, y, vx, vy in self.shots139():
            if vx is None:
                continue
            for t in range(0, 31):
                if overlap(hero, (x + vx * t, y + vy * t, 12, 12)):
                    best = t if best is None else min(best, t)
                    break
        return best

    def key(self, bits, n):
        if n <= 2 * FRAME:
            return super().key(bits, n)
        self.r.run('kbd ff', f'kbd {bits:02x}')
        done = 0
        while done < n:
            self.s(6000); done += 6000
            m = self.r.mem(0x227f3, 1)[0]
            if m in (0, 1):
                hx = self.r_hx()
                if self.shots140(hx):
                    break
                if self.dodge:
                    hy = sw(self.r.mem(0x1a572, 8), 4)
                    t = self.due139(hx, hy)
                    if t is not None and t <= self.t_hi:
                        break

    def to_platform(self, s):
        """Boss at its left position (x 64). With `left_fight`, stand right of it facing left at the middle x whose swipe (facing left, no mirror word)
        overlaps the boss box without the hero touching it, and jump and fire while it is open; otherwise wait on the platform as before."""
        if not self.left_fight:
            return super().to_platform(s)
        ok = [hx for hx in range(80, 150, 2) if self.hits_ok(s, hx, bf.FIRE_Y, 0)]
        if not ok:
            return super().to_platform(s)
        open_ = s['banim'] != 0x221f6
        if s['hx'] > LEFT_STEP_X + 4:
            self.key(0x04, max(6000, min((s['hx'] - LEFT_STEP_X) // 2, 40) * FRAME)); self.key(0, 1)
        elif open_ and s['fd'] == 0:
            self.left_jumps += 1
            self.air_phase_left()
        else:
            self.s(QF)

    def air_phase_left(self):
        """Hop up+left off the x-118 step toward the boss and fire whenever the left-facing swipe overlaps it (as `air_phase(True)`, mirrored)."""
        self.jumps += 1
        self.key(0x05, FRAME + 6000)
        self.key(0x04, 3000)
        for i in range(80):
            t = self.state()
            if i > 2 and t['st'] in (0, 1):
                break
            open_ = t['banim'] != 0x221f6
            if t['st'] == 2 and t['fd'] == 0 and open_ and t['btype'] and t['bx'] < 150 and self.hits_ok(t, t['hx'], t['hy'], t['face']):
                self.pulses += 1
                self.key(0x84, FRAME + 6000)
                if w(slot(self.r, 16), 0):
                    self.swipes += 1
                self.key(0x04, 1)
            else:
                self.s(6000)
        self.key(0, FRAME // 2)

    def jump139(self, s, t):
        self.dodges += 1
        self.log139.append((self.steps, s['hx'], s['hy'], t))
        self.jumps += 1
        bf.Fight.key(self, 0x01, FRAME + 6000)
        bf.Fight.key(self, 0x00, 3000)
        for i in range(80):          # wait for the landing (or the next decision if the loop needs it airborne)
            st = self.state()
            if i > 2 and st['st'] in (0, 1):
                break
            self.s(6000)

    def run(self, max_iter, log):
        orig_state = self.state

        def state():
            s = orig_state()
            if self.dodge and s['st'] in (0, 1) and s['health'] and s['btype']:
                t = self.due139(s['hx'], s['hy'])
                if t is not None and self.t_lo <= t <= self.t_hi:
                    self.jump139(s, t)
                    s = orig_state()
                elif t is not None and t < self.t_lo:
                    self.log139.append((self.steps, s['hx'], s['hy'], t, 'late'))
            return s
        self.state = state
        try:
            return super().run(max_iter, log)
        finally:
            self.state = orig_state


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('snap')
    ap.add_argument('--max-iter', type=int, default=3000)
    ap.add_argument('--delay', type=int, default=0)
    ap.add_argument('--out', default='dodge139')
    ap.add_argument('--t-lo', type=float, default=3)
    ap.add_argument('--t-hi', type=float, default=8)
    ap.add_argument('--no-dodge', action='store_true')
    ap.add_argument('--left-fight', action='store_true', help='fight the boss at x 64 from its right, facing left, instead of waiting on the platform')
    ap.add_argument('--reach', type=int, default=80, help="boss_unpoked.REACH: retreat from a 140 while closer than this to its spawn point")
    ap.add_argument('--record', help='write the state-changing commands (kbd, s, w) as a replayable .repl, ending in a snap and q')
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    rec = []
    if a.record:
        orig = Repl.run

        def run(self, *cmds):
            rec.extend(c for c in cmds if c.startswith(('kbd', 's ', 'w ')))
            return orig(self, *cmds)
        Repl.run = run
    bu.REACH = a.reach
    f = Dodge139Fight(a.snap, 0, False, False, t_lo=a.t_lo, t_hi=a.t_hi, dodge=not a.no_dodge, left_fight=a.left_fight)
    if a.delay:
        f.s(a.delay)
    s = f.run(a.max_iter, lambda m: print(m, flush=True))
    print(f'RESULT hp={s["hp"]} $22803={s["flag"]:02x} jumps={f.jumps} pulses={f.pulses} swipes={f.swipes} hits={f.watch_hits()} '
          f'retreats={f.retreats} dodges={f.dodges} left_jumps={f.left_jumps} steps={f.steps} health={s["health"]} min_health={f.min_health} wall={time.time()-t0:.0f}s')
    for d in f.damage_log:
        print('damage', d)
    for d in f.log139:
        print('dodge139', d)
    endsnap = f'scratchpad/impossamole/pass108/boss/{a.out}_end.snap'
    f.r.run(f'snap {endsnap}')
    if a.record:
        with open(a.record, 'w') as fo:
            fo.write('\n'.join(rec) + f'\nsnap {os.path.join(bf.ROOT, endsnap)}\nq\n')
        print(len(rec), 'commands ->', a.record)
    f.r.close()


if __name__ == '__main__':
    main()
