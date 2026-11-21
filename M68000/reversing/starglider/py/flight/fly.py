"""Reusable Starglider flight driver: fly the AGAV from a snapshot (default g_game1) with held keys, mouse motion and
mouse buttons, and report which named fields each input changes (same-snapshot, same-budget input/control pairs).

    cd M68000 && ATARI_NOTRACE=1 python3 reversing/starglider/py/flight/fly.py            # the input table
    cd M68000 && ATARI_NOTRACE=1 python3 reversing/starglider/py/flight/fly.py --snap S   # another start snapshot

As a library:
    from fly import Flight
    f = Flight()                                  # loads g_game1 into a stdrive.Drive
    f.hold(keys=['up'], loops=4)                  # hold the up arrow for ~4 main-loop passes (a pass is ~48k steps)
    f.mouse(dx=10, dy=0)                          # relative mouse motion (adds to stick x / stick y)
    f.mouse(dy=-9, right=True)                    # with the right button held, vertical motion is the throttle
    f.click('l', loops=2)                         # left button = laser (also Return / Insert / keypad Enter)
    f.run(loops=6); print(f.state())              # all named fields
    print(f.ab(lambda f: f.hold(keys=['space'], loops=3), loops=12).report())

Inputs and what they write (proof: gate_controls.py, gate_isr.py): the scancode of a held key sets a flag byte at
$c34e + scancode (ISR $b7be); the routine $d29a (once per pass) reads the flags. Held arrow keys step the stick
accumulators $c3ce (x), $c3d0 (y) by $20 per pass and Space / '/' step the throttle $c3d4 by -$10 / +$10 per pass;
mouse motion adds its raw counts to the same words ($c3d4 instead of $c3d0 while the right button is down)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flightlib import *

SCAN = dict(KEYMAP, ret=0x1c, insert=0x52, kpenter=0x72, esc=0x01, f=0x21, l=0x26, p=0x19, q=0x10, s=0x1f, m=0x32,
            i=0x17, n=0x31, g=0x22, k=0x25)
COUNTERS = {'shots': (176, 4), 'hits': (184, 4), 'dockings': (192, 4), 'agav_hits': (196, 4),
            'laser_energy': (650, 2), 'laser_cool': (644, 2)}


class Flight:
    def __init__(self, snap=None, journal=None):
        self.dr = new_drive(journal or sg.work('flight', 'fly.jsonl'), snap)
        self.ranges = {k: (G + o, 2) for k, o in WORDS.items()}
        self.ranges.update({k: (G + o, 1) for k, o in BYTES.items()})
        self.ranges.update({k: (a, 2) for k, a in ACC.items()})
        self.ranges.update({k: (G + o, n) for k, (o, n) in COUNTERS.items()})

    def state(self):
        s = state(self.dr)
        s.update({k: int.from_bytes(self.dr.read(G + o, n), 'big') for k, (o, n) in COUNTERS.items()})
        return s

    def run(self, loops=1):
        self.dr.step(int(loops * POLL * 1.1))

    def hold(self, keys=(), loops=4, buttons=''):
        """Press every key (names in SCAN or raw scancodes), hold ~`loops` passes (>= 1 poll period), release."""
        ks = [sd.Key(SCAN[k] if isinstance(k, str) else k) for k in keys]
        for k in ks: self.dr.press(k)
        if 'l' in buttons: self.dr.mouse('down', button='l')
        if 'r' in buttons: self.dr.mouse('down', button='r')
        self.dr.step(max(int(loops * POLL * 1.1), POLL))
        for k in ks: self.dr.release(k)
        if 'l' in buttons: self.dr.mouse('up', button='l')
        if 'r' in buttons: self.dr.mouse('up', button='r')

    def mouse(self, dx=0, dy=0, right=False, settle=POLL):
        if right: self.dr.mouse('down', button='r')
        self.dr.mouse('move', dx=dx, dy=dy); self.dr.step(settle)
        if right: self.dr.mouse('up', button='r')

    def click(self, which='l', loops=2):
        self.hold(buttons=which, loops=loops)

    def ab(self, fn, loops=12):
        return self.dr.ab(lambda d: fn(self), int(loops * POLL * 1.1), ranges=self.ranges)

    def close(self):
        self.dr.close()


CASES = [
    ('left arrow x4', lambda f: f.hold(['left'], 4)), ('right arrow x4', lambda f: f.hold(['right'], 4)),
    ('up arrow x4 (dive)', lambda f: f.hold(['up'], 4)), ('down arrow x4 (climb)', lambda f: f.hold(['down'], 4)),
    ('space x4 (accelerate)', lambda f: f.hold(['space'], 4)), ('slash x4 (decelerate)', lambda f: f.hold(['slash'], 4)),
    ('X x4 (= left arrow)', lambda f: f.hold(['x'], 4)), ('C x4 (= right arrow)', lambda f: f.hold(['c'], 4)),
    ('mouse dx=+20', lambda f: f.mouse(dx=20)), ('mouse dy=+20', lambda f: f.mouse(dy=20)),
    ('right button + dy=-30', lambda f: f.mouse(dy=-30, right=True)),
    ('left mouse button x2', lambda f: f.click('l', 2)), ('Return x2', lambda f: f.hold(['ret'], 2)),
    ('F (cross-hair lock)', lambda f: f.hold(['f'], 2)), ('L (launch missile)', lambda f: f.hold(['l'], 2)),
    ('Q / S (sound)', lambda f: f.hold(['q'], 2)),
]

if __name__ == '__main__':
    snap = sys.argv[sys.argv.index('--snap') + 1] if '--snap' in sys.argv else None
    f = Flight(snap)
    start = f.dr.fork()
    for name, fn in CASES:
        f.dr.restore(start)                  # every case starts from the same snapshot state
        r = f.ab(fn, 14)
        ch = []
        for n, addr, a, b in r.diff:
            w = len(a); sg_ = lambda x: int.from_bytes(x, 'big', signed=(w == 2 and n not in COUNTERS) )
            ch.append(f'{n} {sg_(b)}->{sg_(a)}')
        print(f'{name:26s} {len(r.diff):2d} fields: ' + ', '.join(ch))
    f.close()
