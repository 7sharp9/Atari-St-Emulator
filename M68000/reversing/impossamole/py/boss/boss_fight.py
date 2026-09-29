"""Kill the Amazon boss with real joystick packets only (agents/boss, 104th pass).

    uv run python reversing/impossamole/py/boss/boss_fight.py [snap] [--weapon N] [--poke-health]
        [--max-iter N] [--allow-contact] [--out name] [--chain]

Starts from `scratchpad/impossamole/pass99/boss_room.snap` (boss room 318..326, boss alive, 60 hp, weapon $bb72 = 2)
and plays the fight with `kbd` packets and nothing else: no projectile position is poked. The hero walks to a spot,
jumps (kbd 01, or kbd 09 for the hop over the step at x=172), and while airborne (state $227f3 = 2; the fire handler
`$d37c` accepts states < 3) pulses fire (kbd 80 held for more than one 24,000-step frame, then released) whenever
the model below says the swipe overlaps the boss. Optional labelled pokes: `--weapon N` writes $bb72, `--poke-health`
writes health $bb74 = 18 every iteration (without it the boss's shots, damage 1 and 7, usually kill the hero: report
the `health`/`died` fields).

Geometry (README "Boss", "Natural aim"): the shot is slot 16 ($1a9aa), a static swipe spawned at hero x/y + (dx, dy)
from the table at $d4be + 64*(weapon-1), plus the mirror word at $d57e + 2*(weapon-1) added to x when the hero faces
right ($227f4 != 0); its box is (w, h) = (12, 13)(A1) from the table, alive while $227fd counts 6 -> 0 (one count per
frame). `$b71a` is an AABB test on x+8(A), y+10(A) with widths 12(A), 13(A). `$13a9c` (called by the boss handler
`$15e9a` unless its animation is `$221f6`) subtracts 104(A1) = the weapon index from the boss hit points at `$13b20`.

Reports jumps, fire pulses, swipes (slot 16 live after a pulse), hits ($13b20 writes seen by `watch $1a645`) and steps.
With `--chain` (after the boss dies) it checks $22803 = $ff and counts hits of $b0b2 / $f0ee over 8M steps.
"""
import argparse, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from repl import Repl, slot, w, sw, ROOT, OUT

BOSS = 7
FRAME = 24000
STEP_X = 172          # measured: a walking hero stops at x=172 (8 px step up onto the platform at x >= ~176)
ROOM_X = 260          # measured: the hero walks to x=260 on the platform and stops
FIRE_Y = 130          # a rising hero is inside the swipe's y window for every weapon (README "Natural aim")


def overlap(e, p):
    """$b71a on boxes (x, y, w, h): e = enemy (A0), p = projectile (A1)."""
    for a in (0, 1):
        d = e[a] - p[a]
        if d >= 0:
            if not d < p[2 + a]:
                return False
        elif not -d < e[2 + a]:
            return False
    return True


class Fight:
    def __init__(self, snap, weapon, poke_health, allow_contact):
        self.r = Repl(snap)
        self.poke_health, self.allow_contact = poke_health, allow_contact
        self.steps = self.jumps = self.pulses = self.swipes = self.hops = 0
        self.min_health = 99
        self.last_health = None
        self.damage_log = []
        if weapon:
            cur = self.r.mem(0xbb72, 4)                   # `w` writes a longword: keep $bb73 (counter), $bb74/5 (health)
            self.r.run('w bb72 %02x%s' % (weapon, cur[1:].hex()))   # labelled poke: equipped weapon
        self.weapon = self.r.mem(0xbb72, 1)[0]
        t = self.r.mem(0xd4be + (self.weapon - 1) * 64, 8)
        self.p_dx, self.p_dy, self.p_w, self.p_h = sw(t, 2), sw(t, 4), t[6], t[7]
        self.p_mir = sw(self.r.mem(0xd57e + (self.weapon - 1) * 2, 2), 0)
        self.bb73_start = self.r.mem(0xbb73, 1)[0]
        self.r.run('watch 1a645 1')

    def s(self, n, *cmds):
        self.r.run(*cmds, f's {n}')
        self.steps += n

    def key(self, bits, n):
        self.s(n, 'kbd ff', f'kbd {bits:02x}')

    def state(self):
        r = self.r
        h = r.mem(0x1a572, 108)
        b = slot(r, BOSS)
        m = r.mem(0x227f3, 12)
        hp = r.mem(0xbb74, 1)[0]
        self.min_health = min(self.min_health, hp)
        if self.last_health is not None and hp < self.last_health:
            objs = [(n, w(slot(r, n), 0), sw(slot(r, n), 2), sw(slot(r, n), 4), slot(r, n)[104]) for n in range(8, 16)
                    if w(slot(r, n), 0)]
            self.damage_log.append((self.steps, self.last_health - hp, sw(h, 2), sw(h, 4), m[0], objs))
        self.last_health = hp
        return dict(hx=sw(h, 2), hy=sw(h, 4), ho=(sw(h, 8), sw(h, 10), h[12], h[13]),
                    st=m[0], face=m[1], fd=m[10],
                    bx=sw(b, 2), by=sw(b, 4), banim=int.from_bytes(b[22:26], 'big'), hp=b[103], binv=b[102],
                    bbox=(sw(b, 2) + sw(b, 8), sw(b, 4) + sw(b, 10), b[12], b[13]), btype=w(b, 0),
                    flag=r.mem(0x22803, 1)[0], health=hp)

    def shot_box(self, hx, hy, face):
        return (hx + self.p_dx + (self.p_mir if face else 0), hy + self.p_dy, self.p_w, self.p_h)

    def hero_box(self, s, hx, hy):
        o = s['ho']
        return (hx + o[0], hy + o[1], o[2], o[3])

    def hits_ok(self, s, hx, hy, face=1):
        """Model: a swipe fired at (hx, hy) overlaps the boss, and (unless --allow-contact) the hero does not touch it."""
        if not overlap(s['bbox'], self.shot_box(hx, hy, face)):
            return False
        return self.allow_contact or not overlap(s['bbox'], self.hero_box(s, hx, hy))

    def target_x(self, s, xmax):
        ok = [hx for hx in range(8, xmax + 1, 2) if self.hits_ok(s, hx, FIRE_Y)]
        return ok[len(ok) // 2] if ok else None

    def watch_hits(self):
        return sum(1 for l in self.r.err if 'pc=$013b20' in l)

    def air_phase(self, hop):
        """Jump and fire while airborne. hop: up+right over the step at x=172 and keep drifting right."""
        self.jumps += 1
        self.hops += hop
        drift = 0x08 if hop else 0x00
        self.key(0x09 if hop else 0x01, FRAME + 6000)   # a jump key held under one frame (24,000 steps) is missed 7 times in 8
        self.key(drift, 3000)
        for i in range(80):
            t = self.state()
            if i > 2 and t['st'] in (0, 1):
                break
            open_ = t['banim'] != 0x221f6
            if t['st'] == 2 and t['fd'] == 0 and open_ and t['btype'] and self.hits_ok(t, t['hx'], t['hy'], t['face']):
                self.pulses += 1
                self.key(drift | 0x80, FRAME + 6000)
                if w(slot(self.r, 16), 0):
                    self.swipes += 1
                self.key(drift, 1)
            else:
                self.s(6000)
        self.key(0, FRAME // 2)

    def run(self, max_iter, log):
        for it in range(max_iter):
            if self.poke_health:
                self.r.run('w bb74 12120300')
            s = self.state()
            if s['flag'] == 0xff or s['hp'] == 0 or s['btype'] == 0:
                log(f'it {it}: boss dead hp={s["hp"]} $22803={s["flag"]:02x} anim={s["banim"]:x}')
                return s
            if s['health'] == 0 or s['hp'] > 60:
                log(f'it {it}: hero dead (health {s["health"]})')
                return s
            xmax = STEP_X if s['hx'] <= STEP_X else ROOM_X
            tx = self.target_x(s, xmax)
            if it % 50 == 0:
                log(f'it {it} step {self.steps}: hero x={s["hx"]} y={s["hy"]} st={s["st"]} face={s["face"]} health={s["health"]} '
                    f'boss x={s["bx"]} y={s["by"]} anim={s["banim"]:x} hp={s["hp"]} tx={tx} hits={self.watch_hits()} '
                    f'pulses={self.pulses} swipes={self.swipes} jumps={self.jumps}')
            grounded = s['st'] in (0, 1)
            open_ = s['banim'] != 0x221f6
            if not grounded:
                self.s(FRAME // 4); continue
            if tx is not None:
                near = abs(s['hx'] - tx) <= 4
                if not (near and s['face'] == 1):
                    if s['hx'] > tx + 4 or (near and s['face'] == 0):
                        # go left of the target, then right, so the hero ends facing right ($227f4 = 1)
                        self.key(0x04, max(6000, min((s['hx'] - tx + 8) // 2, 40) * FRAME)) if s['hx'] > tx + 4 else None
                        self.key(0x08, FRAME // 2)
                    else:
                        self.key(0x08, max(6000, min((tx - s['hx']) // 2 - 1, 40) * FRAME))
                    self.key(0, 1)
                elif open_ and s['fd'] == 0:
                    self.air_phase(False)
                else:
                    self.s(FRAME // 4)
            else:
                # no ground spot reaches the boss (boss x too far right): hop over the step from x in [150, 172]
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
    ap.add_argument('snap', nargs='?', default='scratchpad/impossamole/pass99/boss_room.snap')
    ap.add_argument('--weapon', type=int, default=0)
    ap.add_argument('--max-iter', type=int, default=3000)
    ap.add_argument('--poke-health', action='store_true')
    ap.add_argument('--allow-contact', action='store_true')
    ap.add_argument('--chain', action='store_true')
    ap.add_argument('--delay', type=int, default=0, help='idle steps before the first action (varies the boss RNG phase)')
    ap.add_argument('--out', default='fight')
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    f = Fight(a.snap, a.weapon, a.poke_health, a.allow_contact)
    print(f'weapon $bb72={f.weapon} shot dx={f.p_dx} dy={f.p_dy} w={f.p_w} h={f.p_h} mirror dx={f.p_mir}')
    if a.delay:
        f.s(a.delay)
    s = f.run(a.max_iter, lambda m: print(m, flush=True))
    print('watch lines (first 3, total):', *f.r.err[:3], len(f.r.err), sep='\n  ')
    print(f'RESULT hp={s["hp"]} $22803={s["flag"]:02x} jumps={f.jumps} (hops {f.hops}) pulses={f.pulses} swipes={f.swipes} '
          f'hits={f.watch_hits()} steps={f.steps} health={s["health"]} min_health={f.min_health} '
          f'$bb73 {f.bb73_start}->{f.r.mem(0xbb73, 1)[0]} wall={time.time()-t0:.0f}s')
    for d in f.damage_log:
        print('damage', d)
    if a.chain and s['flag'] == 0xff:
        f.r.run('w bb74 12120300')
        print('chain hits over 8M steps:', *f.r.run('hits 8000000 b0b2 f0ee f050 fbcc'), sep='\n  ')
        print('$22803', f.r.mem(0x22803, 1).hex(), '$22804', f.r.mem(0x22804, 1).hex())
    f.r.run(f'snap scratchpad/impossamole/agents/boss/{a.out}_end.snap')
    f.r.close()


if __name__ == '__main__':
    main()
