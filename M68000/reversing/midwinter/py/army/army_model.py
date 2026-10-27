"""Model of the enemy army tick `$c136` (ai.md section 2), transcribed from the routine.

State (all big-endian, absolute addresses):
  $2bb96  32 unit records of 16 bytes: +0/+2 x, y (words, node-coordinate units); +4 bit 7 active, bits 0-6 the node
          the unit last reached; +5 bit 7 "spread" mode; +11 speed per tick; +13 target node (0 = choose one, < 0 =
          stationary)
  $25b4a  node coordinates, (x.w, y.w) per node, 96 nodes (static)
  $25cca  node adjacency, 4 neighbour bytes per node, 0 = no road (static)
  $2bb36  per-node state byte: bit 7 enemy held, bits 0-6 the neighbour a unit last left it towards (the trail)
  $2a150  the feature list; `$14a8` returns record #node, whose kind byte gets bit 7 (enemy held, on the map)
  $d5d8   RNG seed word, $d5da its multiplier (`$d598`)
  $2bb2e  trail-following toggle (read and flipped by non-spread units), $2bb30 set to -1 on an empty road slot
  $2bae4/$2bae6  scratch words (unit offset, target*4)
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'terrain'))
from terrain_gen import isqrt_198d8  # noqa: E402

UNITS, NODES, ADJ, STATE, FEAT = 0x2bb96, 0x25b4a, 0x25cca, 0x2bb36, 0x2a150
SEED, MULT = 0xd5d8, 0xd5da
BRANCH = {}  # how often each branch of the tick ran (for the gate's coverage line)


def hit(name):
    BRANCH[name] = BRANCH.get(name, 0) + 1


class Mem:
    def __init__(self, ram):
        self.b = bytearray(ram)

    def u8(self, a): return self.b[a]
    def s8(self, a): v = self.b[a]; return v - 256 if v & 0x80 else v
    def w(self, a): return (self.b[a] << 8) | self.b[a + 1]
    def sw(self, a): v = self.w(a); return v - 0x10000 if v & 0x8000 else v
    def set8(self, a, v): self.b[a] = v & 0xff
    def setw(self, a, v): self.b[a] = (v >> 8) & 0xff; self.b[a + 1] = v & 0xff


def rand_d598(m):
    """`$d5b2`: s' = (s*k + k) mod 65537 - 1, as the 68000 computes it; returns D0 (32-bit)."""
    s, k = m.w(SEED), m.w(MULT)
    d0 = s * k + k
    lo, hi = d0 & 0xffff, d0 >> 16
    d0 = lo - hi
    if d0 < 0:
        d0 += 0x10001
    d0 -= 1
    m.setw(SEED, d0 & 0xffff)
    return d0


def rand_mod(m, n):
    """`$d57e`: (rand & $ffff) mod n."""
    return (rand_d598(m) & 0xffff) % n


def feature_record(m, node):
    """`$14a8`: address of feature record #node (1-based) in the variable-length list at $2a150."""
    a = FEAT
    for _ in range(node - 1):
        a += 6 + 2 * (m.u8(a) & 0x7f)
    return a


def s16(v):
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v


def tick(m):
    for unit in range(31, -1, -1):
        u = UNITS + 16 * unit
        m.setw(0x2bae4, 16 * unit)
        if not m.u8(u + 4) & 0x80:
            continue
        t = m.s8(u + 13)
        if t < 0:
            continue
        if t > 0:
            m.setw(0x2bae6, 4 * t)
            x, y = m.sw(u), m.sw(u + 2)
            dx = s16(m.sw(NODES + 4 * t) - x)
            dy = s16(m.sw(NODES + 4 * t + 2) - y)
            dist = isqrt_198d8((dx * dx + dy * dy) & 0xffffffff) & 0xffff
            speed = m.u8(u + 11)
            if speed < dist:
                # muls/divs: quotient truncated toward zero, word add
                hit('move')
                qx = int(dx * speed / dist)
                qy = int(dy * speed / dist)
                m.setw(u, x + qx)
                m.setw(u + 2, y + qy)
            else:
                hit('arrive')
                m.setw(u, m.w(NODES + 4 * t))
                m.setw(u + 2, m.w(NODES + 4 * t + 2))
                f = feature_record(m, t)
                m.set8(f, m.u8(f) | 0x80)
                m.set8(STATE + t, m.u8(STATE + t) | 0x80)
                m.set8(u + 4, t | 0x80)
                m.set8(u + 13, 0)
            continue
        # choose the next node from the four roads out of node n
        n = m.u8(u + 4) & 0x7f
        trail = m.u8(STATE + n)
        roads = ADJ + 4 * n
        k = [0]  # D4, the rotating road index

        def road():
            """`$c2cc`: (neighbour, held) for road k, then k += 1 mod 4; an empty road counts as held."""
            d1 = m.u8(roads + k[0])
            k[0] = (k[0] + 1) & 3
            if d1 == 0:
                m.setw(0x2bb30, 0xffff)
                return 0, True
            return d1, bool(m.u8(STATE + d1) & 0x80)

        if m.u8(u + 5) & 0x80:
            free = sum(1 for _ in range(4) if not road()[1])
            if free:
                hit('spread_free')
                pick = rand_mod(m, free)
                for _ in range(pick + 1):
                    while True:
                        d1, held = road()
                        if not held:
                            break
                if trail & 0x7f == 0:
                    m.set8(STATE + n, trail | d1)
            else:
                hit('spread_all_held')
                k[0] = rand_mod(m, 3)
                d1, _ = road()
                m.set8(STATE + d1, m.u8(STATE + d1) & 0x80)
        else:
            d1 = None
            if m.w(0x2bb2e):
                m.setw(0x2bb2e, ~m.w(0x2bb2e) & 0xffff)
                if trail & 0x7f:
                    d1 = trail & 0x7f
            if d1 is not None:
                hit('trail')
            else:
                hit('wander')
            if d1 is None:
                k[0] = rand_mod(m, 3)
                d1, _ = road()
        m.set8(u + 13, d1)


def held_sites(m, types):
    """`$f656` / `$f6a8`: (x, y) of every enemy-held feature record (kind bit 7) with a building whose type
    (word byte 0 & $1f, names at `$2624e`) is in `types`."""
    out, a = [], FEAT
    while m.u8(a):
        k = m.u8(a)
        if k & 0x80:
            n = k & 0x7f
            if any(m.u8(a + 6 + 2 * j) & 0x1f in types for j in range(n)):
                out.append((m.w(a + 2), m.w(a + 4)))
        a += 6 + 2 * (k & 0x7f)
    return out


def supply(m, field):
    """`$f56e` (field 11: Warehouses $b and Synthesis Plants $c, bias 5) and `$f5e2` (field 12: Warehouses and
    Factories $d, bias 1): per unit, the byte sum of (u[6] + bias) * 500 // (|dx| + |dy| + 50) over those sites."""
    types, bias = ({0xb, 0xc}, 5) if field == 11 else ({0xb, 0xd}, 1)
    sites = held_sites(m, types)
    for unit in range(32):
        u = UNITS + 16 * unit
        x, y, w6 = m.w(u), m.w(u + 2), m.u8(u + 6)
        total = 0
        for sx, sy in sites:
            d = (abs(s16(sx - x)) + abs(s16(sy - y)) + 50) & 0xffff
            total += ((((w6 + bias) * 500) & 0xffffffff) // d) & 0xffff
        m.set8(u + field, total)
