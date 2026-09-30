"""select_track.py [cursor ...] - drive the SELECT TRACK screen to a chosen cursor position, confirm with fire, and read
what the race-start initialiser $be40 does.

Start: data/select_live.snap (SELECT TRACK loop of $19164, loop head $193b6, player slot 1 = joystick 0; made by
prerace.py).  The cursor -4(A6) (0..15) moves +-1 per loop iteration while joystick right/left is held (bit 8/4);
$19164 returns cursor>>1 as the track index and stores cursor>>2 into -3954(A4)[0..2] (starting wrenches).
For each cursor c: hold right until -4(A6) == c, release, hold fire until the loop exits, run to $c156 (first cap
write of $be40), read T = 8(A6) of $be40, wrenches, drone flags, R, then step through the cap writes and read caps
and dividers.  Prints one line per cursor.

    cd M68000 && python3 reversing/supersprint/py/ai_econ/select_track.py 0 2 4 6 8 10 12 14
"""
from aiutil import *

LOOP = 0x193b6


def run(c, poke_R=None):
    r = Repl2(os.path.join(DATA, 'select_live.snap'))
    out, regs = r.cmd('')
    A6 = regs['A6']
    cur = 0
    if c:
        r.cmd('kbd fe 08')
        r.cmd('s 8000')
        for _ in range(40):
            r.cmd('bp %x 300000' % LOOP)
            cur = r.words(A6 - 4, 1)[0]
            if cur >= c - 1:          # release one iteration early: the key-up lands a poll later
                break
        r.cmd('kbd fe 00')
        r.cmd('s 8000')
        r.cmd('bp %x 300000' % LOOP)
        cur = r.words(A6 - 4, 1)[0]
    r.cmd('kbd fe 80')
    if poke_R is not None:
        r.cmd('w %x %04x0000' % (A4 - 1748, poke_R & 0xFFFF))
    out, regs = r.cmd('bpc c156 1 12000000')
    hit = any('hit' in l for l in out)
    A6b = regs['A6']
    T = r.words(A6b + 8, 1)[0]
    wr = r.a4w(-3954, 3)
    drone = r.a4w(-3914, 4)
    R = r.a4w(-1748, 1)[0]
    out, regs = r.cmd('bpc c226 3 100000')
    ok226 = any('hit' in l for l in out)
    r.cmd('s 300')
    caps = r.a4w(-3874, 4)
    div = r.a4w(-3882, 4)
    r.close()
    return cur, hit and ok226, T, wr, drone, R, caps, div


if __name__ == '__main__':
    cs = [int(x) for x in sys.argv[1:]] or [0]
    for c in cs:
        cur, hit, T, wr, drone, R, caps, div = run(c)
        pred = [60 - 4 * T + 4 * i + R if drone[i] else None for i in range(4)]
        print('cursor %2d (settled at %d) valid=%s: T=%d wrenches=%s R=%d drone=%s caps=%s predicted=%s div=%s' % (c, cur, hit, T, wr, R, drone, caps, pred, div), flush=True)
