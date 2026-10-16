"""lib17: helpers for the VAR 17 / object 70 check (promoted to overlay/body70). Natural input only unless labelled."""
import sys, os, time
from pathlib import Path
for p in [Path.cwd(), *Path.cwd().parents, Path(__file__).resolve().parent, *Path(__file__).resolve().parents]:
    if (p / 'tools' / 'rdis.py').exists(): ROOT = str(p); break
os.environ.setdefault('M68000_ROOT', ROOT); os.environ['ATARI_NOTRACE'] = '1'
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay/action')
import drv
from drv import Repl, A5, joy, pos, probe, UP, DOWN, LEFT, RIGHT, FIRE
OUT = ROOT + '/scratchpad/cadaver/body70/'
ROOM, HEALTH, VAR17 = A5 + 1166, A5 + 1174, A5 + 2299
NAMES = {UP: 'U', DOWN: 'D', LEFT: 'L', RIGHT: 'R'}
def door(r, d): return r.mem(0x6d35a + 8 * d, 8).hex()
def st(r): return 'room %d pos %s health %d VAR17 %d t7 %d door24 %s' % (r.w(ROOM), pos(r), r.w(HEALTH), r.b(VAR17), r.b(A5 + 2315), door(r, 0x24))
def hold(r, bits, max_steps=1500000, chunk=20000):
    room0 = r.w(ROOM); joy(r, bits); last = pos(r); n = 0; stall = 0
    while n < max_steps:
        r.cmd('s %d' % chunk); n += chunk
        if r.w(ROOM) != room0: r.cmd('s %d' % chunk); break
        p = pos(r); stall = stall + 1 if p == last else 0
        if stall >= 6: break
        last = p
    joy(r, 0); r.cmd('s 30000')
    return r.w(ROOM), pos(r)
def bfs(snap, goal, maxdepth=6, budget=1800, tag='bfs'):
    tk = OUT + tag + '/'; os.makedirs(tk, exist_ok=True)
    seen = {}; queue = [(snap, '')]; t0 = time.time(); n = 0
    while queue and time.time() - t0 < budget:
        s, path = queue.pop(0)
        if len(path) >= maxdepth: continue
        for mv in (UP, DOWN, LEFT, RIGHT):
            r = Repl(s); room, p = hold(r, mv)
            if (room, p) in seen: r.close(); continue
            seen[(room, p)] = path + NAMES[mv]; n += 1
            s2 = tk + 'n%d.snap' % n; r.snap(s2)
            print('  %-8s %s' % (path + NAMES[mv], st(r)), flush=True)
            ok = goal(r, room, p); r.close()
            if ok: return path + NAMES[mv], s2
            queue.append((s2, path + NAMES[mv]))
