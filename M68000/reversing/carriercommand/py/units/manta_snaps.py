#!/usr/bin/env python3
"""Make the Manta anchor snapshots from c_s30.snap and log the first flight.

usage: manta_snaps.py [ticks_after_takeoff=300]

Through the game's own handlers: lift Manta 0 to the deck ($11386), wait for the lift to stop, launch ($11af6),
follow slot 0 ($498) and its entity ($5df5a) once per main frame (a breakpoint on $1ac8c, the enemy tick), and save $CARRIER_WORK/manta/m_deck.snap (on deck, lift stopped), m_takeoff.snap (the
first airborne tick, +28 = 3) and m_air.snap (the given number of ticks later). One line per tick on stdout.
The run is deterministic: a rerun prints the same log (vehicles.md section 5).
"""
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent))
from ccpaths import *
import struct

sys.path.insert(0, str(ROOT / 'tools'))
from stclient import StServer

OUT = WORK / 'manta'
OUT.mkdir(parents=True, exist_ok=True)
after = int(sys.argv[1]) if len(sys.argv) > 1 else 300
s = StServer(str(ROOT))
s('load', snapshot=str(ANCHOR))
s('poke', addr=0x126c, width=4, value=0x00ff0001)          # the crack's stack leak (README "Provenance")



def w(a): return struct.unpack('>h', s.read(a, 2))[0]


def show(tag):
    sl, e = s.read(0x498, 52), s.read(0x5df5a, 64)
    x, y, z = struct.unpack('>iii', e[10:22])
    print(tag, 'st1', sl[1], 'b28', sl[28], 'b29', sl[29], 'f0', hex(sl[0]), 'e1', hex(e[1]), 'xyz', x, y, z,
          'pitch', struct.unpack('>h', e[4:6])[0], 'hdg', e[6:8].hex(), 'deckz', struct.unpack('>h', e[30:32])[0],
          'v', struct.unpack('>h', sl[6:8])[0], 'fuel', struct.unpack('>h', sl[10:12])[0], 'dca', w(0xdca),
          'dcc', w(0xdcc), flush=True)
    return sl


def tick(): s('run', max_steps=200000)


s.call_resume(0x11386, d2=2)
show('lift')
s('bp_set', addrs=[0x1ac8c])
for k in range(3000):
    tick()
    sl = show(f'L{k}')
    if sl[28] == 1 and w(0xdca) == 0:
        break
s('save', path=str(OUT / 'm_deck.snap'))
s.call_resume(0x11af6, d2=2)
show('launch')
for k in range(3000):
    tick()
    sl = show(f'T{k}')
    if sl[28] == 3:
        s('save', path=str(OUT / 'm_takeoff.snap'))
        break
for k in range(after):
    tick()
    show(f'A{k}')
s('save', path=str(OUT / 'm_air.snap'))
s('bp_clear', addrs=[0x1ac8c])
s.close()
