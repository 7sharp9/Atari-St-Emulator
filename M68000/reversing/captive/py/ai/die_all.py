"""The DIE item's face ($1207c) against every coded door of a base, compared with the door's own corner order.

    uv run python -I reversing/captive/py/ai/die_all.py [snap] [calls]
    (default scratchpad/captive/agents/ai/req4.snap: the D0 = 1 base, whose door list holds three kind-2 doors)

For each entry of the coded-door list (fed 2330(A6) = $1bee8) and each open orthogonal neighbour of its cell, labelled
pokes put the party on the neighbour (x, y, facing = fed 26/28/30(A6)) facing the door, and set the door state's low
nibble to the first k corners of its own order (k = 0..3; the order is the byte $e358[code], read from RAM). The game
runs 120,000 steps (the view refreshes the cell-ahead copy 15408(A6)), then $1207c is called `calls` times with A0 at
a scratch record. Expected: every face = '0' + the next corner (c = 2*bottom + right). Control: the same position
facing each other way (no door ahead) must give only the random faces $20..$2b.
"""
import os
import sys
from collections import Counter


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cap import R, W, srv  # noqa: E402

A6 = 0x1b5ce
DOORS = A6 + 2330
POSX, POSY, FACE = A6 + 26, A6 + 28, A6 + 30
CELLAHEAD = A6 + 15408
MAP = A6 + 9242
STEP = {0: (0, -1), 1: (-1, 0), 2: (0, 1), 3: (1, 0)}  # facing -> map step, measured: the tile at 15408(A6) per facing


def corners(b):
    """Corner order encoded in a $e358 byte, as $120f4 reads it: k-th corner at ror 2, 4, 6, then 0 (x8 & 7)."""
    return [(b >> sh) & 3 for sh in (2, 4, 6, 0)]


def main():
    snap = sys.argv[1] if len(sys.argv) > 1 else os.path.join(W, 'agents', 'ai', 'req4.snap')
    calls = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    s = srv(snap)
    base = s('fork')['id']
    scratch = s.reg('a7') - 0x400
    tab = s.read(0xe358, 24)
    grid = s.read(MAP, 2048)
    hint_ok = hint_bad = ctrl_ok = ctrl_bad = 0
    lst = s.read(DOORS, 32)
    listed = {(lst[4 * i], lst[4 * i + 1]) for i in range(8) if any(lst[4 * i:4 * i + 4])}
    for i in range(8):
        x, y, st = lst[4 * i], lst[4 * i + 1], int.from_bytes(lst[4 * i + 2:4 * i + 4], 'big')
        if not (x or y or st):
            continue
        code = (st >> 4) & 0x1f
        order = corners(tab[code])
        print(f'door ({x},{y}) tile ${grid[y * 64 + x]:02x} state ${st:04x} code {code} order {order}')
        for f, (sx, sy) in STEP.items():
            px, py = x - sx, y - sy
            if not (0 <= px < 64 and 0 <= py < 32) or grid[py * 64 + px] <= 0x1a:
                continue
            for face in range(4):
                for k in range(4):
                    s('restore', id=base)
                    s('poke', addr=POSX, width=2, value=px)
                    s('poke', addr=POSY, width=2, value=py)
                    s('poke', addr=FACE, width=2, value=face)
                    nib = 0
                    for c in order[:k]:
                        nib |= 1 << c
                    s('poke', addr=DOORS + 4 * i + 2, width=2, value=(st & 0x1f0) | nib)
                    s('step', n=120000)
                    ahead = s.read(CELLAHEAD, 1)[0]
                    s.sp = None
                    t = Counter()
                    for _ in range(calls):
                        s('poke', addr=scratch, width=4, value=0)
                        s.call(0x1207c, a0=scratch)
                        t[s.read(scratch + 3, 1)[0]] += 1
                    ax, ay = px + STEP[face][0], py + STEP[face][1]
                    exp = grid[ay * 64 + ax] if 0 <= ax < 64 and 0 <= ay < 32 else 0
                    if ahead != exp:
                        print(f'  facing map mismatch: ahead ${ahead:02x}, map ${exp:02x} at ({ax},{ay})')
                    if (ax, ay) in listed and face != f:
                        continue  # another listed door ahead: neither hint nor control
                    if face == f:
                        good = t[0x30 + order[k]]
                        hint_ok += good
                        hint_bad += calls - good
                    else:
                        good = sum(v for c, v in t.items() if 0x20 <= c <= 0x2b)
                        ctrl_ok += good
                        ctrl_bad += calls - good
                    if k == 0 or face == f:
                        print(f'  from ({px},{py}) facing {face}{" (door)" if face == f else ""} pressed {k} '
                              f'ahead ${ahead:02x}:', ' '.join(f'${c:02x}x{v}' for c, v in sorted(t.items())))
    print(f'hint: next corner shown {hint_ok}/{hint_ok + hint_bad}; control: random face {ctrl_ok}/{ctrl_ok + ctrl_bad}')
    s.close()


main()
