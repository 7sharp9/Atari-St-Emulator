"""The Amazon boss fight of `boss_unpoked.py` / `boss_dodge139.py` on `tools/stdrive.py` (one `stserver`, journalled).

    uv run python reversing/impossamole/py/boss/boss_stdrive.py <boss-room snap> [--delay N] [--policy dodge139|unpoked]
        [--reach PX] [--t-lo F] [--t-hi F] [--max-iter N] [--out-dir DIR] [--tag NAME] [--dll stserver.dll] [--no-cache]
        [--record DIR]

The same policy, transliterated: `boss_fight.Fight` (swipe geometry, jump-and-fire `air_phase`), `boss_unpoked.DodgeFight` (retreat from
the type-140 lob, wait on the platform when the boss is at its left position) and `boss_dodge139.Dodge139Fight` (jump over a type-139 due
in t-lo..t-hi frames). `--policy unpoked` is `boss_unpoked.py` (reach 80, no 139 dodge); `--policy dodge139` (default) is
`boss_dodge139.py --reach 100 --t-lo 4 --t-hi 10 --max-iter 12000`, whose delay-700,000 run is the recorded kill (health 6). The left-position
fight (`--left-fight`) and the labelled pokes (`--weapon`, `--poke-health`) of the originals are not ported.

Every input and step is issued in the original's order with the original's step counts, and the joystick packet goes as the REPL's two
`kbd ff` / `kbd <bits>` calls (`stdrive.Joy(bits, split=True)`; `--joy-onecall` sends one call, which ends in the same snapshot here), so
the run must end in the same machine state as the REPL script; `hold` and `tap` are not used, because their VBL alignment would change
the fight. Checked: the delay-700,000 kill ends byte-identical to `pass108/boss/kill_d700000_end.snap`, and its journal replays to the
same bytes. The REPL `watch 1a645 1` hit count (lines with
`pc=$013b20`) is an stserver write watch on `$1a645` filtered to that PC. Output: `<out-dir>/<tag>_end.snap` and the stdrive journal
`<out-dir>/<tag>.jsonl`, which `uv run python tools/stdrive.py <journal> <dir>` replays.
"""
import argparse, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(HERE, '..', '..', '..', '..')))
sys.path.insert(0, os.path.join(os.path.abspath(os.path.join(HERE, '..', '..', '..', '..')), 'tools'))
import stdrive as sd

DISK = 'scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st'
SLOT0, STRIDE, NSLOTS = 0x1a2ea, 0x6c, 20      # object slots; the hero is slot 6 ($1a572), the boss 7, the swipe 16 ($1a9aa)
BOSS = 7
FRAME = 24000            # the scripts' "frame": two VBLs, about the game's poll period
QF = FRAME // 4
STEP_X, ROOM_X, FIRE_Y = 172, 260, 130
SHOT140, SHOT139 = 0x16184, 0x14790
OPEN_SHUT = 0x221f6      # boss animation while closed (invulnerable)
SPLIT = True             # the REPL's two kbd calls per packet; --joy-onecall sends one

FIELDS = {                # end-state fields (names from boss_fight.py / README "Boss")
    'health': (0xbb74, 1), 'weapon': (0xbb72, 1), 'bb73': (0xbb73, 1), 'boss_dead_flag': (0x22803, 1), 'level_flag_22804': (0x22804, 1),
    'hero_x': (0x1a574, 2), 'hero_y': (0x1a576, 2), 'hero_state': (0x227f3, 1), 'hero_face': (0x227f4, 1),
    'boss_type': (0x1a5de, 2), 'boss_x': (0x1a5e0, 2), 'boss_y': (0x1a5e2, 2), 'boss_hp': (0x1a5de + 103, 1), 'boss_anim': (0x1a5de + 22, 4),
}


def w(b, o): return int.from_bytes(b[o:o + 2], 'big')
def sw(b, o): return int.from_bytes(b[o:o + 2], 'big', signed=True)


def overlap_b71a(e, p):
    """$b71a on boxes (x, y, w, h): e = enemy (A0), p = projectile (A1)."""
    for a in (0, 1):
        d = e[a] - p[a]
        if d >= 0:
            if not d < p[2 + a]:
                return False
        elif not -d < e[2 + a]:
            return False
    return True


def overlap(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


class Fight:
    def __init__(self, d, reach=100, t_lo=4, t_hi=10, dodge=True):
        self.d = d
        self.reach, self.t_lo, self.t_hi, self.dodge = reach, t_lo, t_hi, dodge
        self.steps = self.jumps = self.pulses = self.swipes = self.hops = 0
        self.retreats = self.dodges = 0
        self.min_health = 99
        self.last_health = None
        self.damage_log, self.log140, self.log139 = [], [], []
        self.prev139 = {}
        d.step(1)                                       # Repl.__init__'s `s 1`
        self.weapon = d.u8(0xbb72)
        t = d.read(0xd4be + (self.weapon - 1) * 64, 8)
        self.p_dx, self.p_dy, self.p_w, self.p_h = sw(t, 2), sw(t, 4), t[6], t[7]
        self.p_mir = sw(d.read(0xd57e + (self.weapon - 1) * 2, 2), 0)
        self.hit_watch = d.rpc('watch_add', lo=0x1a645, kind='w', pc_lo=0x13b20, pc_hi=0x13b20, max_events=1)['id']

    # -- primitives (the original's `s` and `key`) --

    def slot(self, n):
        self.d.prefetch(SLOT0, NSLOTS * STRIDE)
        return self.d.read(SLOT0 + n * STRIDE, STRIDE)

    def s(self, n):
        self.d.step(n)
        self.steps += n

    def key0(self, bits, n):
        """boss_fight.Fight.key: the packet, then n steps."""
        self.d.press(sd.Joy(bits, split=SPLIT))
        self.s(n)

    def key(self, bits, n):
        """Dodge139Fight.key: a long grounded walk is cut short when a 140 can reach the hero or a 139 is due within t_hi frames."""
        if n <= 2 * FRAME:
            return self.key0(bits, n)
        self.d.press(sd.Joy(bits, split=SPLIT))
        done = 0
        while done < n:
            self.s(6000); done += 6000
            m = self.d.u8(0x227f3)
            if m in (0, 1):
                hx = self.r_hx()
                if self.shots140(hx):
                    break
                if self.dodge:
                    hy = sw(self.d.read(0x1a572, 8), 4)
                    t = self.due139(hx, hy)
                    if t is not None and t <= self.t_hi:
                        break

    def watch_hits(self):
        return next(x['hits'] for x in self.d.rpc('watch_list') if x['id'] == self.hit_watch)

    def r_hx(self):
        return sw(self.d.read(0x1a572, 8), 2)

    # -- state --

    def state_raw(self):
        d = self.d
        h = self.slot(6)
        b = self.slot(BOSS)
        m = d.read(0x227f3, 12)
        hp = d.u8(0xbb74)
        self.min_health = min(self.min_health, hp)
        if self.last_health is not None and hp < self.last_health:
            objs = [(n, w(self.slot(n), 0), sw(self.slot(n), 2), sw(self.slot(n), 4), self.slot(n)[104]) for n in range(8, 16)
                    if w(self.slot(n), 0)]
            self.damage_log.append((self.steps, self.last_health - hp, sw(h, 2), sw(h, 4), m[0], objs))
        self.last_health = hp
        return dict(hx=sw(h, 2), hy=sw(h, 4), ho=(sw(h, 8), sw(h, 10), h[12], h[13]),
                    st=m[0], face=m[1], fd=m[10],
                    bx=sw(b, 2), by=sw(b, 4), banim=int.from_bytes(b[22:26], 'big'), hp=b[103], binv=b[102],
                    bbox=(sw(b, 2) + sw(b, 8), sw(b, 4) + sw(b, 10), b[12], b[13]), btype=w(b, 0),
                    flag=d.u8(0x22803), health=hp)

    def state(self):
        """Dodge139Fight's wrapped state: a grounded hero with a 139 due in t_lo..t_hi frames jumps first."""
        s = self.state_raw()
        if self.dodge and s['st'] in (0, 1) and s['health'] and s['btype']:
            t = self.due139(s['hx'], s['hy'])
            if t is not None and self.t_lo <= t <= self.t_hi:
                self.jump139(s, t)
                s = self.state_raw()
            elif t is not None and t < self.t_lo:
                self.log139.append((self.steps, s['hx'], s['hy'], t, 'late'))
        return s

    # -- geometry (boss_fight.py) --

    def shot_box(self, hx, hy, face):
        return (hx + self.p_dx + (self.p_mir if face else 0), hy + self.p_dy, self.p_w, self.p_h)

    def hero_box(self, s, hx, hy):
        o = s['ho']
        return (hx + o[0], hy + o[1], o[2], o[3])

    def hits_ok(self, s, hx, hy, face=1):
        if not overlap_b71a(s['bbox'], self.shot_box(hx, hy, face)):
            return False
        return not overlap_b71a(s['bbox'], self.hero_box(s, hx, hy))

    def target_x(self, s, xmax):
        ok = [hx for hx in range(8, xmax + 1, 2) if self.hits_ok(s, hx, FIRE_Y)]
        return ok[len(ok) // 2] if ok else None

    # -- shots (boss_unpoked.py, boss_dodge139.py) --

    def shots140(self, hx=None):
        out = []
        for n in range(8, 16):
            b = self.slot(n)
            if w(b, 0) and int.from_bytes(b[86:90], 'big') == SHOT140 and b[101] == 0 and b[103] != 254 and sw(b, 4) < 165:
                out.append((n, sw(b, 2), sw(b, 4)))
        if hx is not None:
            bx = sw(self.slot(BOSS), 2)
            out = [o for o in out if abs(hx - (bx + 7)) < self.reach]
        return out

    def shots139(self):
        out, seen = [], set()
        for n in range(8, 16):
            b = self.slot(n)
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

    # -- actions --

    def air_phase(self, hop):
        self.jumps += 1
        self.hops += hop
        drift = 0x08 if hop else 0x00
        self.key(0x09 if hop else 0x01, FRAME + 6000)
        self.key(drift, 3000)
        for i in range(80):
            t = self.state()
            if i > 2 and t['st'] in (0, 1):
                break
            open_ = t['banim'] != OPEN_SHUT
            if t['st'] == 2 and t['fd'] == 0 and open_ and t['btype'] and self.hits_ok(t, t['hx'], t['hy'], t['face']):
                self.pulses += 1
                self.key(drift | 0x80, FRAME + 6000)
                if w(self.slot(16), 0):
                    self.swipes += 1
                self.key(drift, 1)
            else:
                self.s(6000)
        self.key(0, FRAME // 2)

    def to_platform(self, s):
        if s['hx'] < 150:
            self.key(0x08, max(6000, min((150 - s['hx']) // 2, 60) * FRAME)); self.key(0, 1)
        elif s['hx'] <= STEP_X:
            self.jumps += 1
            self.key(0x09, FRAME + 6000); self.key(0x08, 3 * FRAME); self.key(0, FRAME // 2)
        else:
            self.s(FRAME // 4)

    def retreat(self, s):
        self.retreats += 1
        sh = self.shots140(s['hx'])
        self.log140.append((self.steps, s['hx'], sh))
        t0 = self.steps
        sx0 = s['bx'] + 7
        goleft = s['hx'] <= sx0 or sx0 > 150
        while self.steps - t0 < 40 * FRAME:
            st = self.state()
            if st['health'] == 0 or st['btype'] == 0:
                return
            if not self.shots140(st['hx']):
                break
            if st['st'] in (0, 1):
                if goleft and st['hx'] > sx0 - self.reach:
                    self.key(0x04, 6000)
                elif not goleft and st['hx'] < sx0 + self.reach:
                    self.key(0x08, 6000)
                else:
                    self.key(0, 6000)
            else:
                self.s(6000)
        self.key(0, 6000)

    def jump139(self, s, t):
        self.dodges += 1
        self.log139.append((self.steps, s['hx'], s['hy'], t))
        self.jumps += 1
        self.key0(0x01, FRAME + 6000)
        self.key0(0x00, 3000)
        for i in range(80):
            st = self.state()
            if i > 2 and st['st'] in (0, 1):
                break
            self.s(6000)

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
            open_ = s['banim'] != OPEN_SHUT
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


class NoCacheDrive(sd.Drive):
    """A Drive whose reads all go to the server (for timing the cache's share)."""
    def read(self, addr, n):
        return self.s.read(addr, n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('snap')
    ap.add_argument('--disk', default=os.path.join(ROOT, DISK))
    ap.add_argument('--policy', choices=('dodge139', 'unpoked'), default='dodge139')
    ap.add_argument('--delay', type=int, default=0)
    ap.add_argument('--reach', type=int)
    ap.add_argument('--t-lo', type=float, default=4)
    ap.add_argument('--t-hi', type=float, default=10)
    ap.add_argument('--max-iter', type=int)
    ap.add_argument('--out-dir', default=os.path.join(ROOT, 'scratchpad', 'stdrive', 'boss'))
    ap.add_argument('--tag', default='boss')
    ap.add_argument('--dll', help='stserver.dll (default <root>/server/bin/Debug/net8.0/stserver.dll)')
    ap.add_argument('--no-cache', action='store_true')
    ap.add_argument('--record', help='record the fight to this directory (stdrive "Recordings": segments for provenance.py)')
    ap.add_argument('--joy-onecall', action='store_true', help='send each joystick packet as one kbd call (not the REPL form)')
    a = ap.parse_args()
    global SPLIT
    SPLIT = not a.joy_onecall
    dodge = a.policy == 'dodge139'
    reach = a.reach if a.reach is not None else (100 if dodge else 80)
    max_iter = a.max_iter if a.max_iter is not None else (12000 if dodge else 3000)
    os.makedirs(a.out_dir, exist_ok=True)
    t0 = time.time()
    D = NoCacheDrive if a.no_cache else sd.Drive
    d = D(ROOT, dll=a.dll, journal=os.path.join(a.out_dir, a.tag + '.jsonl'), fields=FIELDS, period=FRAME, record=a.record)
    d.load(a.snap, a.disk)
    d.note(f'boss_stdrive policy={a.policy} reach={reach} t_lo={a.t_lo} t_hi={a.t_hi} delay={a.delay} max_iter={max_iter}')
    f = Fight(d, reach=reach, t_lo=a.t_lo, t_hi=a.t_hi, dodge=dodge)
    if a.delay:
        f.s(a.delay)
    s = f.run(max_iter, lambda m: print(m, flush=True))
    print(f'RESULT hp={s["hp"]} $22803={s["flag"]:02x} jumps={f.jumps} pulses={f.pulses} swipes={f.swipes} hits={f.watch_hits()} '
          f'retreats={f.retreats} dodges={f.dodges} steps={f.steps} health={s["health"]} min_health={f.min_health} wall={time.time()-t0:.0f}s')
    for x in f.damage_log:
        print('damage', x)
    for x in f.log139:
        print('dodge139', x)
    end = d.save(os.path.join(a.out_dir, a.tag + '_end.snap'))
    print('fields', ' '.join(f'{k}={v:#x}' for k, v in d.fields().items()))
    d.close()
    print('end', end, 'journal', d.journal_path, f'wall={time.time()-t0:.1f}s')


if __name__ == '__main__':
    main()
