"""Wrench (gold spanner) pickup proof.  From race_T.snap: run until the wrench state machine ($ae0e) has placed a wrench
(-1850(A4)==4), read its cell, confirm the surface-attribute map holds 0x0d there, teleport the human car onto it, and
show -3954(A4)[car] (per-car wrench count, initialised from the difficulty dial) +1, the cell cleared, -1856 set."""
import sys; sys.path.insert(0,'.')
from tkcommon import *
import struct

def rw(r, off, n=1):
    b = r.mem(A4 + off, 2 * n); return list(struct.unpack('>%dh' % n, b))
def setw(r, off, val):
    a = A4 + off; aligned = a & ~1
    cur = r.mem(a, 4)                                  # `w` writes a longword: preserve the neighbour word
    r.cmd('w %x %04x%s' % (a, val & 0xffff, cur[2:].hex()))

def main(T):
    r = Repl(out('snaps', 'race_%d.snap' % T))
    r.cmd('s 3000000')
    for _ in range(400):
        r.cmd('s 12000')
        if rw(r, -1850)[0] == 4: break
    col, row = rw(r, -1852)[0], rw(r, -1854)[0]
    cell = col + row * 40
    attr = r.mem(A4 + 0, 0) if False else None
    mapptr = struct.unpack('>I', r.mem(A4 - 1910, 4))[0]
    a0 = r.mem(mapptr + cell, 2)
    print('track %d: wrench placed at cell col=%d row=%d (px %d,%d); attr[cell],attr[cell+1] = %02x %02x; state=%d timer=%d' %
          (T + 1, col, row, col * 8, row * 8, a0[0], a0[1], rw(r, -1850)[0], rw(r, -1848)[0]))
    flags = rw(r, -3914, 4); human = [i for i in range(4) if flags[i] == 0][0]
    before = rw(r, -3954, 4)
    print('human car slot', human, 'wrench counts before (-3954(A4)[0..3]):', before, 'pickup flag -1856:', rw(r, -1856)[0])
    # teleport the human car onto the wrench (screen coords: x = col*8 .. ; sampler adds a per-heading offset)
    wx, wy = rw(r, -3786, 4)[human], rw(r, -3794, 4)[human]
    print('world words for human: -3786(A4)=%d -3794(A4)=%d (screen px %d,%d)' % (wx, wy, rw(r, -3690, 4)[human], rw(r, -3698, 4)[human]))
    sx = rw(r, -3690, 4)[human]
    xoff, yoff = (-3786, -3794) if abs(wx - sx * 8) <= 8 else (-3794, -3786)   # whichever word is ~8 x screen X
    X, Y = col * 64 + 16, row * 64 - 6 * 8      # heading-12 sampler offsets are (+1,+7) and (+3,+4) px: aim so both fall in the cell
    for o, v in ((-3786, X), (-3738, X), (-3794, Y), (-3746, Y)): setw(r, o + 2 * human, v)
    print('pos after poke', rw(r,-3690,4), rw(r,-3698,4))
    for _ in range(4):
        r.cmd('s 12000'); print('  step pos', rw(r,-3690,4)[human], rw(r,-3698,4)[human], 'cnt', rw(r,-3954,4)[human], 'edge', rw(r,-3778,4)[human], 'spd', rw(r,-3730,4)[human])
    after = rw(r, -3954, 4)
    a1 = r.mem(mapptr + cell, 2)
    print('after ~3 frames: counts', after, ' attr[cell]', '%02x %02x' % (a1[0], a1[1]), ' pickup flag -1856:', rw(r, -1856)[0])
    print('RESULT: human wrench count %d -> %d ; cell %02x%02x -> %02x%02x' % (before[human], after[human], a0[0], a0[1], a1[0], a1[1]))
    r.close()
if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
