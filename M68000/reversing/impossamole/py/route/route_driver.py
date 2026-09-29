"""Event-driven driver for Impossamole: a live REPL wrapper that walks the hero with real joystick input.

Library (import it) plus a tiny CLI to replay a recorded .repl and compare snapshots.

    from route_driver import Driver
    d = Driver('scratchpad/impossamole/pass103/room188.snap', 'agents/hop3/seg_a')   # seg_a.repl / seg_a.log
    d.poke_health('segment start')                    # labelled poke, logged in the .repl and .log
    s = d.hold(RIGHT, until=lambda s: s.wx >= 6400, max_steps=600_000)
    d.finish('agents/hop3/snaps/seg_a_end.snap')

What it does per tick (default 6,000 steps, under half a frame... a frame is ~12-15k steps, the game's joystick
poll ~24k): reads the hero (x $1a574, y $1a576, busy $1a5d7), state byte $227f3 (0 idle, 2 jump, 3 fall, 4
ladder), camera $227b6, leftmost block $227b4, room limit $227b8 and health $bb74, appends a line to
`<name>.log`, and evaluates the caller's `until` predicate. A `kbd` packet is sent only when the wanted joystick
bits change (the pad byte is a raw level held by the IKBD state until the next packet), so a held direction is one
packet however many ticks it lasts.

Replay guarantee: `<name>.repl` contains exactly the state-changing commands (`w ...` pokes, `kbd ...`, `s ...`), in
order, plus a closing `snap`. Reads (`m`), the sentinel (`hits 0 fb98`) and the periodic checkpoint `snap`s are
side-effect-free and are not recorded. `python route_driver.py replay <snap> <name>.repl <out.snap>` re-runs it and
`cmp`s against the live snapshot.

World position: the game's tile lookup is tile_x = ((x - 32) + camera) >> 3 (README "$be96's tile classification"),
so `wx = x - 32 + camera` is the hero's left-edge map pixel and `block = (x + camera - 16) // 32` matches the exit
records. The hero is pinned at screen x=192 while the camera scrolls, so always use wx, never bare x.

Joystick bits: 01 up, 02 down, 04 left, 08 right, 80 fire (`kbd ff` then `kbd <bits>`).
"""
import json, os, subprocess, sys, time
from dataclasses import dataclass

ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))
DISK = 'scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st'
UP, DOWN, LEFT, RIGHT, FIRE = 0x01, 0x02, 0x04, 0x08, 0x80
NONE = 0
STATE_NAMES = {0: 'idle', 2: 'jump', 3: 'fall', 4: 'ladder'}
HEALTH_FULL = 'w bb74 12120300'   # health/max/.. longword used by the other drivers (boss_kill.py); labelled poke


def s16(v):
    return v - 65536 if v >= 32768 else v


@dataclass
class State:
    x: int; y: int; busy: int; st: int; cam: int; blk: int; lim: int; hp: int; hpmax: int
    sens: bytes = b''      # $227e0..$227eb sensor category bytes

    @property
    def wx(self):
        return self.x - 32 + self.cam

    @property
    def block(self):
        return (self.x + self.cam - 16) // 32

    def brief(self):
        return (f'x={self.x} y={self.y} wx={self.wx} cam={self.cam:#x} blk={self.blk} st={STATE_NAMES.get(self.st, self.st)}'
                f' busy={self.busy} hp={self.hp}/{self.hpmax}')


class Driver:
    def __init__(self, snap, name, disk=DISK, tick=6000, checkpoint_every=0, ckpt_dir=None, log_state=True, hp_floor=4):
        """snap: start snapshot (relative to ROOT). name: path prefix (no extension) for .repl / .log, relative to ROOT
        or absolute. checkpoint_every: write a checkpoint snapshot every N ticks into ckpt_dir (default `<name>_ck`)."""
        self.root = ROOT
        self.name = name if os.path.isabs(name) else os.path.join(ROOT, name)
        os.makedirs(os.path.dirname(self.name), exist_ok=True)
        self.tick = tick
        self.ckpt_every = checkpoint_every
        self.ckpt_dir = ckpt_dir or (self.name + '_ck')
        self.nticks = 0
        self.cur_bits = 0          # pad byte the game last received (assume 0 after a fresh resume)
        self.total_steps = 0
        self.script = []           # state-changing commands
        self.last = None
        self.reread_count = 0
        self.hurts = []
        self.hp_floor = hp_floor
        env = dict(os.environ, ATARI_NOTRACE='1')
        self.p = subprocess.Popen(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl',
                                   '--disk-a', disk], cwd=ROOT, env=env, text=True, bufsize=1,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.start_snap = snap
        self.logf = open(self.name + '.log', 'w')
        self._raw('s 1')      # bring the emulator up (the first command after resume)
        self.script.append('s 1'); self.total_steps += 1
        self.logf.write(json.dumps({'ev': 'start', 'snap': snap}) + '\n')
        self.last = self.read()

    # ---- raw REPL access ----
    def _raw(self, *cmds):
        for c in cmds:
            self.p.stdin.write(c + '\n')
        self.p.stdin.write('hits 0 fb98\n'); self.p.stdin.flush()
        out = []
        while True:
            l = self.p.stdout.readline()
            if not l:
                raise RuntimeError('repl closed')
            if l.startswith('  $00fb98'):
                return [x.rstrip() for x in out if not x.startswith(('enqueued', '---'))]
            out.append(l)

    def mem(self, addr, n):
        return bytes.fromhex(''.join(self._raw(f'm {addr:x} {n}')).replace(' ', ''))

    def _do(self, *cmds):
        """State-changing commands: recorded in the .repl."""
        self.script.extend(cmds)
        for c in cmds:
            if c.startswith('s '):
                self.total_steps += int(c.split()[1])
        return self._raw(*cmds)

    # ---- state ----
    def read(self):
        regs = [(0x1a572, 8), (0x1a5d7, 1), (0x227f3, 1), (0x227b4, 8), (0xbb74, 2), (0x227e0, 12)]
        lines = self._raw(*[f'm {a:x} {n}' for a, n in regs])
        h, busy, st, c, hp, sens = [bytes.fromhex(l.replace(' ', '')) for l in lines]
        busy, st = busy[0], st[0]
        x, y = int.from_bytes(h[2:4], 'big'), s16(int.from_bytes(h[4:6], 'big'))
        s = State(x, y, busy, st, int.from_bytes(c[2:4], 'big'), int.from_bytes(c[0:2], 'big'),
                  int.from_bytes(c[4:6], 'big'), hp[0], hp[1], sens)
        return s

    def read_stable(self):
        """Read the hero; if x/y jumped implausibly since the last tick (the sensor scan $c0d0..$c204 overwrites the
        hero's x/y with probe offsets transiently), step a few hundred instructions and read again."""
        s = self.read()
        p = self.last
        if p is not None and (abs(s.x - p.x) > 14 or abs(s.y - p.y) > 24) and s.blk == p.blk:
            self.reread_count += 1
            self.step(347)
            s2 = self.read()
            s = s2
        return s

    def objects(self):
        """All 20 object slots ($1a2ea, stride $6c): list of dicts (slot, type, x, y, dx, dy to hero, act flags)."""
        raw = bytes.fromhex(''.join(self._raw('m 1a2ea 2160')).replace(' ', ''))
        hx, hy = (self.last.x, self.last.y) if self.last else (0, 0)
        out = []
        for i in range(20):
            b = raw[i * 0x6c:(i + 1) * 0x6c]
            ty = int.from_bytes(b[0:2], 'big'); x = s16(int.from_bytes(b[2:4], 'big')); y = s16(int.from_bytes(b[4:6], 'big'))
            out.append(dict(slot=i, type=ty, x=x, y=y, dx=x - hx, dy=y - hy, raw=b))
        return out

    def near(self, r=48):
        return [o for o in self.objects() if o['type'] and abs(o['dx']) <= r and abs(o['dy']) <= r]

    # ---- actions ----
    def step(self, n):
        self._do(f's {n}')

    def set_bits(self, bits):
        if bits != self.cur_bits:
            self._do('kbd ff', f'kbd {bits:02x}')
            self.cur_bits = bits

    def poke(self, cmd, label):
        self.logf.write(json.dumps({'ev': 'poke', 'cmd': cmd, 'label': label, 'steps': self.total_steps}) + '\n')
        self._do(cmd)

    def poke_health(self, label='health full'):
        self.poke(HEALTH_FULL, label)

    def note_hurt(self, prev, s, why):
        """Health dropped between two ticks: log which live objects were within 40 px of the hero (hazard census)."""
        near = [dict(slot=o['slot'], type=o['type'], x=o['x'], y=o['y'], dx=o['dx'], dy=o['dy'],
                     w0=o['raw'][2 * 0:2 * 0 + 2].hex(), anim=o['raw'][22:26].hex())
                for o in self.near(40) if o['slot'] != 6]
        cat = list(s.sens.hex())
        self.hurts.append(dict(t=self.total_steps, wx=s.wx, block=s.block, y=s.y, hp=(prev.hp, s.hp), why=why, near=near))
        self.log(ev='hurt', t=self.total_steps, wx=s.wx, y=s.y, hp0=prev.hp, hp1=s.hp, why=why, near=near,
                 sens=s.sens.hex())
        if s.hp <= self.hp_floor:
            self.poke_health(f'hp {s.hp} <= floor {self.hp_floor}, refill at wx={s.wx} block={s.block}')
            self.last = self.read()

    def log(self, **kw):
        self.logf.write(json.dumps(kw) + '\n'); self.logf.flush()

    def snap(self, path):
        """Write a snapshot (side-effect-free, not part of the .repl)."""
        ap = path if os.path.isabs(path) else os.path.join(ROOT, path)
        os.makedirs(os.path.dirname(ap), exist_ok=True)
        self._raw(f'snap {ap}')

    def hold(self, bits, until=None, max_steps=600_000, tick=None, stall_ticks=0, why='', release=True,
             stall_key=None):
        """Hold joystick `bits`, stepping `tick` instructions at a time, until `until(state)` is truthy, the room
        changes ($227b4 differs from the entry value and x jumps), max_steps elapse, or (stall_ticks>0) the
        position `stall_key(state)` (default (wx, y)) has not changed for that many ticks. Returns
        (reason, state) with reason in {'until', 'max', 'stall'}."""
        tick = tick or self.tick
        self.set_bits(bits)
        used = 0
        key = stall_key or (lambda s: (s.wx, s.y))
        lastkey, same = None, 0
        reason = 'max'
        s = self.last
        while used < max_steps:
            self.step(tick); used += tick
            prev = self.last
            s = self.last = self.read_stable()
            self.nticks += 1
            if prev is not None and s.hp < prev.hp:
                self.note_hurt(prev, s, why)
            self.logf.write(json.dumps({'t': self.total_steps, 'in': f'{self.cur_bits:02x}', 'x': s.x, 'y': s.y, 'wx': s.wx,
                                        'st': s.st, 'busy': s.busy, 'cam': s.cam, 'blk': s.blk, 'hp': s.hp,
                                        'why': why}) + '\n')
            if self.ckpt_every and self.nticks % self.ckpt_every == 0:
                self.snap(os.path.join(self.ckpt_dir, f'ck_{self.total_steps:010d}.snap'))
            if until is not None and until(s):
                reason = 'until'; break
            if stall_ticks:
                k = key(s)
                same = same + 1 if k == lastkey else 0
                lastkey = k
                if same >= stall_ticks:
                    reason = 'stall'; break
        if release:
            self.set_bits(0)
        return reason, s

    def idle(self, steps, until=None, tick=None):
        """Release everything and let time pass (falls, transitions), reading each tick."""
        return self.hold(NONE, until=until, max_steps=steps, tick=tick)

    def hop(self, dirbits, up_steps=0, land_max=1_600_000, why='hop', tick=None, start_max=150_000):
        """Jump: hold UP|dir until the game starts the jump (state 2; the game polls the pad about every 24k
        steps, so this takes up to ~30k), keep UP|dir for a further `up_steps`, then hold `dir` alone until the
        hero is grounded again. Returns (started, landing state); started is False if no jump began."""
        reason, s = self.hold(UP | dirbits, until=lambda s: s.st in (2, 3), max_steps=start_max, why=why + '-up',
                              release=False, tick=tick)
        if reason != 'until':
            self.set_bits(0)
            return False, s
        if up_steps:
            self.hold(UP | dirbits, max_steps=up_steps, why=why + '-up2', release=False, tick=tick)
        return True, self.land(dirbits, land_max, why=why + '-air', tick=tick)

    def land(self, dirbits, land_max=1_600_000, why='air', tick=None):
        """Hold `dir` until the state is idle/walk and y is unchanged for two ticks (grounded)."""
        n = [0]
        lasty = [None]

        def done(s):
            ok = s.st in (0, 1) and lasty[0] == s.y
            lasty[0] = s.y
            n[0] = n[0] + 1 if ok else 0
            return n[0] >= 2
        return self.hold(dirbits, until=done, max_steps=land_max, why=why, tick=tick)[1]

    def finish(self, final_snap=None):
        """Write the replayable .repl and (optionally) the final snapshot, then quit the emulator."""
        with open(self.name + '.repl', 'w') as f:
            for c in self.script:
                f.write(c + '\n')
            if final_snap:
                fp = final_snap if os.path.isabs(final_snap) else os.path.join(ROOT, final_snap)
                f.write(f'snap {fp}\n')
            f.write('q\n')
        if final_snap:
            self.snap(final_snap)
        self.logf.write(json.dumps({'ev': 'end', 'steps': self.total_steps, 'rereads': self.reread_count}) + '\n')
        self.logf.close()
        try:
            self.p.stdin.write('q\n'); self.p.stdin.flush()
        except Exception:
            pass
        self.p.wait(timeout=30)

    def close(self):
        """Stop without saving a .repl (exploration)."""
        try:
            self.p.stdin.write('q\n'); self.p.stdin.flush()
        except Exception:
            pass
        self.p.wait(timeout=30)
        self.logf.close()


def replay(snap, repl, out_snap):
    """Re-run a recorded .repl from `snap`, writing out_snap (the .repl's own final `snap` line is rewritten)."""
    lines = [l.rstrip('\n') for l in open(repl)]
    lines = [('snap ' + (out_snap if os.path.isabs(out_snap) else os.path.join(ROOT, out_snap))) if l.startswith('snap ') else l
             for l in lines]
    env = dict(os.environ, ATARI_NOTRACE='1')
    r = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl', '--disk-a', DISK],
                       cwd=ROOT, env=env, input='\n'.join(lines) + '\n', text=True, capture_output=True)
    return r.stdout


if __name__ == '__main__':
    if len(sys.argv) >= 5 and sys.argv[1] == 'replay':
        t = time.time()
        replay(sys.argv[2], sys.argv[3], sys.argv[4])
        print('replayed in %.0fs -> %s' % (time.time() - t, sys.argv[4]))
    else:
        print(__doc__)
