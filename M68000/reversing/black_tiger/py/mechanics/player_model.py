"""Python model of the player's vertical/jump/ladder step $00d7b0..$00daae and the tile-class lookup
$00ec7c (Black Tiger, COMMAND.PRG runtime addresses).  Operates on a bytearray RAM image.
The death branch (feet on a class-3 tile -> bsr $d44a) is reported, not modelled."""
import struct

def s16(v): v &= 0xffff; return v - 0x10000 if v & 0x8000 else v
class Mem:
    def __init__(self, ram): self.r = ram
    def rb(self, a): return self.r[a]
    def rw(self, a): return (self.r[a] << 8) | self.r[a + 1]
    def rl(self, a): return struct.unpack_from(">I", self.r, a)[0]
    def wb(self, a, v): self.r[a] = v & 0xff
    def ww(self, a, v): self.r[a] = (v >> 8) & 0xff; self.r[a + 1] = v & 0xff

def tile_class(m, x, y):
    """$ec7c: returns (class byte, tile word at the cell, D1 high byte for the cmp.b users)."""
    W = m.rw(0x1effe)
    x &= 0xffff
    if x & 0x8000: x = (x + W) & 0xffff
    elif s16(x) >= s16(W): x = (x - W) & 0xffff
    row = (y & 0xffff) >> 4
    d0 = (row * m.rw(0x201c8)) & 0xffffffff
    col = x >> 4
    d0 = (d0 & 0xffff0000) | ((d0 + col) & 0xffff)
    d0 = (d0 & 0xffff0000) | ((d0 << 1) & 0xffff)
    off = s16(d0 & 0xffff)
    tile = m.rw(0x201cc + off)
    return m.rb(0x25fcc + (tile & 0x3ff)), tile

JUMP_DY = 0x176f2

def step_vertical(m):
    """$d7b0. Returns list of events ('death',) if the class-3 branch is taken."""
    ev = []
    ww, rw, wb, rb = m.ww, m.rw, m.wb, m.rb
    def air_dx():
        ww(0x1782e, 8)
        if rw(0x1eece): ww(0x1782e, -8 & 0xffff)
    skip = False
    if rw(0x17830) != 0 and rw(0x1eed0) == 3 and rw(0x1782e) == 0:
        ww(0x17830, rw(0x17830) + 1); air_dx()
    elif rb(0x1f011) == 5:
        air_dx()
    while True:                                           # d7fe (re-entered from d890)
        if rw(0x17830) != 0:
            ww(0x1f016, rw(0x1f016) - rb(JUMP_DY + rw(0x17830)))
            ww(0x17830, rw(0x17830) - 1)
        c, _ = tile_class(m, rw(0x1f014), rw(0x1f016) - 0x20)        # head
        if c == 1:
            ww(0x17830, 0); ww(0x17832, 4); ww(0x1782e, 0)
        c, _ = tile_class(m, rw(0x1f014), rw(0x1f016) - 0x10)        # chest
        if c == 0 and rw(0x1f000) == 1 and rw(0x1eed0) == 1:
            ww(0x17830, 7); ww(0x17832, 0); ww(0x1f000, 2); continue
        break
    ww(0x1f000, 1)
    if c == 2:                                                          # ladder (d9a4)
        if rb(0x1f011) != 5:
            wb(0x1f01e, 2); ww(0x1f000, 1)
            ww(0x1f014, (rw(0x1f014) & 0xfff0) | 8)
            ww(0x1eff0, rw(0x1f016)); ww(0x17832, 3); ww(0x17830, 0); ww(0x1782e, 0)
    else:
        ww(0x1f000, 2)
        c, _ = tile_class(m, rw(0x1f014), rw(0x1f016))                  # feet
        if c in (0, 2):
            c2, _ = tile_class(m, (rw(0x1782e) + rw(0x1f014)) & 0xffff, rw(0x1f016))
            if c2 == 1: ww(0x1782e, 0)
            ww(0x1f014, rw(0x1f014) + rw(0x1782e))
            ww(0x1f000, 2)
            if rw(0x17830) == 0:
                i = rw(0x17832)
                ww(0x1f016, rw(0x1f016) + rb(JUMP_DY + i))
                if not (i & 8): ww(0x17832, i + 1)
            c3, _ = tile_class(m, rw(0x1f014), rw(0x1f016))
            if c3 == 1: land(m)
        elif c == 1:
            land(m)
        else:                                                           # class 3
            ww(0x1f000, 0); ww(0x1782e, 0); ev.append(("death",))
            return ev
    wb(0x1f013, rb(0x1eecf))
    A0 = m.rl(0x1769c + 4 * rw(0x1f000))
    d0 = rb(A0 + rw(0x1eed0))
    if d0 & 0x80:
        d0 &= 0x7f
        if rw(0x17830) == 0:
            ww(0x17832, 0); ww(0x17830, 6)
            if rw(0x1f000) == 1: ww(0x17830, 4)
    if rb(0x1eed6) & 0x80:
        if rw(0x1f000) == 1: ww(0x17830, 0)
        d0 = rb(0x176ce + rw(0x1f000))
        d1 = rw(0x1eed0)
        if d1 != 0 and d1 >= 4 and rw(0x1f000) == 0: d0 = 0x0b
    if d0 != rb(0x1f011):
        wb(0x1f011, d0); wb(0x1f012, 0)
    return ev

def land(m):
    m.ww(0x1f000, 0); m.ww(0x1782e, 0); m.wb(0x1f01e, 0)
    m.ww(0x1f016, m.rw(0x1f016) & 0xfff0)
    m.ww(0x17832, 3); m.ww(0x1eff0, m.rw(0x1f016))
