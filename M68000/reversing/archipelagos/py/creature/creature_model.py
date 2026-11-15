#!/usr/bin/env python3
"""creature_model.py: model of Archipelagos' per-tick creature loop $1a4e0 (object_step_loop) and its
footprint $1a6c4, from the disassembly of m2.snap's $1a4e0..$1a6e0 (README "The creature and its blood").

State read and written (word = big-endian 16 bit):
  $1db28          object count n
  $1db3e + 2i     phase counter (word)        $1a4f8 / $1a6bc
  $1db3e + 64+2i  position word (hi byte y, lo byte x of a 256x256 map; cell = A1 + sext16(pos), A1 = $b000)
  $1db3e + 128+2i copy of the word at $1d2a0 + phase, written every tick   $1a4fa
  $1d696, $1d698  the player position: the BYTES at those addresses (the high bytes of two words)
  map $3000..$12fff: cell byte; low 3 bits = land value, bit 7 = "occupied/visible" mark
Every tick: out[i] = W[$1d2a0 + phase]; phase += 2; if phase != $150: store it, next object. At $150 the
object steps (and its phase is stored as 0).
Step: for shift k in 3, 4, 5: candidate = pos - ((pos_byte - player_byte) >> k) per axis (byte arithmetic; from the
second round the x difference register D4 holds ((cell(-1) ^ $80) & $82) left by the cell test, not the difference);
take the first of {candidate, then the 8 neighbours in the order -257 -256 -255 +1 +257 +256 +255 -1}
whose cell has bit 1 set and bit 7 clear; none for all three k -> stay.  Old cell &= 7; new cell =
(v & $f) | $80; the new cell and its four cardinal neighbours (self, +1, -1, +256, -256) then run the
footprint: low 3 bits > 4 -> minus 4.
Usage: import and call step_tick(ram, bug=None) on a bytearray copy of the whole 1 MB RAM (in place).
"""
import os, subprocess, sys

import collections
A1 = 0xB000
BR = collections.Counter()   # branch coverage of choose(): 'k3:direct', 'k4:off-257', ..., 'stay'
TAB = 0x1DB3E
CNT = 0x1DB28
SRC = 0x1D2A0
PLY_X = 0x1D696
PLY_Y = 0x1D698
PHASE_END = 0x150
ORDER = (-257, -256, -255, 1, 257, 256, 255, -1)


def s8(x):
    x &= 0xFF
    return x - 256 if x & 0x80 else x


def s16(x):
    x &= 0xFFFF
    return x - 65536 if x & 0x8000 else x


def rw(m, a):
    return m[a] << 8 | m[a + 1]


def ww(m, a, v):
    m[a] = (v >> 8) & 0xFF
    m[a + 1] = v & 0xFF


def ok(v):
    """(v ^ $80) & $82 == $82: bit 1 set, bit 7 clear."""
    return ((v ^ 0x80) & 0x82) == 0x82


def footprint(m, a, bug=None):
    v = m[a]
    lo = v & 7
    lim = 5 if bug == 'lim5' else 4
    if lo > lim:
        lo -= 4
    m[a] = (v & 0xF8) | lo


def choose(m, pos, bug=None):
    """Return the new position word (D1) for the object at word position pos."""
    d5 = (pos >> 8) - m[PLY_Y]              # y difference, byte
    d4 = (pos & 0xFF) - m[PLY_X]            # x difference, byte
    d3, d2 = (pos >> 8) & 0xFF, pos & 0xFF
    order = ORDER if bug != 'order' else (-256, -257, -255, 1, 257, 256, 255, -1)
    k = 3
    while k < 6:
        sh = k + 1 if bug == 'shift' else k
        d7 = (d3 - (s8(d5) >> sh)) & 0xFF
        d6 = (d2 - (s8(d4) >> sh)) & 0xFF
        d1 = d7 << 8 | d6
        a3 = A1 + s16(d1)
        if ok(m[a3]):
            BR['k%d:direct' % k] += 1
            return d1
        for off in order:
            if ok(m[a3 + off]):
                BR['k%d:off%+d' % (k, off)] += 1
                return (d1 + off) & 0xFFFF
        if bug != 'noclobber':
            d4 = (m[a3 - 1] ^ 0x80) & 0x82      # D4 is also the cell-test register ($1a540..): the x difference is lost
        k += 1                               # after a failed round, the retry shifts the last tested cell's masked value
    BR['stay'] += 1
    return pos


def step_tick(m, bug=None):
    n = rw(m, CNT)
    for i in range(n):
        a2 = TAB + 2 * i
        d0 = s16(rw(m, a2))
        ww(m, a2 + 128, rw(m, SRC + d0))
        d0 += 2
        if d0 != PHASE_END:
            ww(m, a2, d0 & 0xFFFF)
            continue
        pos = rw(m, a2 + 64)
        d1 = choose(m, pos, bug)
        m[A1 + s16(pos)] &= 7
        a5 = A1 + s16(d1)
        m[a5] = (m[a5] & 0xF) | 0x80
        ww(m, a2 + 64, d1)
        for off in (0, 1, -1, 256, -256):
            footprint(m, a5 + off, bug)
        ww(m, a2, 0)
    return m


def event_writes(m, i=0, bug=None):
    """The ordered map writes (pc, address, value) object i makes when it steps, on RAM m (not modified):
    $1a634 old cell, $1a63e then $1a642 the new cell, then five $1a6de footprint writes."""
    a2 = TAB + 2 * i
    pos = rw(m, a2 + 64)
    t = bytearray(m)
    d1 = choose(t, pos, bug)
    out = [(0x1A634, A1 + s16(pos), t[A1 + s16(pos)] & 7)]
    t[A1 + s16(pos)] &= 7
    a5 = A1 + s16(d1)
    v = t[a5] & 0xF
    out.append((0x1A63E, a5, v))
    v |= 0x80
    t[a5] = v
    out.append((0x1A642, a5, v))
    for off in (0, 1, -1, 256, -256):
        footprint(t, a5 + off, bug)
        out.append((0x1A6DE, a5 + off, t[a5 + off]))
    return out


def repo_root(start=None):
    d = os.path.abspath(start or os.path.dirname(__file__))
    while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
        d = os.path.dirname(d)
    return d


def capture_entry():
    """Fresh capture: m2.snap run to its first $1a4e0 call (A1 = $b000), written to
    scratchpad/archipelagos/creature/entry.snap.  Returns the snapshot path."""
    root = repo_root()
    work = os.path.join(root, 'scratchpad', 'archipelagos', 'creature')
    os.makedirs(work, exist_ok=True)
    out = os.path.join(work, 'entry.snap')
    for f in (out, out + '.prov.json'):
        if os.path.exists(f):
            os.remove(f)
    script = 'bp 1a4e0 300000\nsnap %s\nq\n' % os.path.relpath(out, root)
    dll = os.path.join(root, 'bin', 'Debug', 'net8.0', 'M68000.dll')
    subprocess.run(['dotnet', 'exec', dll, 'resume', 'scratchpad/archipelagos/m2.snap', 'repl'], input=script.encode(),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=root, check=True)
    assert os.path.exists(out), 'entry capture failed'
    return out
