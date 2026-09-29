"""Hop 3 without health pokes: `route_hop3.py`'s eleven segments driven by a `Driver` that fights or dodges what comes at it.

    uv run python reversing/impossamole/py/route/natural_hop3.py [seg ...] [--from <seg>]

`NatDriver` changes two things relative to `route_driver.Driver`:
  * `poke_health` and the refill-at-4 rule do nothing (the run is unpoked; every call is logged as a skipped poke);
  * after each state read the guard reacts to hostile kind-2 objects ahead of the hero (0 < dx <= HOP_DX, |dy| <= 20): a killable one (hp 1..127) within SWIPE_DX gets one fire pulse (the fire bit is edge-detected once per game poll, so the pulse is held longer than the 24,000-step gameplay frame), an immune one (hp >= 128) gets a hop over it.
Everything else (segments, waypoints) is `route_hop3.py`'s. Output goes to `agents/natural/hop3/` (snapshots, `.repl`, `.log`).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import route_driver
import route_hop3
from route_driver import *

BASE = 'scratchpad/impossamole/agents/natural/hop3'
SWIPE_DX = 50      # swipe when a killable enemy is this close ahead (weapon 3 reaches about 20 + 32 px)
HOP_DX = 44        # hop over an immune enemy this close ahead
PULSE = 30_000


class NatDriver(Driver):
    def __init__(self, *a, **kw):
        kw['hp_floor'] = -1
        self.pulses = 0
        self.hops = 0
        self.hops_enabled = True
        self.busy_guard = False
        self.last_pulse = -10**9
        super().__init__(*a, **kw)

    def poke_health(self, label='health full'):
        self.log(ev='skipped_poke', label=label, steps=self.total_steps, hp=self.last.hp if self.last else None)

    def threats(self, s):
        """Live hostile objects (kind 2, damage byte > 0) as (object, killable): killable is hp 1..127; hp >= 128 is immune
        (README "Spawn types"), hp 254 is a dying object. Crocodiles (`$015d26`, damage 0) are platforms and skipped."""
        out = []
        for o in self.objects():
            r = o['raw']
            hp, dmg = r[103], r[104]
            if o['type'] == 2 and dmg > 0 and hp != 254 and hp != 0:
                out.append((o, hp < 128))
        return out

    def note_hurt(self, prev, s, why):
        near = [dict(slot=o['slot'], type=o['type'], dx=o['dx'], dy=o['dy'], hp=o['raw'][103],
                     handler=hex(int.from_bytes(o['raw'][86:90], 'big')), anim=o['raw'][22:26].hex())
                for o in self.near(40) if o['slot'] != 6]
        self.hurts.append(dict(t=self.total_steps, wx=s.wx, y=s.y, hp=(prev.hp, s.hp), near=near))
        self.log(ev='hurt', t=self.total_steps, wx=s.wx, y=s.y, hp0=prev.hp, hp1=s.hp, st=s.st, why=why, near=near, sens=s.sens.hex())

    def read_stable(self):
        s = super().read_stable()
        if self.busy_guard or s.hp <= 0 or s.st not in (0, 1):
            return s
        self.busy_guard = True
        try:
            ahead = [(o, k) for o, k in self.threats(s) if abs(o['dy']) <= 20 and 0 < o['dx'] <= HOP_DX]
            kill = [o for o, k in ahead if k and o['dx'] <= SWIPE_DX]
            hop = [o for o, k in ahead if not k]
            if kill and self.total_steps - self.last_pulse > 150_000:
                self.pulses += 1
                self.last_pulse = self.total_steps
                keep = self.cur_bits
                self.log(ev='pulse', t=self.total_steps, tgt=[(o['slot'], o['dx'], o['dy']) for o in kill], hero=(s.x, s.y))
                self.set_bits(keep | FIRE)
                self.step(PULSE)
                self.set_bits(keep)
                s = super().read_stable()
            elif hop and self.hops_enabled:
                self.hops += 1
                self.log(ev='dodge_hop', t=self.total_steps, tgt=[(o['slot'], o['dx'], o['dy']) for o in hop], hero=(s.x, s.y))
                keep = self.cur_bits
                self.hop(RIGHT, why='dodge')
                self.set_bits(keep)
                s = self.last = super().read_stable()
        finally:
            self.busy_guard = False
        return s


def run(names):
    route_hop3.Driver = NatDriver
    route_hop3.BASE = BASE
    prev = route_hop3.START
    for f in route_hop3.SEGS:
        n = f.__name__
        endsnap = f'{BASE}/snaps/{n}.snap'
        if names and n not in names:
            if os.path.exists(os.path.join(ROOT, endsnap)):
                prev = endsnap
            continue
        print(f'== {n}: from {prev}', flush=True)
        d = NatDriver(prev, f'{BASE}/segs/{n}', tick=8000, checkpoint_every=250, ckpt_dir=f'{BASE}/ckpt/{n}')
        hp0 = d.last.hp
        f(d)
        d.finish(endsnap)
        print(f'== {n}: done, {d.total_steps} steps, hp {hp0} -> {d.last.hp}, hurts={len(d.hurts)}, pulses={d.pulses}, hops={d.hops}', flush=True)
        if d.last.hp <= 0:
            print('   hero dead, stopping'); break
        prev = endsnap


if __name__ == '__main__':
    run([a for a in sys.argv[1:] if not a.startswith('--')])
