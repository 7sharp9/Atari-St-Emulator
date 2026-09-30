"""The Amazon boss on real input with no pokes, dodging the damage-7 shot (type 140, handler `$016184`).

    uv run python reversing/impossamole/py/boss/boss_unpoked.py <boss-room snap> [--delay N] [--out name] [--record file.repl]

`boss_fight.py`'s `Fight` (swipe geometry, jump-and-fire `air_phase`, walking to the hitting x) plus two rules, and nothing poked:
  * a grounded hero with a type-140 shot in flight within 80 px of its spawn point (boss x + 7) walks away from that point until the shot is
    gone (`retreat`): left at the boss's right position (x 224), right at its left position (x 64);
  * with the boss at its left position the hero waits on the platform (x >= 176), out of reach of the shot's leftward sweep (`to_platform`).
Walks are cut short (`key`) the moment a 140 appears. Start snapshot: `agents/unpoked/hop4s/none/shop/seg5_pit_exit.snap` (hop 4 with the worm can
bought: health 16, weapon 3, coins 25); `--delay N` idles N steps first and varies the boss's random phase. `--record` writes the state-changing
commands as a replayable `.repl`. Result (12 delays 0..1,100,000): 1 kill (900,000: 20 hits, boss hit points 0, `$22803 = $ff`, health 10), the rest
died with the boss at 3 to 60 hit points; the same run from health 9 (no shop) never killed.

Why a retreat works (measured from `$016184` and a live probe, `shot140_probe.py`): the shot spawns at the boss's mouth (x 231 when the boss is at
224, y 121), picks a horizontal speed of 1 or 2 px per frame at random (`$016192`) and flies toward the hero's side, rises to y 109 in 8 frames and
then falls (1, 1, 1, 1, 2, 2, 2, 3, 3, 4 px per frame) to y 164 on frame 27. With speed 2 it is at x 187 when it crosses the hero's row (frame 22),
so a hero standing anywhere from x 172 to 200 is hit for 7; a hero 80 px or more from the spawn point is not.
"""
import argparse, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boss_fight as bf
from boss_fight import Fight, FRAME, STEP_X, ROOM_X, slot, w, sw, OUT
from repl import Repl

SHOT140 = 0x16184


class DodgeFight(Fight):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.retreats = 0
        self.log140 = []

    def shots140(self, hx=None):
        """Live 140 shots; with `hx`, only those that can reach a hero standing there: the shot spawns at the boss's mouth (boss x + 7) and
        sweeps at most 54 px toward the hero's side, so a hero 80 px or more from that point is out of reach."""
        out = []
        for n in range(8, 16):
            b = slot(self.r, n)
            if w(b, 0) and int.from_bytes(b[86:90], 'big') == SHOT140 and b[101] == 0 and b[103] != 254 and sw(b, 4) < 165:
                out.append((n, sw(b, 2), sw(b, 4)))
        if hx is not None:
            bx = sw(slot(self.r, 7), 2)
            out = [o for o in out if abs(hx - (bx + 7)) < 80]
        return out

    def key(self, bits, n):
        """As `Fight.key`, but a long grounded walk is cut short (packet stays latched) as soon as a 140 is in flight, so the loop can retreat."""
        if n <= 2 * FRAME:
            return super().key(bits, n)
        self.r.run('kbd ff', f'kbd {bits:02x}')
        done = 0
        while done < n:
            self.s(6000); done += 6000
            m = self.r.mem(0x227f3, 1)[0]
            if m in (0, 1) and self.shots140(self.r_hx()):
                break

    def r_hx(self):
        return sw(self.r.mem(0x1a572, 8), 2)

    def to_platform(self, s):
        """Boss at the left position: its shot sweeps x <= 125, so the hero waits on the platform (x >= 176), out of reach and out of its way."""
        if s['hx'] < 150:
            self.key(0x08, max(6000, min((150 - s['hx']) // 2, 60) * FRAME)); self.key(0, 1)
        elif s['hx'] <= STEP_X:
            self.jumps += 1
            self.key(0x09, FRAME + 6000); self.key(0x08, 3 * FRAME); self.key(0, FRAME // 2)
        else:
            self.s(FRAME // 4)

    def retreat(self, s):
        """Grounded with a 140 in flight: walk out of the shot's sweep (away from its spawn point), wait for it to end."""
        self.retreats += 1
        sh = self.shots140(s['hx'])
        self.log140.append((self.steps, s['hx'], sh))
        t0 = self.steps
        sx0 = s['bx'] + 7
        goleft = s['hx'] <= sx0 or sx0 > 150       # away from the shot's spawn point: left of it at the right boss position
        while self.steps - t0 < 40 * FRAME:
            st = self.state()
            if st['health'] == 0 or st['btype'] == 0:
                return
            if not self.shots140(st['hx']):
                break
            if st['st'] in (0, 1):
                if goleft and st['hx'] > sx0 - 80:
                    self.key(0x04, 6000)
                elif not goleft and st['hx'] < sx0 + 80:
                    self.key(0x08, 6000)
                else:
                    self.key(0, 6000)
            else:
                self.s(6000)
        self.key(0, 6000)

    def run(self, max_iter, log):
        for it in range(max_iter):
            s = self.state()
            if s['flag'] == 0xff or s['hp'] == 0 or s['btype'] == 0:
                log(f'it {it}: boss dead hp={s["hp"]} $22803={s["flag"]:02x} anim={s["banim"]:x}')
                return s
            if s['health'] == 0 or s['hp'] > 60:
                log(f'it {it}: hero dead (health {s["health"]})')
                return s
            grounded = s['st'] in (0, 1)
            if grounded and self.shots140(s['hx']):
                self.retreat(s)
                continue
            if grounded and s['bx'] < 150:
                self.to_platform(s)
                continue
            xmax = STEP_X if s['hx'] <= STEP_X else ROOM_X
            tx = self.target_x(s, xmax)
            if it % 50 == 0:
                log(f'it {it} step {self.steps}: hero x={s["hx"]} y={s["hy"]} st={s["st"]} face={s["face"]} health={s["health"]} '
                    f'boss x={s["bx"]} y={s["by"]} anim={s["banim"]:x} hp={s["hp"]} tx={tx} hits={self.watch_hits()} '
                    f'pulses={self.pulses} jumps={self.jumps} retreats={self.retreats}')
            open_ = s['banim'] != 0x221f6
            if not grounded:
                self.s(FRAME // 4); continue
            if tx is not None:
                near = abs(s['hx'] - tx) <= 4
                if not (near and s['face'] == 1):
                    if s['hx'] > tx + 4 or (near and s['face'] == 0):
                        if s['hx'] > tx + 4:
                            self.key(0x04, max(6000, min((s['hx'] - tx + 8) // 2, 40) * FRAME))
                        self.key(0x08, FRAME // 2)
                    else:
                        self.key(0x08, max(6000, min((tx - s['hx']) // 2 - 1, 40) * FRAME))
                    self.key(0, 1)
                elif open_ and s['fd'] == 0:
                    self.air_phase(False)
                else:
                    self.s(FRAME // 4)
            else:
                if s['hx'] < 150:
                    self.key(0x08, max(6000, min((150 - s['hx']) // 2, 40) * FRAME)); self.key(0, 1)
                elif s['hx'] <= STEP_X and s['face'] == 1 and open_ and s['fd'] == 0:
                    self.air_phase(True)
                elif s['hx'] > STEP_X:
                    self.key(0x04, FRAME); self.key(0, 1)
                else:
                    self.s(FRAME // 4)
        return self.state()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('snap')
    ap.add_argument('--max-iter', type=int, default=3000)
    ap.add_argument('--delay', type=int, default=0)
    ap.add_argument('--chain', action='store_true')
    ap.add_argument('--out', default='unpoked')
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
    f = DodgeFight(a.snap, 0, False, False)
    if a.delay:
        f.s(a.delay)
    s = f.run(a.max_iter, lambda m: print(m, flush=True))
    print(f'RESULT hp={s["hp"]} $22803={s["flag"]:02x} jumps={f.jumps} pulses={f.pulses} swipes={f.swipes} hits={f.watch_hits()} '
          f'retreats={f.retreats} steps={f.steps} health={s["health"]} min_health={f.min_health} wall={time.time()-t0:.0f}s')
    for d in f.damage_log:
        print('damage', d)
    if a.chain and s['flag'] == 0xff:
        print('chain hits over 8M steps:', *f.r.run('hits 8000000 b0b2 f0ee f050 fbcc'), sep='\n  ')
        print('$22803', f.r.mem(0x22803, 1).hex(), '$22804', f.r.mem(0x22804, 1).hex())
    endsnap = f'scratchpad/impossamole/agents/unpoked/boss/{a.out}_end.snap'
    f.r.run(f'snap {endsnap}')
    if a.record:
        with open(a.record, 'w') as fo:
            fo.write('\n'.join(rec) + f'\nsnap {os.path.join(bf.ROOT, endsnap)}\nq\n')
        print(len(rec), 'commands ->', a.record)
    f.r.close()


if __name__ == '__main__':
    main()
