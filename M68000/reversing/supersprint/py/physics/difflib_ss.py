"""difflib_ss.py - differential-test helpers: run the Python port on a snapshot RAM image and compare with the
emulator's callcap memory delta over the physics-state region (A4-relative window + the surface map)."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pl import *
import ssport as P

# regions compared (absolute addresses): the game's global block and the 1000-byte surface map
LO, HI = A4 - 9000, A4 + 1400
# effect / sound slots that the port deliberately does not model ($b6f8 dust/skid slots)
EXCL = [(A4 - 4650, A4 - 4566),       # $b6f8 dust/skid effect slots
        (A4 - 3634, A4 - 3602)]       # render dirty-rect records (screen offset + row count, double-buffered)


def in_region(a, mapbase):
    if any(lo <= a < hi for lo, hi in EXCL):
        return False
    return (LO <= a < HI) or (mapbase <= a < mapbase + 1000)


def emu_delta(d, mapbase):
    """callcap json -> {addr: newbyte} restricted to the compare region"""
    return {ad: new for ad, old, new in d['mem'] if in_region(ad, mapbase)} if d else None


def py_delta(pre, post, mapbase):
    out = {}
    for lo, hi in ((LO, HI), (mapbase, mapbase + 1000)):
        for a in range(lo, hi):
            if pre[a] != post[a] and in_region(a, mapbase):
                out[a] = post[a]
    return out


def compare(pre_bytes, py_mem, d, mapbase):
    """returns list of mismatching (addr, py_new_or_None, emu_new_or_None)"""
    ed = emu_delta(d, mapbase)
    pd = py_delta(pre_bytes, py_mem.b, mapbase)
    bad = []
    for a in set(ed) | set(pd):
        if ed.get(a) != pd.get(a):
            bad.append((a, pd.get(a, pre_bytes[a]), ed.get(a, pre_bytes[a])))
    return sorted(bad)


def field_name(a):
    off = a - A4
    return '%+d(A4)' % off


class Driver:
    """natural-play driver: pseudo-random joystick-0 input (fire mostly held) applied between breakpoint stops."""
    def __init__(s, h, seed=1):
        s.h = h
        s.rng = random.Random(seed)
        s.cur = None
        s.count = 0

    def poke_input(s):
        if s.count % 6 == 0:
            r = s.rng.random()
            fire = 0x80 if r < 0.85 else 0
            steer = s.rng.choice([0, 0, 4, 8, 4, 8, 4, 8, 1, 2])
            byte = fire | steer
            s.h.cmd('kbd fe %02x' % byte)
            # the IKBD ISR is taken at the very next step; if we are stopped at a routine entry PC it would return to that entry and
            # count as a second breakpoint hit, so step past it first
            s.h.cmd('s 300')
        s.count += 1
