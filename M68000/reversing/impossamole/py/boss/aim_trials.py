"""Negative controls for the swipe geometry model (agents/boss, 104th pass). Each trial fires REAL fire pulses at the
boss while it is at x=224 and in its open animation, ignoring what the model says, and counts $13b20 writes (hits).

    uv run python reversing/impossamole/py/boss/aim_trials.py [--weapon N] [--pulses N] [--snap S] [trial ...]

  ground_low    grounded at the step (x=172, y=152), no jump: the swipe's y box misses the boss box.
  straight_low  jump straight up at x=172 and fire while rising/falling: the swipe's x box ends before x=224.
  ground_plat   hop onto the platform (x >= 176, y=144) and fire standing: the swipe's y box misses by rows.
  hop_plat      hop over the step and fire in the air (what boss_fight.py does): the swipe overlaps the boss.
Health is poked full every iteration (labelled). The weapon is whatever $bb72 holds (2 in the snapshot) unless --weapon.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from boss_fight import Fight, FRAME, w, slot, sw


def state_open(f):
    s = f.state()
    return s, s['banim'] != 0x221f6 and s['btype'] and s['bx'] == 224


def wait_ready(f, need_ground=True, limit=4000):
    for _ in range(limit):
        f.r.run('w bb74 12120300')
        s, ok = state_open(f)
        if ok and s['fd'] == 0 and (not need_ground or s['st'] in (0, 1)):
            return s
        f.s(FRAME // 4)
    return None


def pulse(f, drift=0):
    f.pulses += 1
    f.key(drift | 0x80, FRAME + 6000)
    f.key(drift, 1)
    f.s(FRAME * 6)     # let the swipe run its 6 frames


def trial(name, snap, weapon, n):
    f = Fight(snap, weapon, True, True)
    h0 = 0
    log = []
    # position: walk right to the step
    s = f.state()
    while s['hx'] < 170:
        f.r.run('w bb74 12120300'); f.key(0x08, FRAME * 3); s = f.state()
    f.key(0, FRAME // 2)
    if name == 'ground_low':
        for _ in range(n * 6):
            if f.pulses >= n or not wait_ready(f): break
            pulse(f)
    elif name == 'straight_low':
        for _ in range(n * 6):
            if f.pulses >= n or not wait_ready(f): break
            f.key(0x01, FRAME // 4); f.key(0, FRAME)
            t = f.state()
            if t['st'] == 2 and t['fd'] == 0:
                pulse(f)
            for _ in range(60):
                if f.state()['st'] in (0, 1): break
                f.s(FRAME // 4)
    elif name in ('ground_plat', 'hop_plat'):
        for _ in range(n * 6):
            s = wait_ready(f)
            if not s or f.pulses >= n: break
            if name == 'ground_plat':
                if s['hx'] <= 172:   # hop up onto the platform first, no firing
                    f.key(0x09, FRAME // 4); f.key(0x08, FRAME * 28); f.key(0, FRAME)
                    continue
                pulse(f)
            else:
                f.jumps += 1
                f.key(0x09, FRAME // 4); f.key(0x08, 3000)
                for i in range(80):
                    t = f.state()
                    if i > 2 and t['st'] in (0, 1): break
                    if os.environ.get('DBG'): print('  air', i, t['hx'], t['hy'], t['st'], t['fd'], hex(t['banim']), t['bx'])
                    if t['st'] == 2 and t['fd'] == 0 and t['banim'] != 0x221f6 and t['bx'] == 224 and t['hx'] >= 180:
                        pulse(f, 0x08); break
                    f.s(6000)
                f.key(0, FRAME)
                for _ in range(40):
                    if f.state()['st'] in (0, 1): break
                    f.s(FRAME // 4)
                if f.state()['hx'] > 172:   # back to the step for the next hop
                    f.key(0x04, FRAME * 20); f.key(0, FRAME)
    s = f.state()
    print(f'{name:13s} weapon={f.weapon} pulses={f.pulses} hits={f.watch_hits()} boss hp {s["hp"]} steps={f.steps}')
    f.r.close()
    return f.pulses, f.watch_hits()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--snap', default='scratchpad/impossamole/pass99/boss_room.snap')
    ap.add_argument('--weapon', type=int, default=0)
    ap.add_argument('--pulses', type=int, default=8)
    ap.add_argument('trials', nargs='*', default=['ground_low', 'straight_low', 'ground_plat', 'hop_plat'])
    a = ap.parse_args()
    for t in a.trials:
        trial(t, a.snap, a.weapon, a.pulses)


if __name__ == '__main__':
    main()
