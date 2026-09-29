"""Event-driven joystick driver for Impossamole (hop4).

A live REPL wrapper. Each tick it sends a short input (`kbd ff` / `kbd <bits>`) plus `s <n>`, reads the hero
($1a572: x +2, y +4, busy +101), state $227f3, camera $227b6, room start block $227b4, health $bb74, and
reacts to the state (release up at a ladder top, steer, hop). Every state-changing command is appended to a
per-segment .repl (reads and the sentinel are not: they do not advance the machine), so the finished walk
replays byte-identically: `resume <snap> repl < segment.repl` reproduces the segment's end snapshot (cmp).

Poked commands (health `w bb74 12120300`) are logged too, and tagged with a `;POKE` marker in the sidecar
.log file (the .repl itself holds commands only: the REPL stops at unknown lines).

    ATARI_NOTRACE=1 uv run python route_driver.py [--out DIR]      # hop 4: room 299..318 -> boss room 318..326

Poked (labelled): the start room itself (`stage_room299.repl`, a block-283 top-exit poke from room188.snap) and
health, `w bb74 12120300`, at every segment start and whenever a tick reads health < 10.
"""
import os, subprocess, sys

ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))
DISK = 'scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st'
UP, DOWN, LEFT, RIGHT, FIRE = 1, 2, 4, 8, 0x80


class Driver:
    def __init__(self, snap, seg_repl=None, seg_log=None, verbose=True):
        env = dict(os.environ, ATARI_NOTRACE='1')
        self.p = subprocess.Popen(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl',
                                   '--disk-a', DISK], cwd=ROOT, env=env, text=True, bufsize=1,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.repl = open(seg_repl, 'w') if seg_repl else None
        self.log = open(seg_log, 'w') if seg_log else None
        self.verbose = verbose
        self.safe = False       # True: health poke must preserve $bb77 (the shop flag), see health()
        self.cur = 0            # currently latched joystick level
        self.steps = 0
        self.raw('s 1', log=True)

    # ---- plumbing
    def raw(self, *cmds, log=False, tag=''):
        """Send commands + sentinel; return output lines. log=True records state-changing commands."""
        for c in cmds:
            self.p.stdin.write(c + '\n')
            if log and self.repl:
                self.repl.write(c + '\n')
            if log and self.log:
                self.log.write(c + (' ;' + tag if tag else '') + '\n')
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
        return bytes.fromhex(''.join(self.raw(f'm {addr:x} {n}')[-1:]).replace(' ', ''))

    def poke(self, cmd, tag='POKE'):
        self.raw(cmd, log=True, tag=tag)

    def health(self):
        """Labelled poke: health full. `w bb74 12120300` also writes $bb76=3 and ZEROES $bb77, the shop flag
        ($e842 sets it to 1 inside the shop), which turns every shop item into a free pickup. In safe mode the
        longword is written at $bb72 instead (weapon and coins re-written with their current values)."""
        if self.safe:
            w, c = self.mem(0xbb72, 2)
            self.poke(f'w bb72 {w:02x}{c:02x}1212', 'POKE health full (bb72 weapon/bb73 coins kept, bb77 untouched)')
        else:
            self.poke('w bb74 12120300', 'POKE health full')

    def s(self, n):
        self.raw(f's {n}', log=True); self.steps += n

    def joy(self, bits):
        """Latch a joystick level (packet header + level)."""
        if bits != self.cur:
            self.raw('kbd ff', f'kbd {bits:02x}', log=True)
            self.cur = bits

    def press(self, bits, n):
        self.joy(bits); self.s(n)

    def snap(self, path):
        self.raw('snap ' + path, log=True)

    def close(self):
        self.p.stdin.write('q\n'); self.p.stdin.flush()
        self.p.wait(timeout=30)
        if self.repl: self.repl.close()
        if self.log: self.log.close()

    # ---- state
    def st(self):
        h = self.mem(0x1a572, 108)
        x = int.from_bytes(h[2:4], 'big'); y = int.from_bytes(h[4:6], 'big')
        if y >= 0x8000: y -= 0x10000
        m = self.mem(0x227b4, 8)
        e = self.mem(0x227ea, 6)
        return dict(x=x, y=y, busy=h[101], state=self.mem(0x227f3, 1)[0],
                    blk=int.from_bytes(m[0:2], 'big'), cam=int.from_bytes(m[2:4], 'big'),
                    lim=int.from_bytes(m[4:6], 'big'), hp=self.mem(0xbb74, 1)[0], sens=e.hex())

    def objs(self):
        """The 20 object slots ($1a2ea, stride $6c) as dicts: type, x, y, frame, anim ptr, handler."""
        raw = b''.join(self.mem(0x1a2ea + n * 108, 108) for n in range(20))
        out = []
        for n in range(20):
            b = raw[n * 108:(n + 1) * 108]
            sw = lambda o: int.from_bytes(b[o:o + 2], 'big', signed=True)
            out.append(dict(slot=n, type=sw(0) & 0xffff, x=sw(2), y=sw(4), w6=sw(6) & 0xffff,
                            anim=int.from_bytes(b[22:26], 'big'), idx=sw(26), handler=int.from_bytes(b[86:90], 'big'),
                            hp=b[103], b100=b[100], b101=b[101]))
        return out

    def wx(self, s=None):
        s = s or self.st()
        return s['x'] + s['cam'] - 32

    def show(self, tag=''):
        s = self.st()
        if self.verbose:
            print(f"{tag:12s} steps={self.steps:8d} x={s['x']:3d} y={s['y']:4d} wx={s['x'] + s['cam'] - 32:5d} "
                  f"st={s['state']} busy={s['busy']} cam={s['cam']:04x} blk={s['blk']:x} hp={s['hp']} sens={s['sens']}",
                  flush=True)
        return s


# ------------------------------------------------------------------ the hop-4 route
OUT = os.path.join(ROOT, 'scratchpad/impossamole/agents/hop4')


def until(d, cond, tick, maxticks, bits=None, fix_health=True):
    """Hold `bits` (if given), step `tick` at a time, return the first state satisfying cond(state)."""
    if bits is not None:
        d.joy(bits)
    for _ in range(maxticks):
        d.s(tick)
        s = d.st()
        if fix_health and s['hp'] < 10:
            d.health(); s = d.st()
        if cond(s):
            return s
    raise RuntimeError('condition not reached: ' + str(s))


def wxof(s):
    return s['x'] + s['cam'] - 32


def seg_ladder_a(d):
    """Walk right along the low tunnel to ladder A (world x 9728), climb it, release up at the top (y=48, state 0)."""
    d.health()
    d.press(RIGHT, 30000)                       # the first poll after the resume swallows the packet
    until(d, lambda s: wxof(s) >= 9720, 15000, 100, RIGHT)
    d.joy(0); d.s(30000)
    d.joy(UP)                                    # sensors read ladder tiles $63/$64 at wx 9718..9722 (9714 stalls)
    until(d, lambda s: s['state'] == 0 and s['y'] < 100, 8000, 400)
    d.joy(0); d.s(60000)                          # release up at the top: holding it would start a jump


def seg_traverse_b(d):
    """Right along the ledge above the rock (row 64) to world x 9784, then down ladder B to the tunnel floor."""
    d.health()
    d.press(RIGHT, 30000)
    until(d, lambda s: wxof(s) >= 9784, 15000, 200, RIGHT)
    d.joy(0); d.s(30000)
    d.joy(DOWN)
    until(d, lambda s: s['state'] == 0 and s['y'] > 120, 10000, 300)
    d.joy(0); d.s(30000)


def seg_tunnel_hop(d):
    """Right along the tunnel to its end wall (world x 9896), hop up onto the 32 px ledge, right to the next wall."""
    d.health()
    d.press(RIGHT, 30000)
    until(d, lambda s: wxof(s) >= 9896, 15000, 300, RIGHT)
    d.joy(0); d.s(60000)
    d.press(UP | RIGHT, 30000)
    d.press(RIGHT, 30000)
    until(d, lambda s: s['state'] == 0 and s['y'] == 112, 30000, 40, RIGHT)
    d.press(RIGHT, 60000); d.joy(0); d.s(30000)


def seg_wall_hop(d):
    """Hop up the second 32 px step onto the rock top (y=80) and walk right down the stairs to the pit edge."""
    d.health()
    d.press(UP | RIGHT, 30000)
    d.press(RIGHT, 30000)
    until(d, lambda s: s['state'] == 1 and s['y'] == 80, 30000, 40, RIGHT)


def seg_pit_exit(d):
    """Right down the stairs and along the grass to the pit at block 317, release right once falling, and wait
    for the exit checker ($df4a) to install room 318..326 (the fade takes several hundred thousand steps)."""
    d.health()
    d.press(RIGHT, 30000)
    until(d, lambda s: s['state'] == 3 and s['y'] > 150 and wxof(s) >= 10128, 30000, 200, RIGHT)
    d.joy(0)
    until(d, lambda s: s['blk'] == 0x13e, 30000, 60)
    d.s(600000)


def mole_slot(d):
    """The object slot whose per-frame handler is $00e842 (the mole), or None."""
    for o in d.objs():
        if o['type'] and o['handler'] == 0xe842:
            return o
    return None


def anim_done(d, o):
    """True when the animation list word at anim+idx is $fffd (hold the last frame)."""
    return int.from_bytes(d.mem(o['anim'] + o['idx'], 2), 'big') == 0xfffd


def seg_shop_walk(d):
    """Branch from the end of seg4: down the stairs to the camera limit, then left along the grass and off the
    ground into the block-313 shaft where the mole (type 9) sits; stand there until it has climbed out."""
    d.health()
    d.press(RIGHT, 30000)
    until(d, lambda s: wxof(s) >= 10078, 30000, 200, RIGHT)
    d.joy(0); d.s(60000)
    d.press(LEFT, 30000)

    def cond(s):
        o = mole_slot(d)
        print(f"   walk-left hero=({s['x']},{s['y']}) st={s['state']} mole x={o['x'] if o else None} "
              f"frame={o['w6'] if o else None} idx={o['idx'] if o else None}", flush=True)
        return s['state'] == 0 and s['y'] >= 160
    until(d, cond, 15000, 200, LEFT)
    d.joy(0); d.s(30000)


def seg_shop_wait(d):
    """Idle beside the mole until its animation reaches the hold word $fffd."""
    d.health()
    for _ in range(200):
        o = mole_slot(d)
        if o and anim_done(d, o):
            break
        d.s(50000)
    else:
        raise RuntimeError('mole animation never finished')


def seg_boss_settle(d):
    """No input: wait in the boss room until the falling hero has landed (state 0, y=144) with the boss alive."""
    d.health()
    until(d, lambda s: s['state'] == 0 and s['y'] == 144, 50000, 100)
    d.s(100000)


SEGMENTS = [('seg1_ladder_a', seg_ladder_a), ('seg2_traverse_b', seg_traverse_b),
            ('seg3_tunnel_hop', seg_tunnel_hop), ('seg4_wall_hop', seg_wall_hop),
            ('seg5_pit_exit', seg_pit_exit)]


def seg_shop_enter(d):
    """Press DOWN on the fully emerged mole ($e842, bb77 == 0): the room installer runs with the $ea92 record
    (world 3: blocks 410..418). Release down once the new room's start block is installed and let the fade end."""
    d.health()
    d.press(DOWN, 30000)
    until(d, lambda s: s['blk'] == 0x19a, 30000, 60, DOWN)
    d.joy(0); d.s(600000)


def shop_items(d):
    """Pickup slots 0-5 that are live: (slot, x, y, frame, item $79(A0))."""
    out = []
    for n in range(6):
        b = d.mem(0x1a2ea + n * 108, 108)
        if int.from_bytes(b[0:2], 'big'):
            out.append((n, int.from_bytes(b[2:4], 'big'), int.from_bytes(b[4:6], 'big'), int.from_bytes(b[6:8], 'big'), b[79]))
    return out


def shop_bubble(d):
    """(mole frame, bubble frame, bubble anim ptr) of slots 7 and 8."""
    a = d.mem(0x1a5de, 108); b = d.mem(0x1a64a, 108)
    return (int.from_bytes(a[6:8], 'big'), int.from_bytes(b[6:8], 'big'), int.from_bytes(b[22:26], 'big'))


def seg_shop_touch(d):
    """Walk left along the floor onto the low item (slot 3, item 1) and log the bubble each tick."""
    d.safe = True
    d.health()
    d.press(LEFT, 30000)
    for _ in range(40):
        d.s(15000)
        s = d.st()
        print('   touch', s['x'], s['y'], 'coins', d.mem(0xbb73, 1)[0], 'bubble(mole,bubble,anim)', [hex(v) for v in shop_bubble(d)], flush=True)
        if shop_bubble(d)[1] not in (0x3e, 0):
            break
    d.joy(0); d.s(60000)


def shop_line(d, tag):
    s = d.st(); o = d.objs()
    b = d.mem(0xbb72, 6)
    print(f"   {tag} hero=({s['x']},{s['y']}) st={s['state']} weapon={b[0]} coins={b[1]} hp={b[2]}/{b[3]} bb77={b[5]:02x} "
          f"$22801={d.mem(0x22801, 1)[0]:02x} slot3={o[3]['type']} slot2={o[2]['type']} mole/bubble frames+anim="
          f"{[hex(v) for v in shop_bubble(d)]}", flush=True)


def fire_pulse(d, hold=45000):
    """One real fire press: level 80 held for `hold` steps (> one poll), then released."""
    d.joy(FIRE); d.s(hold); d.joy(0)


def seg_shop_toomuch(d):
    """Fire on the worm can with the natural 25 coins (price 75): expect the TOO MUCH bubble ($4f)."""
    d.safe = True
    d.health()
    shop_line(d, 'before')
    fire_pulse(d)
    for i in range(12):
        d.s(20000); shop_line(d, f'after+{i}')


def seg_shop_buy(d):
    """Labelled poke: coins 255, health 5 (weapon kept), then fire on the worm can (price 75)."""
    d.safe = True
    d.poke('w bb72 03ff0512', 'POKE coins=255 hp=5/18 weapon=3 (test staging)')
    shop_line(d, 'staged')
    fire_pulse(d)
    for i in range(30):
        d.s(20000); shop_line(d, f'after+{i}')


def seg_shop_exit(d):
    """Walk right to the shopkeeper, log the EXIT? bubble, fire, and wait for the return room."""
    d.safe = True
    d.health()
    d.press(RIGHT, 30000)
    until(d, lambda s: shop_bubble(d)[1] == 0x4d, 15000, 100, RIGHT)
    d.joy(0); d.s(30000)
    shop_line(d, 'at mole')
    d.snap('scratchpad/impossamole/agents/hop4/shop_exit_bubble.snap')
    fire_pulse(d)
    for i in range(10):
        d.s(100000); shop_line(d, f'exit+{i}'); s = d.show('  ')


def seg_control_early_down(d):
    """Negative control for the entry: hold DOWN from the moment the hero lands in the shaft (mole still climbing
    out). The room must not change until the mole's animation reaches its hold word $fffd."""
    d.health()
    d.joy(DOWN)
    for i in range(60):
        d.s(50000)
        o = mole_slot(d); s = d.st()
        done = anim_done(d, o) if o else None
        print(f"   t={i:2d} blk={s['blk']:x} bb77={d.mem(0xbb77, 1)[0]:02x} mole frame={o['w6'] if o else None} idx={o['idx'] if o else None} "
              f"anim_at_fffd={done}", flush=True)
        if s['blk'] == 0x19a:
            break
    d.joy(0)


BRANCH = [('seg5b_shop_walk', seg_shop_walk), ('seg6b_shop_wait', seg_shop_wait),
          ('seg7b_shop_enter', seg_shop_enter), ('seg8b_shop_touch', seg_shop_touch),
          ('seg9b_shop_toomuch', seg_shop_toomuch), ('seg10b_shop_buy', seg_shop_buy),
          ('seg11b_shop_exit', seg_shop_exit)]


def run_all(start, which=None, segments=None, prefix=''):
    """Run segments in order, each from the previous end snapshot; files are <prefix><name>.{repl,log,snap}."""
    snap = start
    for name, fn in (segments or SEGMENTS):
        if which and name not in which:
            snap = os.path.join('scratchpad/impossamole/agents/hop4', prefix + name + '.snap'); continue
        d = Driver(snap, os.path.join(OUT, prefix + name + '.repl'), os.path.join(OUT, prefix + name + '.log'))
        d.show(name + ' start')
        fn(d)
        d.show(name + ' end')
        snap = os.path.join('scratchpad/impossamole/agents/hop4', prefix + name + '.snap')
        d.snap(snap)
        d.close()


if __name__ == '__main__':
    args = sys.argv[1:]
    if args and args[0] == '--control':       # negative control: DOWN pressed while the mole is still climbing
        run_all('scratchpad/impossamole/agents/hop4/seg5b_shop_walk.snap', None,
                [('seg6c_early_down', seg_control_early_down)])
    elif args and args[0] == '--real':        # main route from hop3's real-input room299.snap, files real_<seg>.*
        run_all('scratchpad/impossamole/agents/hop3/room299.snap', args[1:] or None,
                SEGMENTS + [('seg6_boss_settle', seg_boss_settle)], prefix='real_')
    elif args and args[0] == '--shop':          # the mole/shop branch, started from the end of seg4
        run_all('scratchpad/impossamole/agents/hop4/seg4_wall_hop.snap', None, BRANCH)
    else:
        run_all('scratchpad/impossamole/agents/hop4/room299_poked.snap', args or None)
