"""The `$b9fa` "CHEAT" branch of the scroll-key switch (graphics.md "Scrolling") driven with real input.

    uv run python reversing/populous/py/hooks/star_key.py [hold_steps]      (from M68000/)

Scan code $66 is keypad `*`. The branch tests `$3c518/$3c51c`, which the VBL (`$16c8e`, `$16cd2`) refreshes from the
pointer while a button latch is armed, so with no click pending it is the live pointer. From game_start.snap: click the
query icon, move the pointer to (316,15) or, as the control, to (200,100), press and release keypad `*`. Counted: `$b9fa`
(entered), `$ba2c` (the guard passed: prints "CHEAT" at (0,10)), `$1eea0` (`cmd_misc` called), `$1fbbe` (sub 15), and the
CPU writes to the human side's command record and to `$3c4e4`, with their PCs.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from popcfg import R, WORK, DISK  # noqa: E402
from popdrive import icon_point  # noqa: E402
sys.path.insert(0, os.path.join(R, 'tools'))
from stclient import StServer  # noqa: E402
from paint_mana import click, w, MOUSE, FRAME  # noqa: E402

REC, HUMAN, UI_MODE, HOOK = 0x21e0c, 0x3affe, 0x21d50, 0x3c4e4
SITES = {0xb9fa: 'b9fa', 0xba2c: 'guard_passed', 0x1eea0: 'cmd_misc', 0x1fbbe: 'sub15'}


def move_to(s, x, y):
    dx, dy = x - w(s, MOUSE), y - w(s, MOUSE + 2)
    while dx or dy:
        sx, sy = max(-127, min(127, dx)), max(-127, min(127, dy))
        s('mouse', action='move', dx=sx, dy=sy)
        dx -= sx; dy -= sy
    s('step', n=2 * FRAME)


def main():
    hold = int(sys.argv[1]) if len(sys.argv) > 1 else 3 * FRAME
    s = StServer(R)
    s('load', snapshot=os.path.join(WORK, 'game_start.snap'), disk=DISK)
    click(s, *icon_point('ui_query'))
    print(f'ui_mode ${w(s, UI_MODE):x} (bit 0 = query)')
    side = w(s, HUMAN)
    rec = REC + 0x2e * side
    fork = s('fork')['id']
    s('watch_add', lo=rec, hi=rec + 2, kind='w', source='cpu')
    s('watch_add', lo=HOOK, hi=HOOK + 1, kind='w', source='cpu')
    for name, (x, y) in [('pointer (316,15)', (316, 15)), ('control (200,100)', (200, 100))]:
        s('restore', id=fork)
        move_to(s, x, y)
        s('watch_events')
        latch = (w(s, 0x3c518), w(s, 0x3c51c))
        s('kbd', bytes=[0x66])
        h1 = s('hits', steps=hold, addrs=list(SITES))
        s('kbd', bytes=[0xe6])
        h2 = s('hits', steps=hold, addrs=list(SITES))
        counts = {SITES[int(a['addr'].lstrip('$'), 16)]: a['count'] + b['count'] for a, b in zip(h1['hits'], h2['hits'])}
        ev = [e for x in s('watch_events') for e in x['events']]
        recw = sorted({(e['pc'], e['addr'], e['value']) for e in ev if e['addr'] != f'${HOOK:06x}'})
        hookw = sorted({(e['pc'], e['value']) for e in ev if e['addr'] == f'${HOOK:06x}'})
        print(f'{name:18s} latch {latch} {counts}\n    record writes (pc, addr, value): {recw}\n    $3c4e4 writes: {hookw}')
    s.close()


if __name__ == '__main__':
    main()
