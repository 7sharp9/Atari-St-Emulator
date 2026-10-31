"""The hidden mana hooks, live: command 14 subs 9 and 10 of `cmd_misc` ($1f0fa) from F6/F7 in paint-map mode
(mechanics.md 7, graphics.md "Scrolling").

    uv run python reversing/populous/py/hooks/paint_mana.py [hold_steps]      (from M68000/)

Builds $POP_WORK/hooks/paint1.snap from game_start.snap through the UI (GAME SETUP icon, CUSTOM GAME, PAINT MAP,
OK), then from that one state runs six trials of the same budget: no key (control), F6, F7, shift+F6, shift+F7, and
F6 with paint mode poked off (the second control). Each trial queues the make, runs `hold` steps, queues the break and
runs `hold` more. Every arrival at a sub-9/10 entry ($1fabc, $1fb16) is stopped on: the side's mana long and the
arg word 10(A6) are read there and again at the dispatcher's exit $1fbf2, and the change is checked against the
model (arg 0: 2*m + 500 while m < 100000, else unchanged; arg != 0: m / 2). Any arrival at sub 15 ($1fbbe) is
counted too.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from popcfg import R, WORK, DISK  # noqa: E402
sys.path.insert(0, os.path.join(R, 'tools'))
from stclient import StServer  # noqa: E402

MOUSE = 0x24748
PAINT, CUSTOM = 0x3b276, 0x21d5e
MANA = {9: 0x3b232, 10: 0x3b242}          # side 0, side 1 (side record +12, long)
ENTRY = {0x1fabc: 9, 0x1fb16: 10}
SUB15, EXIT = 0x1fbbe, 0x1fbf2
FRAME = 120000                             # steps, above one game frame

# (x, y) of each click: the GAME SETUP icon (popdrive.icon_point), then the item squares (x+16..x+24, y+16..y+24
# of the $22286 records: CUSTOM GAME item 10 at (152,76), PAINT MAP item 4 at (152,46)), then OK (32..80, 176..192).
CLICKS = [('game_setup', (304, 176)), ('custom', (172, 96)), ('paint_map', (172, 66)), ('ok', (56, 184))]


def w(s, a):
    return struct.unpack('>h', s.read(a, 2))[0]


def l(s, a):
    return struct.unpack('>i', s.read(a, 4))[0]


def click(s, x, y):
    px, py = w(s, MOUSE), w(s, MOUSE + 2)
    dx, dy = x - px, y - py
    while dx or dy:
        sx, sy = max(-127, min(127, dx)), max(-127, min(127, dy))
        s('mouse', action='move', dx=sx, dy=sy)
        dx -= sx; dy -= sy
    s('step', n=2 * FRAME)
    s('mouse', action='down', button='l')
    s('step', n=2 * FRAME)
    s('mouse', action='up', button='l')
    s('step', n=5 * FRAME)


def build(s, out):
    s('load', snapshot=os.path.join(WORK, 'game_start.snap'), disk=DISK)
    for name, (x, y) in CLICKS:
        click(s, x, y)
        print(f'  {name:10s} paint={w(s, PAINT)} custom={w(s, CUSTOM)} mouse=({w(s, MOUSE)},{w(s, MOUSE + 2)})')
    s('step', n=5 * FRAME)
    if w(s, PAINT) != 1 or w(s, CUSTOM) != -1:
        sys.exit('paint-map mode not reached')
    s('save', path=out)


def model(sub, arg, m):
    if arg:
        return int(m / 2)                  # $206e6 signed long divide, truncating
    return 2 * m + 500 if m < 100000 else m


def run_window(s, steps, calls):
    left = steps
    while left > 0:
        r = s('run', max_steps=left, until_pc=[*ENTRY, SUB15])
        left -= r['steps']
        if r['reason'] != 'until':
            return
        pc = int(r['pc'].lstrip('$'), 16)
        if pc == SUB15:
            calls.append(('sub15', None, None, None, None))
            continue
        sub = ENTRY[pc]
        a6 = s.reg('a6')
        arg = w(s, a6 + 10)
        m0 = l(s, MANA[sub])
        r = s('run', max_steps=10000, until_pc=EXIT)
        left -= r['steps']
        m1 = l(s, MANA[sub])
        calls.append((sub, arg, m0, m1, model(sub, arg, m0)))


def trial(s, fork, keys, hold, poke_off=False):
    s('restore', id=fork)
    if poke_off:
        s('poke', addr=PAINT, width=2, value=0)
    before = (l(s, MANA[9]), l(s, MANA[10]))
    calls = []
    makes, breaks = keys
    if makes:
        s('kbd', bytes=makes)
    run_window(s, hold, calls)
    if breaks:
        s('kbd', bytes=breaks)
    run_window(s, hold, calls)
    after = (l(s, MANA[9]), l(s, MANA[10]))
    return before, after, calls


def main():
    hold = int(sys.argv[1]) if len(sys.argv) > 1 else 5 * FRAME
    out = os.path.join(WORK, 'hooks', 'paint1.snap')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    s = StServer(R)
    print('building', out)
    build(s, out)
    fork = s('fork')['id']
    F6, F7, SH = 0x40, 0x41, 0x2a
    trials = [
        ('none', ([], []), False),
        ('F6', ([F6], [F6 | 0x80]), False),
        ('F7', ([F7], [F7 | 0x80]), False),
        ('shift+F6', ([SH, F6], [F6 | 0x80, SH | 0x80]), False),
        ('shift+F7', ([SH, F7], [F7 | 0x80, SH | 0x80]), False),
        ('F6, paint off (poke)', ([F6], [F6 | 0x80]), True),
    ]
    total = ok = 0
    for name, keys, off in trials:
        before, after, calls = trial(s, fork, keys, hold, off)
        n9 = sum(1 for c in calls if c[0] == 9)
        n10 = sum(1 for c in calls if c[0] == 10)
        n15 = sum(1 for c in calls if c[0] == 'sub15')
        good = sum(1 for c in calls if c[0] in (9, 10) and c[3] == c[4])
        total += n9 + n10; ok += good
        print(f'{name:22s} mana {before} -> {after}  sub9 {n9} sub10 {n10} sub15 {n15}  model {good}/{n9 + n10}')
        for c in calls:
            print('    ', c)
    print(f'calls matching the model: {ok}/{total}')
    s.close()


if __name__ == '__main__':
    main()
