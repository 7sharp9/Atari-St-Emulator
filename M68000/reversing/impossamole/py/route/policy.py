"""Policy harness for hop 3 segments 1-5 (unpoked except ONE health poke to 18 at the start of the first segment run).

    cd M68000 && ATARI_NOTRACE=1 uv run python reversing/impossamole/py/route/policy.py run <policy> <segs> [--chain] [--tag T]

  <segs>   comma list of 1..5 (e.g. 2,3) or 1-5.
  --chain  start seg k from THIS policy's own end snapshot of seg k-1 (seg 1 from room188.snap); the poke happens only in
           the first segment run. Without --chain each segment starts from the poked route's snapshot
           agents/hop3/snaps/seg(k-1)_*.snap (seg 1: pass103/room188.snap) with hp poked to 18.
Outputs (under agents/unpoked/policy/<tag or policy>/): segN.repl .log .snap .json.  The .json has hp lost, hurt list with the
culprit handler/type/hp, steps, pulses, hops, confirmed swipes (a shot object seen in slots 16-19 during the pulse).
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import route_driver, route_hop3, natural_hop3
from route_driver import *
from natural_hop3 import NatDriver

OUT = 'scratchpad/impossamole/agents/unpoked/policy'
SEGFN = {1: 'seg1_pillar_totem', 2: 'seg2_plateau_edge', 3: 'seg3_water1', 4: 'seg4_notches', 5: 'seg5_stone_hole'}
POKED = 'scratchpad/impossamole/agents/hop3/snaps/%s.snap'
START = 'scratchpad/impossamole/pass103/room188.snap'
HNAME = {0x15934: 'monkey', 0x15ac8: 'plant', 0x15a38: 'tentacle', 0x1415e: 'bee-wander', 0x1417c: 'bee-chase',
         0x142be: 'flier', 0x15b3c: 'flier-script', 0x15c7a: 'snake126', 0x15c82: 'snake127', 0x15ca6: 'chameleon',
         0x15d26: 'croc', 0x1439e: 'rock', 0x13cb4: 'slab', 0x16210: 'coconut', 0x14790: 'spit', 0x15e54: 'tongue',
         0x15d82: 'bush131', 0x15d9c: 'bush132', 0x147e6: 'monkeydrop'}

# policy name -> params. mode: 'A' none, 'B' natural_hop3 guard, 'C' generic guard driven by params
POLICIES = {
    'A': dict(mode='A'),
    'B': dict(mode='B'),
    'C1': dict(mode='C', bx_lo=-30, bx_hi=50, by_lo=-40, by_hi=40, hop_dx=44, hop_dy=20, cool=150000, face='toward'),
    'C0': dict(mode='C', bx_lo=0, bx_hi=50, by_lo=-20, by_hi=20, hop_dx=44, hop_dy=20, cool=150000, handlers=None),
    'S1': dict(mode='C', bx_lo=-30, bx_hi=50, by_lo=-14, by_hi=40, hop_dx=44, hop_dy=20, cool=150000, face='toward',
               snipe=dict(handlers=[0x15934], dx_lo=28, dx_hi=46, dy_lo=-44, dy_hi=-10)),
    'R1': dict(mode='C', hop_dx=44, hop_dy=20, cool=150000, face='keep',
               rules=[dict(handlers=[0x1415e, 0x1417c], box=(-30, 50, -40, 40), face='toward'),
                      dict(handlers=None, box=(0, 50, -14, 40), face='keep')],
               snipe=dict(handlers=[0x15934], dx_lo=28, dx_hi=46, dy_lo=-44, dy_hi=-10)),
    'R2': dict(mode='C', hop_dx=44, hop_dy=20, cool=150000, face='keep',
               rules=[dict(handlers=[0x1415e, 0x1417c], box=(-30, 50, -40, 40), face='toward'),
                      dict(handlers=None, box=(0, 50, -14, 40), face='keep')],
               snipe=dict(handlers=[0x15934], dx_lo=28, dx_hi=46, dy_lo=-62, dy_hi=-10)),
    'R3': dict(mode='C', hop_dx=44, hop_dy=20, cool=150000, face='keep',
               rules=[dict(handlers=[0x1415e, 0x1417c], box=(-30, 50, -40, 40), face='toward'),
                      dict(handlers=None, box=(0, 50, -14, 40), face='keep')],
               snipe=dict(handlers=[0x15934], dx_lo=28, dx_hi=46, dy_lo=-62, dy_hi=-10),
               stand_fire=dict(handlers=[0x15934], dx_lo=28, dx_hi=60, dy_lo=-100, dy_hi=-63, lure_dx=20, max_pulses=6)),
    'R4': dict(mode='C', hop_dx=28, hop_dy=20, cool=150000, face='keep',
               rules=[dict(handlers=[0x1415e, 0x1417c], box=(-30, 50, -40, 40), face='toward'),
                      dict(handlers=None, box=(0, 50, -14, 40), face='keep')],
               snipe=dict(handlers=[0x15934], dx_lo=28, dx_hi=46, dy_lo=-62, dy_hi=-10),
               stand_fire=dict(handlers=[0x15934], dx_lo=28, dx_hi=60, dy_lo=-100, dy_hi=-63, lure_dx=20, max_pulses=6)),
    'BEST': dict(mode='C', hop_dx=28, hop_dy=20, cool=150000, face='keep', settle=48000,
               rules=[dict(handlers=[0x1415e, 0x1417c], box=(-30, 50, -40, 40), face='toward'),
                      dict(handlers=None, box=(0, 50, -14, 40), face='keep')],
               snipe=dict(handlers=[0x15934], dx_lo=28, dx_hi=46, dy_lo=-62, dy_hi=-10),
               stand_fire=dict(handlers=[0x15934], dx_lo=28, dx_hi=60, dy_lo=-100, dy_hi=-63, lure_dx=26, max_pulses=6)),
    'T': dict(mode='C', trace=True, bx_lo=999, bx_hi=999, by_lo=999, by_hi=999, hop_dx=0, hop_dy=0, hop=False, cool=150000),
}


def hn(h):
    return HNAME.get(h, hex(h))


class PolicyDriver(NatDriver):
    def __init__(self, *a, **kw):
        self.P = kw.pop('P')
        self._hero = None
        self._hp_seen = None
        self.site = {'$00eb8c': 0, '$00ebca': 0}
        self._site0 = dict(self.site)
        self.hurt_list = []
        self.sniped = {}
        self.sfd = {}
        self.snipes = 0
        self.swipes_ok = 0
        self.swipes_miss = 0
        self.shot_seen = False
        self.trace_on = self.P.get('trace', False)
        super().__init__(*a, **kw)

    # ---- state / census ----
    def read(self):
        s = super().read()
        self._hero = (s.x, s.y)
        if self._hp_seen is not None and s.hp < self._hp_seen:
            self._census(s, self._hp_seen)
        if self.P.get('trace_croc') and not getattr(self, '_in_tc', False):
            self._in_tc = True
            cr = [(o['slot'], o['dx'], o['dy'], o['raw'][26:28].hex(), o['raw'][22:26].hex()) for o in self.objects() if o['h'] == 0x15d26]
            self.log(ev='croc', t=self.total_steps, hero=(s.wx, s.y, s.st, s.hp), c=cr)
            self._in_tc = False
        self._hp_seen = s.hp
        self._site0 = dict(self.site)
        return s

    def objects(self):
        raw = bytes.fromhex(''.join(self._raw('m 1a2ea 2160')).replace(' ', ''))
        hx, hy = self._hero if self._hero else (0, 0)
        out = []
        for i in range(20):
            b = raw[i * 0x6c:(i + 1) * 0x6c]
            ty = int.from_bytes(b[0:2], 'big'); x = s16(int.from_bytes(b[2:4], 'big')); y = s16(int.from_bytes(b[4:6], 'big'))
            out.append(dict(slot=i, type=ty, x=x, y=y, dx=x - hx, dy=y - hy, raw=b,
                            hp=b[103], dmg=b[104], h=int.from_bytes(b[86:90], 'big'), dead=b[101], inv=b[102]))
        return out

    def mons(self, r=200):
        """Live hostile objects: slots 7-15 (kind 1 monsters and kind 3 spawned hazards), damage > 0, not dying."""
        return [o for o in self.objects() if 7 <= o['slot'] <= 15 and o['type'] and o['dmg'] > 0 and o['hp'] not in (0, 254)
                and o['dead'] == 0 and abs(o['dx']) <= r and abs(o['dy']) <= r]

    def _census(self, s, prev_hp):
        near = [dict(slot=o['slot'], h=hn(o['h']), hp=o['hp'], dmg=o['dmg'], dx=o['dx'], dy=o['dy'], ty=o['type'])
                for o in self.objects() if o['type'] and o['slot'] != 6 and abs(o['dx']) <= 44 and abs(o['dy']) <= 44
                and o['slot'] not in range(16, 20)]
        site = 'contact' if self.site['$00eb8c'] > self._site0['$00eb8c'] else ('tile' if self.site['$00ebca'] > self._site0['$00ebca'] else '?')
        self.hurt_list.append(dict(t=self.total_steps, wx=s.wx, y=s.y, st=s.st, hp=(prev_hp, s.hp), near=near, site=site))
        self.log(ev='hurt', t=self.total_steps, wx=s.wx, y=s.y, st=s.st, hp0=prev_hp, hp1=s.hp, near=near, site=site)

    def note_hurt(self, prev, s, why):
        pass   # read() records hurts at the moment they are observed

    def initial_poke(self, hp=18):
        """One health poke that preserves the neighbouring bytes ($bb75 max, $bb76 world index, $bb77 shop flag)."""
        b = self.mem(0xbb74, 4)
        cmd = 'w bb74 %02x%s' % (hp, b[1:].hex())
        self.log(ev='initial_poke', cmd=cmd, before=b.hex())
        Driver.poke(self, cmd, 'initial health %d' % hp)
        self.last = self.read()
        self._hp_seen = self.last.hp

    # ---- stepping with swipe confirmation ----
    def _hs(self, c):
        """`s c` recorded in the .repl, run as `hits c eb8c ebca` (same emulation, counts the two decrement sites)."""
        self.script.append(f's {c}'); self.total_steps += c
        for l in self._raw(f'hits {c} eb8c ebca'):
            f = l.split()
            if len(f) >= 2 and f[0] in ('$00eb8c', '$00ebca'):
                self.site[f[0]] += int(f[1])

    def step(self, n):
        if self.cur_bits & FIRE and n > 10_000:
            k = 0
            while k < n:
                c = min(6_000, n - k)
                self._hs(c)
                k += c
                if not self.shot_seen:
                    self.shot_seen = any(16 <= o['slot'] < 20 and o['type'] for o in self.objects())
        else:
            self._hs(n)

    # ---- guard ----
    def read_stable(self):
        m = self.P['mode']
        if m == 'A':
            return Driver.read_stable(self)
        if m == 'B':
            return self._b_stable()
        return self._c_stable()

    def _b_stable(self):
        """natural_hop3's guard verbatim, wrapped so pulses are counted as confirmed or not."""
        p0 = self.pulses
        self.shot_seen = False
        pulse_t = None
        s = NatDriver.read_stable(self)
        if self.pulses > p0:
            if self.shot_seen: self.swipes_ok += self.pulses - p0
            else: self.swipes_miss += self.pulses - p0
        return s

    def stand_fire(self, slot, s, sf):
        """Lure-and-kill: walk on until the target's dx <= sf['lure_dx'] (it triggers and drops), then stand still and fire
        every ~150k steps until it is dead, out of range, or sf['max_pulses'] is reached."""
        keep = self.cur_bits
        self.log(ev='stand_fire', t=self.total_steps, slot=slot, hero=(s.x, s.y))
        def tgt():
            return [o for o in self.objects() if o['slot'] == slot][0]
        o = tgt()
        n_walk = 0
        while o['dx'] > sf['lure_dx'] and n_walk < 60 and o['type'] and o['hp'] < 128:
            self.set_bits(RIGHT); self.step(6000); self.last = self.read(); o = tgt(); n_walk += 1
        self.set_bits(0)
        fired = 0
        while fired < sf['max_pulses']:
            o = tgt()
            if o['type'] == 0 or o['hp'] >= 128 or o['hp'] == 0 or o['dead'] or abs(o['dx']) > 70:
                break
            self.set_bits(FIRE); self.shot_seen = False
            self.step(30_000)
            self.set_bits(0)
            fired += 1; self.pulses += 1
            if self.shot_seen: self.swipes_ok += 1
            else: self.swipes_miss += 1
            self.step(sf.get('gap', 120_000))
            self.last = self.read()
            if self.last.hp <= 0: break
        o = tgt()
        self.log(ev='stand_fire_end', t=self.total_steps, fired=fired, tgt_hp=o['hp'], dead=o['dead'], type=o['type'], dx=o['dx'], dy=o['dy'])
        self.set_bits(keep)
        return self.last

    def snipe(self, slot, s, sn):
        """Stop, jump straight up and fire every ~150k steps during the flight at object `slot` until it is dead, lands or
        the cap is reached. Returns the state after landing. The swipe box rides up with the hero, so a monkey perched above
        head height is reachable only from the air."""
        keep = self.cur_bits
        self.snipes += 1
        tgt0 = [o for o in self.objects() if o['slot'] == slot][0]
        self.log(ev='snipe', t=self.total_steps, slot=slot, hero=(s.x, s.y), tgt=(tgt0['hp'], tgt0['dx'], tgt0['dy']))
        face = keep & (LEFT | RIGHT)
        self.set_bits(sn.get('dirbits', 0))
        r, s2 = self.hold(sn.get('dirbits', 0) | UP, until=lambda x: x.st in (2, 3), max_steps=150_000, why='snipe-up', release=False)
        if r != 'until':
            self.set_bits(keep); return s2
        self.set_bits(sn.get('dirbits', 0))
        fired = 0
        t_start = self.total_steps
        while self.total_steps - t_start < sn.get('air_max', 1_400_000):
            o = [o for o in self.objects() if o['slot'] == slot][0]
            if o['type'] == 0 or o['hp'] >= 128 or o['hp'] == 0 or o['dead']:
                break
            self.set_bits(sn.get('dirbits', 0) | FIRE)
            self.shot_seen = False
            self.step(30_000)
            self.set_bits(sn.get('dirbits', 0))
            fired += 1; self.pulses += 1
            if self.shot_seen: self.swipes_ok += 1
            else: self.swipes_miss += 1
            self.step(sn.get('gap', 120_000))
            s3 = self.last = self.read()
            if s3.st in (0, 1) and s3.hp > 0 and self.total_steps - t_start > 150_000:
                break
        o = [o for o in self.objects() if o['slot'] == slot][0]
        self.log(ev='snipe_end', t=self.total_steps, fired=fired, tgt_hp=o['hp'], dead=o['dead'], type=o['type'])
        if o['dead'] or o['hp'] >= 128 or o['type'] == 0: self.sniped.pop(slot, None)
        s4 = self.land(sn.get('dirbits', 0), why='snipe-land')
        self.set_bits(keep)
        return self.last

    def _c_stable(self):
        P = self.P
        s = Driver.read_stable(self)
        if self.busy_guard or s.hp <= 0 or s.st not in (0, 1):
            return s
        self.busy_guard = True
        try:
            ms = self.mons(r=140)
            if self.trace_on and ms:
                self.log(ev='mon', t=self.total_steps, hero=(s.wx, s.y), m=[(o['slot'], hn(o['h']), o['hp'], o['dx'], o['dy']) for o in ms])
            sf = P.get('stand_fire')
            if sf:
                cands = [o for o in ms if o['h'] in sf['handlers'] and 0 < o['hp'] < 128 and sf['dx_lo'] <= o['dx'] <= sf['dx_hi']
                         and sf['dy_lo'] <= o['dy'] <= sf['dy_hi'] and self.sfd.get(o['slot'], 0) < sf.get('tries', 2)]
                if cands:
                    o = cands[0]
                    self.sfd[o['slot']] = self.sfd.get(o['slot'], 0) + 1
                    s = self.stand_fire(o['slot'], s, sf)
                    return s
            sn = P.get('snipe')
            if sn:
                cands = [o for o in ms if o['h'] in sn['handlers'] and 0 < o['hp'] < 128 and sn['dx_lo'] <= o['dx'] <= sn['dx_hi']
                         and sn['dy_lo'] <= o['dy'] <= sn['dy_hi'] and self.sniped.get(o['slot'], 0) < sn.get('tries', 4)]
                if cands:
                    o = cands[0]
                    self.sniped[o['slot']] = self.sniped.get(o['slot'], 0) + 1
                    s = self.snipe(o['slot'], s, sn)
                    return s
            rules = P.get('rules') or [dict(handlers=None, box=(P['bx_lo'], P['bx_hi'], P['by_lo'], P['by_hi']))]
            def rule_for(o):
                for r in rules:
                    if r['handlers'] is None or o['h'] in r['handlers']:
                        return r
            kill = []
            for o in ms:
                if not (0 < o['hp'] < 128):
                    continue
                r = rule_for(o)
                if r and r['box'][0] <= o['dx'] <= r['box'][1] and r['box'][2] <= o['dy'] <= r['box'][3]:
                    kill.append(o)
            hop = [o for o in ms if o['hp'] >= 128 and 0 < o['dx'] <= P['hop_dx'] and abs(o['dy']) <= P['hop_dy']
                   and (P.get('hop_handlers') is None or o['h'] in P['hop_handlers'])]
            if kill and self.total_steps - self.last_pulse > P['cool']:
                self.pulses += 1
                self.last_pulse = self.total_steps
                tg = [(o['slot'], hn(o['h']), o['hp'], o['dx'], o['dy']) for o in kill]
                keep = self.cur_bits
                face = keep
                if P.get('face') == 'toward' or rule_for(kill[0]).get('face') == 'toward':
                    t0 = min(kill, key=lambda o: abs(o['dx']) + abs(o['dy']))
                    if t0['dx'] < P.get('face_thr', -4):
                        face = (keep & ~RIGHT) | LEFT
                    else:
                        face = (keep & ~LEFT) | RIGHT
                self.shot_seen = False
                self.set_bits(((0 if (P.get('stand') or rule_for(kill[0]).get('stand')) else face)) | FIRE)
                for _ in range(P.get('npulse', 1)):
                    self.step(P.get('pulse', 30_000))
                self.set_bits(keep)
                if self.shot_seen: self.swipes_ok += 1
                else: self.swipes_miss += 1
                post = {o['slot']: (o['hp'], o['dx'], o['dy']) for o in self.objects() if o['slot'] in [t[0] for t in tg]}
                self.log(ev='pulse', t=self.total_steps, tgt=tg, hero=(s.x, s.y), shot=self.shot_seen, post=post, face=face)
                s = Driver.read_stable(self)
            elif hop and P.get('hop', True):
                self.hops += 1
                self.log(ev='dodge_hop', t=self.total_steps, tgt=[(o['slot'], hn(o['h']), o['dx'], o['dy']) for o in hop], hero=(s.x, s.y))
                keep = self.cur_bits
                if P.get('hop_stand'):
                    self.set_bits(0)
                    for _ in range(P['hop_stand']):
                        self.step(8000)
                        self.last = self.read()
                self.hop(P.get('hop_dir', RIGHT), why='dodge')
                self.set_bits(keep)
                s = self.last = Driver.read_stable(self)
        finally:
            self.busy_guard = False
        return s


def seg3_ride(d):
    """Segment 3 variant: after the hop onto the crocodile, stand still and let it carry the hero (no walking on its back)."""
    route_hop3.walk_to(d, 6488, why='to water edge')
    ok, s = d.hop(RIGHT, why='water hop', land_max=1_600_000)
    route_hop3.rep(d, 'on croc')
    d.hold(NONE, until=lambda s: s.wx >= 6592 or s.y >= 140 or s.hp < 18, max_steps=3_000_000, why='ride')
    route_hop3.rep(d, 'after ride')
    route_hop3.walk_to(d, 6660, why='off plateau 2'); d.land(RIGHT, why='drop to floor'); route_hop3.rep(d, 'floor')


SEG_OVERRIDE = {3: seg3_ride}


def seglist(spec):
    out = []
    for part in spec.split(','):
        if '-' in part:
            a, b = part.split('-'); out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def run_segment(policy, k, start, outdir, do_poke, P=None, tick=8000):
    P = P or POLICIES[policy]
    n = SEGFN[k]
    os.makedirs(os.path.join(ROOT, outdir), exist_ok=True)
    d = PolicyDriver(start, f'{outdir}/seg{k}', tick=tick, P=P)
    if do_poke:
        d.initial_poke(18)
    hp0 = d.last.hp
    t = time.time()
    (SEG_OVERRIDE.get(k) if (P.get('seg3') == 'ride' and k in SEG_OVERRIDE) else getattr(route_hop3, n))(d)
    if P.get('settle') and k == 5:
        d.idle(P['settle']); route_hop3.rep(d, 'settled')
    endsnap = f'{outdir}/seg{k}.snap'
    d.finish(endsnap)
    fin = d.last
    res = dict(policy=policy, seg=k, start=start, hp0=hp0, hp1=fin.hp, lost=hp0 - fin.hp, steps=d.total_steps, pulses=d.pulses,
               hops=d.hops, swipes_confirmed=d.swipes_ok, swipes_unconfirmed=d.swipes_miss,
               end=dict(wx=fin.wx, y=fin.y, st=fin.st), wall=round(time.time() - t),
               hurts=[dict(wx=h['wx'], y=h['y'], st=h['st'], hp=h['hp'], site=h['site'],
                           near=[(o['h'], o['hp'], o['dx'], o['dy']) for o in h['near']]) for h in d.hurt_list])
    json.dump(res, open(os.path.join(ROOT, outdir, f'seg{k}.json'), 'w'), indent=1)
    return res, endsnap


def main():
    a = sys.argv[1:]
    if not a or a[0] != 'run':
        print(__doc__); return
    policy, segs = a[1], seglist(a[2])
    chain = '--chain' in a
    tag = a[a.index('--tag') + 1] if '--tag' in a else policy
    outdir = f'{OUT}/{tag}' + ('_chain' if chain else '')
    prev = None
    for k in segs:
        if '--start' in a:
            start = a[a.index('--start') + 1]
        elif chain:
            start = START if k == 1 else (prev or f'{outdir}/seg{k-1}.snap')
        else:
            start = START if k == 1 else POKED % SEGFN[k - 1]
        PP = dict(POLICIES[policy])
        if '--trace' in a: PP['trace'] = True
        if '--set' in a: PP.update(json.loads(a[a.index('--set') + 1]))
        res, prev = run_segment(policy, k, start, outdir, do_poke=('--nopoke' not in a) and ((not chain) or k == segs[0]), P=PP)
        print(json.dumps(res), flush=True)
        if res['hp1'] <= 0:
            print('hero dead'); break


if __name__ == '__main__':
    main()
