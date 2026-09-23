"""pause.py - prove $3b274 is the PAUSE flag (cmd 14/6, $1f428).

From game_start.snap: click the pause icon, then run 40 frames and capture the frame counter
$3c4c8, the entity array and the side records at each frame. While $3b274 = 1 the main loop skips
$12f84 and $db4c ($b7b2), so the counter and the whole entity array must be frozen. Then click
the icon again and check that the counter runs again.
Writes systems/pause_on.snap (paused) and prints the counts.
"""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from popcfg_local import WORK, OUT  # noqa: sets sys.path for popdrive/popmem
from popdrive import Game, plan_icon, run
from popmem import ram, w

N = 40


def dumps():
    # 'r' after each dump: its non-hex output separates the blobs
    return ['m 3c4c8 2', 'r', 'm 3b274 2', 'r', 'm 3b226 32', 'r', 'm 3b278 %d' % (0x16 * 0xd3), 'r']


def parse(out):
    """-> list of byte blobs, one per 'm' command, in order."""
    blobs, cur = [], None
    for line in out.splitlines():
        t = line.split()
        if t and all(len(x) == 2 and re.fullmatch('[0-9a-f]{2}', x) for x in t):
            cur = (cur or bytearray()) + bytes(int(x, 16) for x in t)
        elif cur is not None:
            blobs.append(bytes(cur)); cur = None
    if cur is not None: blobs.append(bytes(cur))
    return blobs


def main():
    src = os.path.join(WORK, 'game_start.snap')
    g = Game(ram(src))
    lines, info = plan_icon(g, 'pause')
    on = os.path.join(OUT, 'pause_on.snap')
    run(src, lines, on)
    m = ram(on)
    print('after click: $3b274 =', w(m, 0x3b274), 'frame', w(m, 0x3c4c8), 'click at', info['point'])
    L = []
    for _ in range(N):
        L += ['s 120000'] + dumps()
    g2 = Game(m)
    L2, _ = plan_icon(g2, 'pause')
    L += L2
    for _ in range(5):
        L += ['s 120000'] + dumps()
    out = run(on, L, os.path.join(OUT, 'pause_off.snap'))
    b = parse(out)
    assert len(b) == 4 * (N + 5), len(b)
    fr = [b[4 * i] for i in range(N + 5)]
    ents = [b[4 * i + 3] for i in range(N + 5)]
    sides = [b[4 * i + 2] for i in range(N + 5)]
    flag = [b[4 * i + 1] for i in range(N + 5)]
    frozen = sum(1 for i in range(N) if fr[i] == fr[0] and ents[i] == ents[0] and sides[i] == sides[0]
                 and flag[i] == b'\0\1')
    print('paused frames with counter, 211 entity records and side records unchanged: %d/%d' % (frozen, N))
    print('counter while paused:', int.from_bytes(fr[0], 'big'),
          'after unpause:', [int.from_bytes(x, 'big') for x in fr[N:]],
          '$3b274 after unpause:', int.from_bytes(flag[-1], 'big'))


if __name__ == '__main__':
    main()
