#!/usr/bin/env python3
"""Captive's universe generator (fed_MapView $30280..$304a8), reimplemented and diffed against RAM.

Usage (from M68000/):
  uv run python -I reversing/captive/py/world/universe.py <snap> [--callcap delta.json --mission N] [--names]
  (--callcap: compare against the snapshot with a REPL callcap delta applied, e.g. after
   `w 1ef86 00010001` / `callcap 302c6 3000000 delta.json` re-runs the generator for mission index 1)

Naming follows the game's own labels ($2ff6e: object number 1..50 prints "PLANET-", 51..150
"MOON-", 0 "SPACE-STATION"): the 51 map dots are slot 0 = the space station plus planets 1..50,
and the 100 orbiting bodies are moons. Object index = object number - 1 (0..49 planets 1..50,
50..149 moons). In the code below `stars` = the 51 map dots and `planets` = the moons.

The whole mission map comes from one 16-bit LCG seeded with the mission index 14776(A6)
(0 for "CAPTIVE MISSION 0001"):
  rng $3049c:  D0 = (D0.w * $5e5 + $29) & $ffff ; D1 = ror.w #2 of D0
  $30430 dots:     51 (x,y), each coordinate a 5-bit field of D1 (0 rejected) mapped through the
                   32-byte table at $3047c; duplicates rejected. -> 13566(A6), longs (x.w, y.w)
  $303f6 moons:    100 picks of planet 1..50 (D1*50>>16) plus an orbit slot D1&7 in byte 2;
                   duplicates rejected. -> 13770(A6), longs
  $3037a/$3039e:   convert both tables in place to map coordinates (c*512 - $2600, plus an orbit
                   offset from the table at $303d6 for moons)
  $302fa:          10 marked objects in 14170(A6) (150 longs): byte 3 = 1..10 at a random slot
                   (D0*150>>16; slot 0 first for mission 0)
  $3032c:          bytes 0,1 of the 150 objects: 50 x (D0&31, D0>>5&31), 100 x ((D0&15)+7, (D0>>5&15)+7)
The script runs the same steps from the snapshot's own mission index and the table bytes read from
the snapshot's copy of fed_MapView, then compares each table with RAM.
"""
import os
import struct
import sys


def repo_root():
    d = os.environ.get('M68000_ROOT') or os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
        p = os.path.dirname(d)
        if p == d:
            raise SystemExit('repo root (tools/rdis.py) not found')
        d = p
    return d


sys.path.insert(0, os.path.join(repo_root(), 'tools'))
from gfxview import load_ram  # noqa: E402

A6 = 0x1b5ce
MAPVIEW = 0x2f3f0          # fed_MapView code base at mission 1 (tables are read PC-relative)


class Rng:
    def __init__(self, seed):
        self.d0 = seed & 0xffff

    def step(self):
        self.d0 = (self.d0 * 0x5e5 + 0x29) & 0xffff
        d1 = ((self.d0 >> 2) | (self.d0 << 14)) & 0xffff
        return self.d0, d1


def generate(mission, xytab, orbtab):
    r = Rng(mission)
    r.step(); r.step()                       # $30430, $30432
    stars = []
    while len(stars) < 51:                   # $30444 moveq #50 / dbf
        _, d1 = r.step()
        x, y = d1 & 31, (d1 >> 5) & 31
        if x == 0 or y == 0:
            continue
        v = (xytab[x] << 16) | xytab[y]
        if v in stars:                       # compares against all 51 slots, zero-filled
            continue
        stars.append(v)
    planets = []
    while len(planets) < 100:                # $303fa moveq #99
        _, d1 = r.step()
        idx = ((d1 * 50) >> 16) & 0xffff     # mulu #$32 / swap
        star = stars[1 + idx]                # 13570(A6) = star 1
        v = star | ((d1 & 7) << 8)
        if v in planets:
            continue
        planets.append(v)
    # $3037a / $3039e: coordinate conversion
    def conv(c):
        return ((c * 2) << 8) - 0x2600 & 0xffff
    star_xy = [(conv(v >> 16), conv(v & 0xffff)) for v in stars]
    planet_xy = []
    for v in planets:
        x, o, y = v >> 16, (v >> 8) & 0xff, v & 0xff
        dx, dy = orbtab[o]
        planet_xy.append(((conv(x) + dx) & 0xffff, (conv(y) + dy) & 0xffff))
    # $302fa: 10 marked objects
    objs = [[0, 0, 0, 0] for _ in range(150)]
    for k in range(10):
        if mission == 0 and k == 0:
            slot = 0
        else:
            while True:
                d0, _ = r.step()
                slot = (d0 * 150) >> 16
                if objs[slot] == [0, 0, 0, 0]:
                    break
        objs[slot][3] = k + 1
    # NB: the retry test is "tst.l (A0)" on a slot, as above
    for i in range(50):                      # $3032c
        d0, _ = r.step()
        objs[i][0], objs[i][1] = d0 & 31, (d0 >> 5) & 31
    for i in range(50, 150):
        d0, _ = r.step()
        objs[i][0], objs[i][1] = (d0 & 15) + 7, ((d0 >> 5) & 15) + 7
    return stars, star_xy, planets, planet_xy, objs, r.d0


SYL = [0x30706, 0x30726, 0x30746, 0x30766]   # 4 tables of 16 two-byte syllables


def name(ram, mission, obj):
    """$3066e: name of object obj (0..49 stars 1..50, 50..149 planets; -1 the station).

    The routine takes D3 = 149 - obj (the draw loops' dbf counters, stars +100) and seeds with
    mission*150 + 149 - D3 = mission*150 + obj; D3 = 150 (obj -1) is 'STATION'."""
    if obj == -1:
        return 'STATION'
    d4 = (mission * 150 + obj) & 0xffff
    d4 = (d4 * 0x5e5 + 0x29) & 0xffff
    d4 = ((d4 >> 8) | (d4 << 8)) & 0xffff
    d4 = (d4 * 0x5e5 + 0x29) & 0xffff
    d4 = (d4 * 0x5e5 + 0x29) & 0xffff
    s = ''
    for t in SYL:
        a = t + 2 * (d4 & 15)
        s += chr(ram[a])
        if ram[a + 1]:
            s += chr(ram[a + 1])
        d4 = ((d4 >> 4) | (d4 << 12)) & 0xffff
    return s


def main():
    snap = sys.argv[1]
    ram, base = load_ram(snap)
    assert base == 0
    if '--callcap' in sys.argv:              # apply a callcap delta (REPL `callcap 302c6 ... out.json`)
        import json
        ram = bytearray(ram)
        for a, old, new in json.load(open(sys.argv[sys.argv.index('--callcap') + 1]))['mem']:
            ram[a] = new
    w = lambda a: struct.unpack('>H', ram[a:a + 2])[0]
    L = lambda a: struct.unpack('>I', ram[a:a + 4])[0]
    mission = w(A6 + 14776)
    if '--mission' in sys.argv:              # the poked mission index (a REPL poke is not in the delta)
        mission = int(sys.argv[sys.argv.index('--mission') + 1])
    xytab = list(ram[0x3047c:0x3047c + 32])
    orbtab = []
    for i in range(8):
        a = 0x303d6 + 4 * i
        dx, dy = struct.unpack('>hh', ram[a:a + 4])
        orbtab.append((dx, dy))
    stars, sxy, planets, pxy, objs, d0 = generate(mission, xytab, orbtab)
    print(f'mission index 14776(A6) = {mission} (screen shows {mission + 1:04d})')
    print('coordinate table $3047c:', xytab)
    print('orbit offsets $303d6:', orbtab)
    ok = 0
    for i, (x, y) in enumerate(sxy):
        a = A6 + 13566 + 4 * i
        ok += (w(a), w(a + 2)) == (x, y)
    print(f'station+planets 13566(A6) = ${A6 + 13566:x}: {ok}/51 match')
    ok = 0
    for i, (x, y) in enumerate(pxy):
        a = A6 + 13770 + 4 * i
        ok += (w(a), w(a + 2)) == (x, y)
    print(f'moons 13770(A6) = ${A6 + 13770:x}: {ok}/100 match')
    ok = 0
    for i, o in enumerate(objs):
        a = A6 + 14170 + 4 * i
        ok += list(ram[a:a + 4]) == o
    print(f'objects 14170(A6) = ${A6 + 14170:x}: {ok}/150 match')
    marked = [(i, o[3]) for i, o in enumerate(objs) if o[3]]
    print('target objects, byte 3 (object index, number):', sorted(marked, key=lambda t: t[1]))
    if '--names' in sys.argv:
        for i in range(-1, 150):
            print(i, name(ram, mission, i), objs[i] if i >= 0 else '')


if __name__ == '__main__':
    main()
