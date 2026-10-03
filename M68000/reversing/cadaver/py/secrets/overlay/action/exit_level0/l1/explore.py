"""explore.py <in.snap> <out.snap> cmd...: scripted natural-input legs for Cadaver level 1 (92nd pass).  One invocation = one Repl session = one
snapshot reload, the discipline of lib/route_chain.py (a hold's outcome depends on the reload phase).  Everything is joystick/keyboard input: nothing poked.

Commands (one argv word each; a leg is a list of them; `run(inp, out, cmds)` is the same thing as a function):
  H<U|D|L|R>            hold until the hero bbox stalls (6 chunks) or the room changes (then +100,000 steps of the arrival block)
  G<dir>:<axis><op><n>  goto: hold `dir` in 5,000-step chunks until the bbox axis (x lead, y lead, X trail, Y trail) is >= / <= n, e.g. GR:x>=36, GU:y<=17
  W<dir>:<n>[:chunk]    trace: hold `dir` n chunks (default 10,000) printing room, bbox, z and health at each (diagnostic)
  S<n>                  run n steps
  J<dir|->[:n[:settle]] jump: hold FIRE|dir for n x 10,000 steps (default 30), release, settle (default 700,000).  The takeoff direction fixes the arc:
                        a direction added after takeoff does nothing; a jump needs a run-up gap (an adjacent takeoff does not move)
  O<icon hex>           open the object panel in front (FIRE hold) and pick that icon (7/4 operate, 2 take, 9 drink); runs 200,000 steps after
  C<oid>                select rucksack item <oid> via the Return grid (RIGHT-pulse count searched on forks); prints its icons
  K<icon hex>           pick that icon of the open item panel (d = SELECT, c = APPLY to the object in front)
  F                     FIRE hold with nothing in front (casts the selected scroll)
  Z<door hex>[:lane[:chunk]]  align with the portal of that door (lane = hero lead coordinate across the portal, - for the default) and hold through it, retrying up to 5 holds
                        (chunk = steps of the hold's stall test, default 20,000: a hound blocking the door needs 60,000 or more)
  M<door hex>[:chunk]   Z with the lane searched on forks (every 4 cells across the portal): first lane that changes the room with no health loss and no new poison
  X<door hex>[:lane[:wmax[:step]]]  Z preceded by a standing wait W searched on forks (first W with no health loss and a room change)
  Q                     probe (FIRE toward an object in front; cancels the panel; leaves the hero mid-jump when nothing is in front: end a leg before it)
  A<room>[:<min health>] assert the room (and health) so a leg fails loudly
  N                     assert no POISON strength is pending (2434(A5) == 0): a bite's ticks arrive later, -10 each, so health alone does not show it
  T P D B<ids> E<doors> print state / portals / placement table / variables+object bytes / door words
"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE + '/../g2')
os.environ.setdefault('ATARI_NOTRACE', '1')
from lib import *        # Repl, A5, K, goto, hold, probe, Tally, pulse, tap, pick_icon_id, open_panel, icons, portals, dump, door, live_rec, hp, zz, st, ...


def zdoor(r, c, log=print):
    parts = c[1:].split(':'); want = int(parts[0], 16); tbl = r.l(A5 + 88); n = r.w(A5 + 1162); pb = None
    for i in range(n):
        e = r.mem(tbl + 70 * i, 70); d = int.from_bytes(e[10:14], 'big'); dd = (d - 0x6d35a) // 8
        if dd == want: pb = tuple(e[0:4])
    assert pb, ('no portal', want)
    xl, yl, xt, yt = pb; room0 = r.w(ROOM)
    p = pos(r)
    if (yl - yt) < (xl - xt): axis = 'v'; d = 'U' if yl < p[1] else 'D'      # a north or south portal is wide in x and thin in y; the side is the one the hero is not on
    else: axis = 'h'; d = 'L' if xl < p[0] else 'R'
    lane = int(parts[1]) if len(parts) > 1 and parts[1] != '-' else None
    chunk = int(parts[2]) if len(parts) > 2 else 20000        # the stall test of `hold` is 6 chunks: a longer chunk waits out a blocker at the door
    if axis == 'v':
        tgt = lane if lane is not None else (xt + xl) // 2 + 3      # hero lead x (the bbox is 7 wide)
        if p[0] < tgt: goto(r, RIGHT, lambda q: q[0] >= tgt, maxn=1200)
        elif p[0] > tgt: goto(r, LEFT, lambda q: q[0] <= tgt, maxn=1200)
    else:
        tgt = lane if lane is not None else (yt + yl) // 2 + 3
        if p[1] < tgt: goto(r, DOWN, lambda q: q[1] >= tgt, maxn=1200)
        elif p[1] > tgt: goto(r, UP, lambda q: q[1] <= tgt, maxn=1200)
    log('  aligned %s portal %s %s' % (st(r), pb, d))
    for _ in range(5):
        room, p = hold(r, K[d], chunk=chunk)
        if room != room0: r.cmd('s 100000'); break
    log('%s -> %s' % (c, st(r)))


def run(inp, out, cmds, log=print, tmp=None):
    """run the commands from snapshot `inp`, write the final state to `out`; returns the final (room, bbox, health, poison strength)"""
    inp, out = os.path.abspath(inp), os.path.abspath(out); tmp = tmp or out + '.'
    r = Repl(inp)
    log('start %s xp %d' % (st(r), r.l(A5 + 1192)))
    for c in cmds:
        if c[0] == 'H':
            room0 = r.w(ROOM); room, p = hold(r, K[c[1]])
            if room != room0: r.cmd('s 100000')
            log('%s -> %s' % (c, st(r)))
        elif c[0] == 'S': r.cmd('s %d' % int(c[1:])); log('%s %s' % (c, st(r)))
        elif c == 'P': portals(r)
        elif c == 'D': dump(r)
        elif c == 'T': log('%s ruck %s' % (st(r), slot_map(r)))
        elif c[0] == 'O':
            t = Tally(r); open_panel(r, t); pick_icon_id(r, t, int(c[1:], 16)); t.run(200000); log('%s %s' % (c, st(r)))
        elif c[0] == 'J':
            a = c[1:].split(':'); bits = FIRE | (K[a[0]] if a[0] != '-' else 0); n = int(a[1]) if len(a) > 1 else 30; se = int(a[2]) if len(a) > 2 else 700000
            joy(r, bits)
            for i in range(n): r.cmd('s 10000')
            joy(r, 0); r.cmd('s %d' % se); log('%s %s' % (c, st(r)))
        elif c[0] == 'W':
            d, n = c[1], int(c[3:].split(':')[0]); ch = int(c[3:].split(':')[1]) if ':' in c[3:] else 10000
            joy(r, K[d])
            for i in range(n): r.cmd('s %d' % ch); log('   %d %d %s %s %d' % (i, r.w(ROOM), pos(r), zz(r), hp(r)))
            joy(r, 0); r.cmd('s 30000'); log('%s %s' % (c, st(r)))
        elif c[0] == 'B':
            log('B vars %s' % [r.b(A5 + 2282 + i) for i in range(20)])
            for i in [int(v) for v in c[1:].split(',') if v]:
                a = live_rec(r, i); log('  obj %d rec %s' % (i, ('%x b3 %02x b15 %02x' % (a, r.b(a + 3), r.b(a + 15))) if a else None))
        elif c[0] == 'E':
            for d in c[1:].split(','): log('door %s %s' % (d, door(r, int(d, 16))))
        elif c[0] == 'C':
            oid = int(c[1:]); snap = tmp + '_c.snap'; r.snap(snap); found = None
            for k in range(0, 6):
                f = Repl(snap); tt = Tally(f); tap(f, tt, 0x1c)
                for _ in range(k): pulse(f, tt, RIGHT)
                tt.joy(FIRE); tt.run(40000); tt.joy(0); tt.run(90000)
                ok = f.w(A5 + 1236) == oid; f.close()
                if ok: found = k; break
            assert found is not None, ('item not in the Return grid', oid)
            tt = Tally(r); tap(r, tt, 0x1c)
            for _ in range(found): pulse(r, tt, RIGHT)
            tt.joy(FIRE); tt.run(40000); tt.joy(0); tt.run(90000); log('%s icons %s' % (c, icons(r)))
        elif c[0] == 'K':
            tt = Tally(r); pick_icon_id(r, tt, int(c[1:], 16)); tt.run(100000); log('%s %s sel %s' % (c, st(r), r.a5(1262, 2).hex()))
        elif c == 'F':
            tt = Tally(r); tt.joy(FIRE); tt.run(40000); tt.joy(0); tt.run(70000); r.cmd('s 300000'); log('%s %s xp %d' % (c, st(r), r.l(A5 + 1192)))
        elif c[0] == 'Z': zdoor(r, c, log)
        elif c[0] == 'M':
            # M<door hex>[:chunk]: try lanes across the portal (every 4 cells) on forks; keep the first that changes the room with no health loss and no poison taken
            a = c[1:].split(':'); door_ = a[0]; chunk = a[1] if len(a) > 1 else '20000'
            snap = tmp + '_m.snap'; r.snap(snap); h0 = hp(r); p0 = r.b(A5 + 2434); room0 = r.w(ROOM)
            tbl = r.l(A5 + 88); n = r.w(A5 + 1162); pb = None
            for i in range(n):
                e = r.mem(tbl + 70 * i, 70); d_ = int.from_bytes(e[10:14], 'big')
                if (d_ - 0x6d35a) // 8 == int(door_, 16): pb = tuple(e[0:4])
            assert pb, ('no portal', door_); xl, yl, xt, yt = pb
            vertical = (yl - yt) < (xl - xt); lo, hi = (xt + 2, xl) if vertical else (yt + 2, yl)
            lanes = list(range((lo + hi) // 2, hi + 1, 4)) + list(range((lo + hi) // 2 - 4, lo - 1, -4)); good = None
            for lane in lanes:
                f = Repl(snap)
                try: zdoor(f, 'Z%s:%d:%s' % (door_, lane, chunk), lambda s_: None)
                except AssertionError: f.close(); continue
                ok = hp(f) >= h0 and f.b(A5 + 2434) == p0 and f.w(ROOM) != room0
                log('  lane %d -> room %d health %d%s' % (lane, f.w(ROOM), hp(f), '  <- taken' if ok else ''))
                if ok: f.snap(tmp + '_mend.snap'); f.close(); good = lane; break
                f.close()
            assert good is not None, 'no lane crosses'
            r.close(); r = Repl(tmp + '_mend.snap'); log('%s lane %d %s' % (c, good, st(r)))
        elif c[0] == 'X':
            a = c[1:].split(':'); lane = a[1] if len(a) > 1 and a[1] != '-' else None
            wmax = int(a[2]) if len(a) > 2 else 3000000; step = int(a[3]) if len(a) > 3 else 100000
            snap = tmp + '_x.snap'; r.snap(snap); h0 = hp(r); room0 = r.w(ROOM); good = None
            for W in range(0, wmax + 1, step):
                f = Repl(snap)
                if W: f.cmd('s %d' % W)
                try: zdoor(f, 'Z' + a[0] + (':' + lane if lane else ''), lambda s: None)
                except AssertionError as e: f.close(); continue
                ok = hp(f) >= h0 and f.w(ROOM) != room0
                log('  W %8d -> room %d health %d%s' % (W, f.w(ROOM), hp(f), '  <- taken' if ok else ''))
                if ok: f.snap(tmp + '_xend.snap'); f.close(); good = W; break
                f.close()
            assert good is not None, 'no clear wait'
            r.close(); r = Repl(tmp + '_xend.snap'); log('%s W %d %s' % (c, good, st(r)))
        elif c == 'Q': log('probe %s' % (probe(r),))
        elif c[0] == 'G':
            d, cond = c[1], c[3:]
            ax = {'x': 0, 'y': 1, 'X': 2, 'Y': 3}[cond[0]]; op = '>=' if '>=' in cond else '<='; n = int(cond.split(op)[1])
            f = (lambda p, ax=ax, n=n: p[ax] >= n) if op == '>=' else (lambda p, ax=ax, n=n: p[ax] <= n)
            goto(r, K[d], f, maxn=1200); log('%s -> %s' % (c, st(r)))
        elif c == 'N': assert r.b(A5 + 2434) == 0, ('poison pending', r.b(A5 + 2434))
        elif c[0] == 'A':
            a = c[1:].split(':'); room = r.w(ROOM)
            assert room == int(a[0]), ('room', room, c, st(r))
            if len(a) > 1: assert hp(r) >= int(a[1]), ('health', hp(r), c)
        else:
            raise SystemExit('unknown command ' + c)
    res = (r.w(ROOM), pos(r), hp(r), r.b(A5 + 2434))      # 2434(A5) = poison strength: non-zero means a POISON bite whose ticks (-strength each) are still to come
    r.snap(out); r.close()
    return res


if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2], sys.argv[3:])
