"""Gate: the laser. $131f8 (once per pass) fires when the laser-energy word 650(A6) is non-zero, the craft is not docked
(714 = 0) and one of the fire keys is held: key flags $c34e+116 (left mouse button, IKBD button-as-key $74), +28 (Return),
+82 (Insert), +114 (keypad Enter). A shot adds 1 to the shots-fired long 176(A6), loads the 4-pass cool-down 644(A6) and
takes $100 from 650(A6) (floor 0).

    cd M68000 && ATARI_NOTRACE=1 python3 reversing/starglider/py/flight/gate_laser.py
Prints per leg the shots fired and laser energy; `laser: MATCH k/n` counts legs where 650 == start - $100 * shots (floor 0)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flightlib import *
from fly import Flight

f = Flight(journal=sg.work('flight', 'j_laser.jsonl'))
dr = f.dr
f0 = dr.fork()
ok = n = 0
def leg(name, start650, run):
    global ok, n
    dr.restore(f0)
    dr.poke(G + 650, 2, start650)
    s0 = dr.u32(G + 176)
    t0 = dr.step_count
    run()
    shots = dr.u32(G + 176) - s0
    e = dr.u16(G + 650)
    exp = max(0, start650 - 0x100 * shots)
    n += 1; ok += (e == exp)
    print(f'{name:34s} shots {shots:3d} in {(dr.step_count - t0) // POLL} x 44k steps; laser {start650} -> {e} (expect {exp}) {"ok" if e == exp else "BAD"}')
leg('Return held 20 passes', 65535, lambda: f.hold(['ret'], 20))
leg('left mouse button held 20 passes', 65535, lambda: f.hold([], 20, buttons='l'))
leg('Insert held 8 passes', 65535, lambda: f.hold(['insert'], 8))
leg('keypad Enter held 8 passes', 65535, lambda: f.hold(['kpenter'], 8))
leg('Return, laser energy 300 (floor)', 300, lambda: f.hold(['ret'], 20))
leg('Return, laser energy 0 (no fire)', 0, lambda: f.hold(['ret'], 20))
leg('no key (control)', 65535, lambda: f.run(20))
print(f'laser: MATCH {ok}/{n}')
f.close()
