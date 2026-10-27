"""A driven kill from d_ski.snap: the ski weapon fired with Space at the engaged vehicle, against a same-snapshot,
same-budget control with no key. Each of the game's own calls of the launcher `$1fc6e`, the ski shot `$208d6` and
the tumble `$141ce` is checked against shot_model.py; the run counts `$cbbe`/`$cdd0` and reads the report's counters.

usage: drive_kill.py [frames]   (default 40)
Labelled pokes, the same in both arms: the engaged vehicle `$1cdaa` moved straight ahead of the camera
(+6/+10 = camera + (0, 300); heading 0 points +y); TRAINING `$2c180` on, so the vehicle fires no missile (from
d_ski a missile ends the trip at frame 170, and a launch clears the vehicle's fire wait). The input is the IKBD
make `$39` (Space) at frame 2 and its break 30000 steps later.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gate_shot as gs  # noqa: E402
import shot_model as sm  # noqa: E402
from shot_model import Mem, l  # noqa: E402
from stclient import StServer  # noqa: E402

AHEAD = int(os.environ.get("AHEAD", "300"))
FRAME = 0x12a5e
COUNTERS = [(0x2bad8, 'ENEMY UNITS destroyed'), (0x2bada, 'MOBILE UNITS'), (0x2badc, 'ENEMY VEHICLES destroyed'),
            (0x2bade, 'MOBILE VEHICLES')]


def arm(s, fork, fire, frames):
    s('restore', id=fork)
    ok = {'launch': [0, 0], 'shot': [0, 0], 'tumble': [0, 0]}
    hits = {k: 0 for k in ('$1fc6e', '$208d6', '$141ce kill flag', '$cbbe', '$cdd0')}
    cam = (l(Mem(s.read(0, 0x48000)), sm.CAMX), l(Mem(s.read(0, 0x48000)), sm.CAMY))
    s('poke', addr=sm.VEH + 6, width=4, value=cam[0])
    s('poke', addr=sm.VEH + 10, width=4, value=cam[1] + AHEAD)
    s('poke', addr=0x2c180, width=2, value=0xffff)
    before = {a: s('peek', addr=a, width=2)[0] for a, _ in COUNTERS}
    bps = [FRAME, 0x1fc6e, 0x208d6, 0x141ce, 0xcdd0]
    s('bp_set', addrs=bps)
    n, released, steps_at_key = 0, False, None
    end = None
    while n < frames:
        r = s('run', max_steps=3000000)
        if r['reason'] != 'breakpoint':
            end = r
            break
        pc = s.reg('pc')
        if pc == FRAME:
            n += 1
            if fire and n == 2:
                s('kbd', bytes=[0x39])
                steps_at_key = s('regs')['step']
            if fire and not released and steps_at_key is not None and s('regs')['step'] - steps_at_key > 30000:
                s('kbd', bytes=[0xb9])
                released = True
            continue
        if pc == 0xcdd0:
            hits['$cdd0'] += 1
            continue
        m = Mem(s.read(0, 0x48000))
        ret = int.from_bytes(s.read(s.reg('a7'), 4), 'big')
        s('bp_clear', addrs=bps)
        if pc == 0x1fc6e:
            hits['$1fc6e'] += 1
            sm.launch(m, 0x1fc6e)
            s('run', max_steps=200000, until_pc=ret)
            key = 'launch'
        elif pc == 0x208d6:
            hits['$208d6'] += 1
            sm.ski_shot(m)
            s('run', max_steps=200000, until_pc=ret)
            key = 'shot'
        else:
            key = 'tumble'
            if sm.tumble(m):
                hits['$141ce kill flag'] += 1
                r = s('run', max_steps=200000, until_pc=[0xcbbe, ret])
                if s.reg('pc') == 0xcbbe:
                    hits['$cbbe'] += 1
                else:
                    ok[key][0] += 1  # the model expected $cbbe; count as a miss
                    s('bp_set', addrs=bps)
                    continue
                good = all(s.read(a, ln) == bytes(m.b[a:a + ln]) for a, ln in gs.OUT)
                ok[key][0] += 1
                ok[key][1] += good
                s('bp_set', addrs=bps + [ret])  # let $cbbe run (it may stop in $cdd0)
                while True:
                    r = s('run', max_steps=3000000)
                    if s.reg('pc') == 0xcdd0:
                        hits['$cdd0'] += 1
                        continue
                    break
                s('bp_clear', addrs=[ret])
                if s.reg('pc') != ret:
                    end = r
                    break
                continue
            else:
                if m.w(sm.KILL) or s.read(sm.KILL, 2) != b'\0\0':
                    hits['$141ce kill flag'] += 1
                s('run', max_steps=200000, until_pc=ret)
        good = all(s.read(a, ln) == bytes(m.b[a:a + ln]) for a, ln in gs.OUT)
        ok[key][0] += 1
        ok[key][1] += good
        s('bp_set', addrs=bps)
    s('bp_clear', addrs=bps)
    after = {a: s('peek', addr=a, width=2)[0] for a, _ in COUNTERS}
    return n, ok, hits, before, after, end, s.read(0x2bb96 + 27 * 16, 16).hex()


def main():
    frames = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    s = StServer(gs.root)
    s('load', snapshot=os.path.join(gs.WORK, 'd_ski.snap'), disk=os.path.join(gs.WORK, 'zuul067.st'))
    fork = s('fork')['id']
    fails = 0
    res = {}
    for name, fire in (('fire', True), ('control', False)):
        n, ok, hits, before, after, end, unit = arm(s, fork, fire, frames)
        res[name] = (hits, before, after)
        print(f'{name}: {n} frames{"" if end is None else f", ended early {end}"}')
        print('  calls checked against the model:', ' '.join(f'{k} {v[1]}/{v[0]}' for k, v in ok.items()))
        print('  hits:', ' '.join(f'{k}={v}' for k, v in hits.items()))
        for a, label in COUNTERS:
            b0, a0 = int(str(before[a]).lstrip('$'), 16), int(str(after[a]).lstrip('$'), 16)
            print(f'  ${a:x} {label}: {b0} -> {a0}')
        print(f'  unit 27 record: {unit}')
        fails += sum(v[0] - v[1] for v in ok.values())
    s('shutdown')
    killed = res['fire'][0]['$cbbe'] > 0 and res['control'][0]['$cbbe'] == 0
    print('PASS' if fails == 0 and killed else 'FAIL')


if __name__ == '__main__':
    main()
