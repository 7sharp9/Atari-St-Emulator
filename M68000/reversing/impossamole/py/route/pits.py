"""Segment 6 (four water pits) with rollout search over the take-off delay.

    uv run python reversing/impossamole/py/route/pits.py sweep <snap> <pit> <w0> <w1> <wstep> [nproc]     # idle W frames, cross, print outcome per W
    uv run python reversing/impossamole/py/route/pits.py play <snap> <out_prefix> <pit>:<W> [<pit>:<W> ...]  # run the chosen plan, chain, save snapshots

A pit is (take-off wx, right-edge wx): the hero walks to the take-off spot, idles W frames (24,000 steps each, the game's frame in gameplay),
then `cross` hops right until it is grounded past the right edge. Health is not poked here: `lost` is the real cost.
"""
import sys, os, json
from multiprocessing import Pool
sys.path.insert(0, 'reversing/impossamole/py/route')
from route_driver import *
B = 'scratchpad/impossamole/agents/unpoked/pits_work'
FRAME = 24000
# pit -> (take-off wx, right edge wx (first solid wx past the pit))
PITS = {1: (7244, 7328), 2: (7372, 7520), 3: (7562, 7616), 4: (7660, 7808)}
NOCROC = {3}   # pit 3 sweeps the take-off offset 0..30 px: 0-24 lose nothing


def grounded(s):
    return s.st in (0, 1)


SHUT = set(range(10, 14)) | {18, 19} | set(range(30, 45))   # entries of $22132/$220d6 whose frame is 144/140 (jaws shut, `$e5fe` carries the hero)
CROC = 0x15d26


def croc_under(d):
    """The crocodile object the hero stands on, as (dir_right, entry, counter, shut_frames_left, wx) or None."""
    s = d.last
    best = None
    for o in d.objects():
        r = o['raw']
        if o['type'] and int.from_bytes(r[86:90], 'big') == CROC and abs(o['dx']) <= 26 and 6 <= o['dy'] <= 22:
            ent = int.from_bytes(r[26:28], 'big') // 2
            cnt = r[29]
            left = 3 - cnt
            e = ent
            if e in SHUT:
                while True:
                    e += 1
                    if e in SHUT:
                        left += 3
                    else:
                        break
            else:
                left = 0
            best = (int.from_bytes(r[22:26], 'big') == 0x22132, ent, cnt, left, o['x'] - 32 + s.cam)
    return best


OFFSET_STOP = 17    # hero left edge minus croc left edge at which the hero stops walking on the back (it falls off at about 23)


def ride_until_hop(d, min_left=5, max_frames=70, mode='turn', walk=True):
    """Standing on a crocodile: walk right along its back to OFFSET_STOP, then stand while it carries the hero until it turns
    (mode 'turn') or its jaws are about to open; returns the frames ridden."""
    for i in range(max_frames * 4):
        c = croc_under(d)
        if c is None:
            d.set_bits(0)
            return i / 4
        right, ent, cnt, left, cx = c
        if left <= min_left or (mode == 'turn' and not right):
            d.set_bits(0)
            return i / 4
        d.set_bits(RIGHT if walk and d.last.wx - cx < OFFSET_STOP else 0)
        d.step(6000)
        d.last = d.read_stable()
        if not grounded(d.last):
            d.set_bits(0)
            return i / 4
    d.set_bits(0)
    return max_frames


def cross(d, pit, max_hops=8, stop_on_loss=True, ride=True):
    take, edge = PITS[pit]
    hp0 = d.last.hp
    trace = []
    for i in range(max_hops):
        if i and ride:
            r = ride_until_hop(d)
            trace.append(('ride', r))
        ok, s = d.hop(RIGHT, why=f'pit{pit}-hop{i}', land_max=1_600_000)
        c = croc_under(d) if grounded(s) else None
        trace.append((s.wx, s.y, s.st, s.hp, c))
        if s.hp < hp0 and stop_on_loss:
            return False, trace
        if grounded(s) and s.wx >= edge - 8:
            return True, trace
    return False, trace


def walk_to(d, wx):
    return d.hold(RIGHT, until=lambda s: s.wx >= wx and grounded(s), max_steps=max(80_000, 30_000 * max(1, wx - d.last.wx)), why=f'walk {wx}')[1]


def trial(args):
    snap, pit, w = args
    d = Driver(snap, f'{B}/out/sw_p{pit}_w{w:03d}', tick=6000, hp_floor=-1)
    hp0 = d.last.hp
    take, edge = PITS[pit]
    w_arg = w
    if pit in NOCROC:      # no crocodile in this pit: W is a take-off offset in px instead of an idle delay
        take += w
        w = 0
    if d.last.wx < take:
        walk_to(d, take)
    if w:
        d.idle(w * FRAME)
    ok, trace = cross(d, pit)
    res = dict(pit=pit, w=w_arg, ok=ok, lost=hp0 - d.last.hp, trace=trace, steps=d.total_steps)
    d.close()
    return res


def sweep(snap, pit, w0, w1, ws, n):
    os.makedirs(f'{B}/out', exist_ok=True)
    with Pool(n) as p:
        for r in p.imap(trial, [(snap, pit, w) for w in range(w0, w1, ws)]):
            print(json.dumps(r), flush=True)


def play(snap, prefix, plan):
    d = Driver(snap, f'{B}/{prefix}', tick=6000, hp_floor=-1)
    hp0 = d.last.hp
    for item in plan:
        pit, w = map(int, item.split(':'))
        take, edge = PITS[pit]
        if d.last.wx < take:
            walk_to(d, take)
        if w:
            d.idle(w * FRAME)
        ok, trace = cross(d, pit, stop_on_loss=False)
        print(f'pit {pit} W={w}: ok={ok} trace={trace} hp={d.last.hp}', flush=True)
        d.snap(f'{B}/{prefix}_after_pit{pit}.snap')
    d.finish(f'{B}/{prefix}_end.snap')
    print('hp lost', hp0 - d.last.hp)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'sweep':
        sweep(a[1], int(a[2]), int(a[3]), int(a[4]), int(a[5]), int(a[6]) if len(a) > 6 else 3)
    elif a[0] == 'play':
        play(a[1], a[2], a[3:])
