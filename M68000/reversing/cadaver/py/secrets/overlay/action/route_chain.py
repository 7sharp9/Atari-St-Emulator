"""route_chain.py: shared harness of the 87th-pass route scripts (route_room16_to_flask392.py, route_room23_to_item455.py, route_heal_chain.py).
`Route` runs natural-input legs with a reload (snapshot, close, reopen) after each one, because `Repl.__init__` runs `s 1` and a hold's outcome depends on that phase; checkpoints go to the OUTDIR given
to it and nowhere else.  The repo root comes from M68000_ROOT or the nearest ancestor holding reversing/cadaver/py/secrets."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_HERE = os.path.dirname(os.path.abspath(__file__))


def _root():
    """M68000_ROOT, else the nearest ancestor holding reversing/cadaver (works from scratchpad/ and from overlay/action/)"""
    if os.environ.get('M68000_ROOT'): return os.environ['M68000_ROOT']
    d = _HERE
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, 'reversing', 'cadaver', 'py', 'secrets')): return d
        d = os.path.dirname(d)
    raise SystemExit('set M68000_ROOT')


_ROOT = _root(); os.environ['M68000_ROOT'] = _ROOT
sys.path.insert(0, _ROOT + '/reversing/cadaver/py/secrets/overlay/action')
from route_lib import *

K = {'U': UP, 'D': DOWN, 'L': LEFT, 'R': RIGHT}


class Route:
    def __init__(self, outdir, start):
        self.d = os.path.abspath(outdir); os.makedirs(self.d, exist_ok=True)
        self.n = 0; self.r = Repl(start); self.ledger = []

    def reopen(self, name):
        self.n += 1
        path = os.path.join(self.d, 'ck_%02d_%s.snap' % (self.n, name))
        self.r.snap(path); self.r.close(); self.r = Repl(path)

    def leg(self, name, f, expect_room=None):
        r = self.r; h0 = r.w(HEALTH); res = f(r)
        room = r.w(ROOM); h1 = r.w(HEALTH)
        print('%-16s room %2d pos %s health %d -> %d%s' % (name, room, pos(r), h0, h1, '  ' + str(res) if res is not None else ''), flush=True)
        self.ledger.append((name, room, pos(r), h0, h1))
        if expect_room is not None: assert room == expect_room, (name, room, expect_room)
        self.reopen(name)

    def H(self, name, mv, room=None): self.leg(name, lambda r: hold(r, K[mv]), room)
    def G(self, name, mv, cond, room=None): self.leg(name, lambda r: goto(r, K[mv], cond), room)
    def S(self, name, steps): self.leg(name, lambda r: r.cmd('s %d' % steps) and None)

    def settle_on_change(self, name, f, expect_room=None):
        """a hold that may cross a door: run it, then 100000 steps of the arrival block if the room changed"""
        def g(r):
            room0 = r.w(ROOM); res = f(r)
            if r.w(ROOM) != room0: r.cmd('s 100000')
            return res
        self.leg(name, g, expect_room)


