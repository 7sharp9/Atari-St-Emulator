"""Closed-loop canyon flight from the land screen with mouse input only (no poke).
Controller (every 30,000 steps): pointer x is never moved (steering 0); pointer y is set to climb or descend towards
target = clamp(max(req of the next two path rows) + MARGIN, LO, HI) where req(row) = ((T[o]+T[o+1])>>1)+1 is the game's
own collision height ($10c18..$10c22, T at $70400, o = the path word at $10a8a + (A6)); the right button is held
(re-pressed every iteration while the speed word $10a54 is 0) while the speed is below SPD.
Usage: fly2.py <start.snap> <outprefix> [maxsteps]     Run from M68000/."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from repl import Repl
MARGIN, LO, HI, SPD = 4, 40, 255, 20
snap, pre = sys.argv[1], sys.argv[2]; cap = int(sys.argv[3]) if len(sys.argv) > 3 else 80_000_000
r = Repl(snap)
w = lambda a: r.w(a, 2)
x, y = w(0xc6ce), w(0xc6d0); dx, dy = 187 - x, 16 - y; lines = []
while dx or dy:
    sx = max(-100, min(100, dx)); sy = max(-100, min(100, dy)); lines += [f'mouse move {sx} {sy}', 's 30000']; dx -= sx; dy -= sy
lines += ['s 100000', 'mouse down l', 's 40000', 'mouse up l']
r.cmd(*lines)
r.step(600000); total = 600000; right = False; last = None; saved = set(); toggle = 0
def save(tag):
    if tag not in saved:
        saved.add(tag); r.snap(f'{pre}_{tag}.snap'); print('saved', tag, 'at', total, flush=True)
def req(k):
    o = w(0x10a8a + 4 * (k % 64))
    t = r.mem(0x70400 + o, 2)
    return ((t[0] + t[1]) >> 1) + 1
while total < cap:
    r.step(30000); total += 30000
    cb = r.w(0x10a86, 4); f6 = w(0x110f6); idx = w(0x10a4c)
    alt = w(0x10a66); spd = w(0x10a54); yb = w(0x10a64); crash = r.w(0x10a4a, 1); bumps = r.w(0x10a4b, 1); tbl = r.w(0xd586, 4)
    k0 = idx // 4
    if cb != 0 and tbl == 0xd58a and w(0x10642) == 0:
        tgt = max(LO, min(HI, max(req(k0), req(k0 + 1)) + MARGIN))
        want = 56 + max(-56, min(56, (alt - tgt) * 2))   # y below 56 climbs, above descends
        want = max(0, min(112, want))
        if want != yb: r.cmd(f'mouse move 0 {want - yb}')
        if spd < SPD:
            if spd == 0 and right: r.cmd('mouse up r'); right = False
            if not right: r.cmd('mouse down r'); right = True
        elif right: r.cmd('mouse up r'); right = False
    st = (hex(cb), f6 >= 0x8000, crash, tbl, bumps)
    if total % 1_500_000 < 30000 or st != last:
        print(total, 'idx', idx, 'alt', alt, 'spd', spd, 'y', yb, 'bumps', bumps, 'cb', hex(cb), '110e0', hex(w(0x110e0)), 'f6', f6, 'crash', crash, 'tbl', hex(tbl), flush=True)
        last = st
    if cb == 0x11154: save('pad_seen')
    if cb == 0x11248: save('landing')
    if tbl == 0xd5e4 or (crash and total > 1500000): break
save('end')
r.close()
