"""trek.py <snap> <target room> [maxdepth] [budget s] [--probe]: natural-input walk between rooms of level 0.

Breadth-first search over joystick holds (U/D/L/R) from a snapshot.  A hold runs until the hero bbox stops changing (a wall, the stall one step short of an object) or the room id
`1166(A5)` changes (the hold stops one chunk after the transition so the arrival position is the door's own landing point).  Each node is a snapshot under
scratchpad/cadaver/secrets_out/action/trek/; the key is (room, bbox).  The goal is `1166(A5) == target`.  Prints the path, the room, bbox and health `1174(A5)` of every node.

    python reversing/cadaver/py/secrets/overlay/action/trek.py scratchpad/cadaver/secrets_out/action/lever_after.snap 7"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drv import *
TK = OUT + 'trek/'
os.makedirs(TK, exist_ok=True)
NAMES = {UP: 'U', DOWN: 'D', LEFT: 'L', RIGHT: 'R'}
ROOM, HEALTH = A5 + 1166, A5 + 1174


def hold(r, bits, max_steps=1500000, chunk=20000):
    """hold `bits` until the bbox is unchanged for 6 chunks (the hold starts moving ~40,000 steps after the press, one cell per ~10,000) or the room changes; returns (room, bbox)"""
    room0 = r.w(ROOM); joy(r, bits); last = pos(r); n = 0; stall = 0
    while n < max_steps:
        r.cmd('s %d' % chunk); n += chunk
        if r.w(ROOM) != room0:
            r.cmd('s %d' % chunk); break
        p = pos(r)
        stall = stall + 1 if p == last else 0
        if stall >= 6: break
        last = p
    joy(r, 0); r.cmd('s 30000')
    return r.w(ROOM), pos(r)


def bfs(snap, target, maxdepth=8, budget=1800, seen=None, do_probe=False):
    seen = {} if seen is None else seen
    queue = [(snap, '')]; t0 = time.time(); n = 0
    while queue and time.time() - t0 < budget:
        s, path = queue.pop(0)
        if len(path) >= maxdepth: continue
        for mv in (UP, DOWN, LEFT, RIGHT):
            r = Repl(s)
            room, p = hold(r, mv)
            key = (room, p)
            if key in seen: r.close(); continue
            seen[key] = path + NAMES[mv]; n += 1
            s2 = TK + 'n%d.snap' % n; r.snap(s2); hp = r.w(HEALTH)
            res = probe(r) if do_probe else None; r.close()
            print('  %-10s room %2d pos %s health %d%s' % (path + NAMES[mv], room, p, hp, ' probe %s %s' % (res[0], res[1]) if res else ''), flush=True)
            if room == target: return path + NAMES[mv], s2
            queue.append((s2, path + NAMES[mv]))
    return None


if __name__ == '__main__':
    snap, target = sys.argv[1], int(sys.argv[2])
    md = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    print(bfs(snap, target, md, int(sys.argv[4]) if len(sys.argv) > 4 else 1800, do_probe='--probe' in sys.argv))
