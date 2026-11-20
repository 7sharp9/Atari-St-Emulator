"""Replay a per-tick control sequence in the real game (Virus, Atari ST) under stserver and record the trajectory.

    uv run python replay.py <controls.json> <out.json> [--snap <path>] [--cap <steps>] [--keep-going] [--ground]

controls.json: a JSON list, one entry per tick: [D0, D1, D2] as unsigned 16-bit integers (negative values are taken
mod 65536), or null to leave the game's own input for that tick. Tick k is the k-th arrival at $255d4 after the start
snapshot (k = 0 is the first, 1003 steps into fl/f1.snap). At each arrival the low words of D0, D1, D2 are overwritten
and the game runs to the next arrival.

out.json: {"snap", "ticks": [...], "complete", "end", "seconds", "steps"}; ticks[k] is the state read AT arrival k,
before tick k runs: pos, vel, att (signed words from $270b0 and $32a32), g ($32a3a), fuel ($32a2e), d (the game's own
D0, D1, D2 low words before the overwrite), step (the emulator's step counter), flags (bytes $62a5d, $62a5e, $62a62,
$62a63), lives ($32a54), and, describing tick k itself (the run from arrival k to arrival k+1): "path", the list of
marker PCs the game passed, by name (PATHS below), and "ext", the CPU writes to the ship state, attitude or fuel made
by code outside the tick routine ($255c2..$25c6d) during that run (an enemy acting on the ship). The last entry has
no path. A complete replay has len(controls) + 1 entries.

Left free flight: the replay stops at the first tick that reaches the death exit $25ad8 ("dead" in its path; that
tick's entry is the last one, so there is no state after it), or that does not return to $255d4 within --cap steps
(default 400,000; a tick is about 35,000). "end" then says {"tick", "reason"} and "complete" is false. With
--keep-going a death does not stop the replay: the controls go on being applied through the respawn (the death
tick itself runs the 50-frame explosion, so give it --cap 5000000), and "end" names the first death. Landing ("landed", "pad"), ground contact ("ground"), the
object-map test ("low", "object"), the ceiling thrust cut ("ceiling") and empty fuel ("fuel_out") are recorded in
the path and do not stop the replay.

Runs from any cwd: the repo's M68000 directory is found by walking up to the one that holds tools/rdis.py.
"""
import json
import os
import struct
import sys
import time

_d = os.path.dirname(os.path.abspath(__file__))
ROOT = _d
while not os.path.exists(os.path.join(ROOT, 'tools', 'rdis.py')):
    p = os.path.dirname(ROOT)
    if p == ROOT:
        raise SystemExit('repo root (the directory holding tools/rdis.py) not found')
    ROOT = p
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from stclient import StServer  # noqa: E402

DEFAULT_SNAP = os.path.join(ROOT, 'scratchpad', 'virus', 'fl', 'f1.snap')
# every output of the scripts in this directory (controls, replays, captures, logs) goes here, never beside them
WORK = os.environ.get('VIRUS_MPC_WORK') or os.path.join(ROOT, 'scratchpad', 'virus', 'mpc', 'gate')
os.makedirs(WORK, exist_ok=True)
TICK = 0x255d4
# marker PCs inside the tick, each the first instruction of a path only that condition reaches (tick.asm)
PATHS = {
    0x255de: 'ceiling',     # y < $c900: thrust bit cleared
    0x25a6e: 'pad',         # no thrust and latch $62a63 clear: sitting on the pad (refuel, y := $3ca)
    0x25692: 'fuel_out',    # thrust asked with fuel < 3: no thrust, fuel := 0
    0x25734: 'fire_fuel_out',
    0x2581a: 'low',         # 0 <= ground - $56 - y <= $170: object-map test
    0x25846: 'object',      # an object in the cell: bit 4 set in the map, then crash or $2004a
    0x25870: 'ground',      # ground - $56 - y < 0
    0x25c52: 'landed',      # soft contact on the pad: y := $3ca, vel := 0, latch $62a63 cleared
    0x25ad2: 'crash',
    0x25ad8: 'dead',        # also reached from $62a5d (hit by an enemy) at $257fa
    0x257f4: 'gnd',         # only with --ground: just after jsr $245b8, D1 = ground height
}
TICK_LO, TICK_HI = 0x255c2, 0x25c6d


def hx(v):
    return int(str(v).lstrip('$'), 16)


def s16(v):
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v


class Game:
    def __init__(self, snap=DEFAULT_SNAP, ground=False, quiet=True):
        self.snap = os.path.abspath(snap)
        self.s = StServer(ROOT) if not quiet else _quiet_server()
        self.ground = ground
        r = self.s('load', snapshot=self.snap)
        self.step0 = r['step']
        bps = [TICK] + [a for a, n in PATHS.items() if n != 'gnd' or ground]
        self.s('bp_set', addrs=bps)
        # writes to ship state, attitude and fuel by code outside the tick routine
        self.watches = {}
        for name, lo, hi in (('ship', 0x270b0, 0x270bb), ('att', 0x32a32, 0x32a35), ('fuel', 0x32a2e, 0x32a2f)):
            for plo, phi in ((0, TICK_LO - 1), (TICK_HI + 1, 0xffffff)):
                i = self.s('watch_add', lo=lo, hi=hi, kind='w', pc_lo=plo, pc_hi=phi, source='cpu')['id']
                self.watches[str(i)] = name

    def run_to_tick(self, cap, stop_dead=False):
        """Run until the next arrival at $255d4. Returns (reached, path, ext, gnd, steps)."""
        path = []; ext = []; gnd = None; left = cap; steps = 0
        while left > 0:
            r = self.s('run', max_steps=left)
            steps += r['steps']; left -= r['steps']
            if r.get('watch_hits'):
                for wid, n in r['watch_hits'].items():
                    if n:
                        ev = self.s('watch_events', id=int(wid))
                        for e in (ev if isinstance(ev, list) else ev.get('events', [])):
                            ext.append({'what': self.watches.get(str(wid), str(wid)), **e})
            if r['reason'] != 'breakpoint':
                return False, path, ext, gnd, steps, r['reason']
            pc = hx(r['pc'])
            if pc == TICK:
                return True, path, ext, gnd, steps, 'tick'
            name = PATHS.get(pc, f'${pc:x}')
            if name == 'gnd':
                gnd = s16(hx(self.s('regs')['d1']))
            else:
                path.append(name)
                if name == 'dead' and stop_dead:
                    return False, path, ext, gnd, steps, 'dead'
        return False, path, ext, gnd, steps, 'max_steps'

    def state(self):
        regs = self.s('regs')
        a = bytes.fromhex(self.s('read', addr=0x270b0, len=12))
        b = bytes.fromhex(self.s('read', addr=0x32a2e, len=14))      # fuel, .., att at +4, .., g at +12
        c = bytes.fromhex(self.s('read', addr=0x62a5d, len=7))       # $62a5d .. $62a63
        lives = bytes.fromhex(self.s('read', addr=0x32a54, len=2))
        pv = struct.unpack('>6h', a)
        return regs, {
            'pos': list(pv[:3]), 'vel': list(pv[3:]), 'att': list(struct.unpack('>2h', b[4:8])),
            'g': struct.unpack('>h', b[12:14])[0], 'fuel': struct.unpack('>h', b[0:2])[0],
            'd': [hx(regs[k]) & 0xffff for k in ('d0', 'd1', 'd2')],
            'step': regs['step'],
            'flags': {'hit_62a5d': c[0], 'crashing_62a5e': c[1], 'x_62a62': c[5], 'latch_62a63': c[6]},
            'lives': struct.unpack('>h', lives)[0],
        }

    def set_controls(self, regs, entry):
        for name, v in zip(('d0', 'd1', 'd2'), entry):
            self.s('set_reg', name=name, value=(hx(regs[name]) & 0xffff0000) | (int(v) & 0xffff))

    def close(self):
        try:
            self.s('shutdown')
        except SystemExit:
            pass
        try:
            self.s.close()
        except Exception:
            pass


def _quiet_server():
    """StServer with the core's stderr diagnostics (load banner, build warning) sent to a log beside this file."""
    import subprocess
    s = StServer.__new__(StServer)
    dll = os.path.join(ROOT, 'server', 'bin', 'Debug', 'net8.0', 'stserver.dll')
    s.log = open(os.path.join(WORK, 'stserver.stderr.log'), 'a')
    s.p = subprocess.Popen(['dotnet', 'exec', dll], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=s.log,
                           text=True, cwd=ROOT)
    s.seq = 0; s.sp = None
    return s


def replay(controls, snap=DEFAULT_SNAP, cap=400000, keep_going=False, ground=False, game=None):
    t0 = time.time()
    own = game is None
    g = game or Game(snap, ground=ground)
    try:
        ticks = []; end = None
        ok, path, ext, _gnd, steps, why = g.run_to_tick(cap)
        if not ok:
            raise SystemExit(f'the snapshot did not reach $255d4 within {cap} steps ({why}); path {path}')
        first_steps = steps
        for k, entry in enumerate(controls):
            regs, st = g.state()
            if entry is not None:
                g.set_controls(regs, entry)
                st['u'] = [int(v) & 0xffff for v in entry]
            else:
                st['u'] = None
            ok, path, ext, gnd, steps, why = g.run_to_tick(cap, stop_dead=not keep_going)
            # An interrupt taken at $255d4 returns to it, and stserver's breakpoint stops there a second time after
            # the handler's few steps with the tick not yet run (mpc10: 8 steps, state unchanged). The RTE restores
            # D0..D2, so the controls are still in place: run on, and count it as the same tick. The handler can take
            # 181 to 243 steps before the re-stop (scratchpad/virus/mpc/README.md "chaos/"), a real tick at least 19,900.
            while ok and steps < 2000 and not path:
                st['rearrive'] = st.get('rearrive', 0) + 1
                ok, path, ext, gnd, more, why = g.run_to_tick(cap, stop_dead=not keep_going)
                steps += more
            st['path'] = path; st['ext'] = ext; st['tick_steps'] = steps
            if ground:
                st['gnd'] = gnd
            ticks.append(st)
            if 'dead' in path and end is None:
                end = {'tick': k, 'reason': 'death exit of the tick ($25ad8), path ' + ','.join(path), 'path': path}
                if not keep_going:
                    break
            if not ok:
                end = {'tick': k, 'reason': f'no return to $255d4 within {cap} steps ({why})', 'path': path}
                break
        complete = end is None
        if ok:
            _regs, st = g.state()               # the state after the last tick run
            st['u'] = None
            ticks.append(st)
        total = ticks[-1]['step'] - g.step0
        return {'snap': g.snap, 'ticks': ticks, 'complete': complete, 'end': end,
                'first_arrival_steps': first_steps, 'steps': total, 'seconds': round(time.time() - t0, 3)}
    finally:
        if own:
            g.close()


def main():
    a = sys.argv[1:]
    def opt(name, default=None):
        if name in a:
            i = a.index(name); v = a[i + 1]; del a[i:i + 2]; return v
        return default
    def flag(name):
        if name in a:
            a.remove(name); return True
        return False
    snap = opt('--snap', DEFAULT_SNAP); cap = int(opt('--cap', '400000'))
    keep = flag('--keep-going'); ground = flag('--ground')
    if len(a) != 2:
        raise SystemExit(__doc__)
    controls = json.load(open(a[0]))
    out = replay(controls, snap, cap, keep, ground)
    with open(a[1], 'w') as f:
        json.dump(out, f)
    n = len(out['ticks'])
    print(f'{len(controls)} controls, {n} states recorded, complete={out["complete"]}, end={out["end"]}, '
          f'{out["steps"]} steps, {out["seconds"]} s')
    seen = {}
    for k, t in enumerate(out['ticks']):
        for pth in t.get('path', []):
            seen.setdefault(pth, []).append(k)
        if t.get('ext'):
            seen.setdefault('ext', []).append(k)
    for name, ks in seen.items():
        print(f'  path {name}: {len(ks)} ticks, first {ks[0]}, last {ks[-1]}')


if __name__ == '__main__':
    main()
