"""Gate: the letter commands of $d29a, each driven in flight from g_game1 against a no-key control (same snapshot, same
budget): F toggles the cross-hair lock 705, Q/S clear/set the sound flag 715, Esc jumps to $ca20 (abandon the game),
L launches a missile (632 1 -> 0, missile camera 712). P, I, N, M need a docked/practice state and are only read.

    cd M68000 && ATARI_NOTRACE=1 python3 reversing/starglider/py/flight/gate_letters.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flightlib import *
from fly import Flight, SCAN
f = Flight(journal=sg.work('flight', 'j_letters.jsonl')); dr = f.dr
f0 = dr.fork()
ok = n = 0
def check(name, keys, field, off, width, want, base=None):
    global ok, n
    dr.restore(f0)
    if base is not None: dr.poke(G + off, width, base)
    f.hold(keys, 2); f.run(2)
    got = int.from_bytes(dr.read(G + off, width), 'big')
    dr.restore(f0)
    if base is not None: dr.poke(G + off, width, base)
    f.run(4)
    ctl = int.from_bytes(dr.read(G + off, width), 'big')
    good = (got == want and ctl != want)
    n += 1; ok += good
    print(f'{name:22s} {field}={got:#x} (want {want:#x}), control {ctl:#x}  {"ok" if good else "BAD"}')
check('F', ['f'], '705 lock', 705, 1, 0xff)
check('Q (sound off)', ['q'], '715 sound', 715, 1, 0)
check('S (sound on)', ['s'], '715 sound', 715, 1, 0xff, base=0)
check('L (missile)', ['l'], '632 missiles', 632, 2, 0)
# Esc: breakpoint at $ca20 must be reached with Esc held and not without
for name, keys in (('Esc', ['esc']), ('control', [])):
    dr.restore(f0)
    dr.rpc('bp_set', addrs=[0xca20])
    if keys: dr.press(sd.Key(SCAN['esc']))              # `step` ignores breakpoints, so press, then `run`
    r = dr.run(1500000)
    if keys: dr.release(sd.Key(SCAN['esc']))
    dr.rpc('bp_clear', addrs=[0xca20])
    hit = r['reason'] == 'breakpoint'
    good = hit == bool(keys); n += 1; ok += good
    print(f'{name:22s} reached $ca20: {hit}  {"ok" if good else "BAD"}')
print(f'letters: MATCH {ok}/{n}')
f.close()
