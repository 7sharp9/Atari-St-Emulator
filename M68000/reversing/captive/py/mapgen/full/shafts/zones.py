"""Python model of fed_MapGen's first stage (the base's floor plan) and its emulator gate.

    uv run python -I reversing/captive/py/mapgen/zones.py model <d0>          # print the 4x4 block table, floor offsets and entry for one seed
    uv run python -I reversing/captive/py/mapgen/zones.py gate <lo> <hi>      # emulator vs model for D0 = lo..hi-1 (D2 = 1), match count

Model (transcribed from the decrypted module, runtime addresses with the module at $1f7b0, A6 = $20376):
  $23b96 rng        x = (x * $5e5 + $29) mod 2^16 in 12404(A6), seeded with the D0 argument; returns ror16(x, 4) ^ $800
  $2011e blocks     16 blocks of 16x8 cells (a 4x4 grid over the 64x32 map); mask table $20110 indexed by min(D0, 6)
                    marks which blocks belong to the base (bit 15 = block 0); the rest get 6 (outside); then 2..5
                    floors (1 when D0 = 0) each grow by a random walk from a random empty block until it leaves the
                    grid or meets another floor; leftover empty blocks copy a random neighbour
  $201de offsets    for each floor k < last: a random block of floor k and of floor k+1; the block-coordinate
                    difference x16, x8 is stored at 16(A6)/24(A6): the translation a lift applies ($25136/$2514c)
  $20252 entry      random column 0..63 with (col & 15) != 15 at 32(A6), its top-row block's floor at 34(A6);
                    D0 = 0 replaces the table by one 3-block column (block 1, 5, 9) and the column by 30
  $202a2 G0 init    64x32 words at 56(A6): $ffff on the right column / bottom row of a block whose right / lower
                    neighbour is a different floor, else 0
Gate: from mg_ret.snap, call $20054 (labelled pokes as gen.py) and stop at $23c92 (the return from $202a2); compare
module bytes 0..55, the RNG word 12404(A6) and all 4096 bytes of G0 with the model.
"""
import os
import sys

MASKS = [0xcc00, 0xf600, 0xff00, 0xff60, 0xfff0, 0xfff6, 0xffff]  # $20110
DX4 = [0, 1, 0, -1]   # $20366, block step in x
DY4 = [4, 0, -4, 0]   # $2036e, block step in y (index units: 4 per block row)


def ror16(v, n):
    n &= 15
    v &= 0xffff
    return ((v >> n) | (v << (16 - n))) & 0xffff


class Rng:
    def __init__(self, seed):
        self.x = seed & 0xffff

    def __call__(self):  # $23b96
        self.x = (self.x * 0x5e5 + 0x29) & 0xffff
        return ror16(self.x, 4) ^ 0x800


def plan(d0):
    rng = Rng(d0)
    mask = MASKS[min(d0, 6)]
    t = [0] * 16
    free = 16
    for i in range(16):             # rol.w #1 then test bit 0: block i takes mask bit 15-i
        if not (mask >> (15 - i)) & 1:
            t[i] = 6
            free -= 1
    nz = ((ror16(rng(), 1)) & 3) + 2   # $20150: drawn even when D0 = 0
    if d0 == 0:
        nz = 1
    global LAST_NZ
    LAST_NZ = nz                    # the drawn floor count, kept at 12418(A6) (shafts/chain.py)

    def pick():                     # $20328: col D4 = r' & 3, row*4 D5 = r' & 12 with r' = ror(r, r)
        r = rng()
        r = ror16(r, r & 63)
        return r & 3, r & 12

    def step(c, rw):                # $2033e: a random one-block step, oob when unsigned col > 3 or row*4 > 12
        r = rng()
        k = (ror16(r, r & 63) & 6) // 2
        c2, r2 = (c + DX4[k]) & 0xffff, (rw + DY4[k]) & 0xffff
        return c2, r2, c2 > 3 or r2 > 12

    z = 1
    done = False
    while z <= nz:                  # $2016a..$20194
        while True:
            c, rw = pick()
            if t[c + rw] == 0:
                break
        free -= 1
        t[c + rw] = z
        while True:
            if free == 0:
                done = True
                break
            c, rw, oob = step(c, rw)
            if oob:
                break
            v = t[c + rw]
            if v == 0:
                free -= 1
                t[c + rw] = z
                continue
            if v == z:
                continue
            break
        if done:
            break
        z += 1
    if not done:
        z = nz
    while free:                     # $2019a..$201da: an empty block copies a random neighbour (up to 4 tries)
        while True:
            c, rw = pick()
            if t[c + rw] == 0:
                break
        for _ in range(4):
            c2, r2, oob = step(c, rw)
            if oob:
                continue
            v = t[c2 + r2]
            if v == 0:
                continue
            t[c + rw] = v
            free -= 1
            break
    nfloors = z
    offs = [0] * 8
    last = (0, 0)
    for k in range(1, nfloors):     # $201de
        def find(want):
            i = rng() & 15
            while t[i] != want:
                i = (i + 1) & 15
            return i & 3, (i >> 2) & 3
        x0, y0 = find(k)
        x1, y1 = find(k + 1)
        last = (x0, y0)
        offs[k - 1] = ((x1 - x0) << 4) & 0xffff
        offs[k + 3] = ((y1 - y0) << 3) & 0xffff
    while True:                     # $20252
        e = rng() & 63
        if (e & 15) != 15:
            break
    if d0 == 0:
        t = [6, 1, 6, 6, 6, 1, 6, 6, 6, 1, 6, 6, 6, 6, 6, 6]
        e = 30
    v = bytearray(56)
    v[0:16] = bytes(t)
    for i in range(8):
        v[16 + 2 * i:18 + 2 * i] = offs[i].to_bytes(2, 'big')
    v[32:34] = e.to_bytes(2, 'big')
    v[34:36] = t[e >> 4].to_bytes(2, 'big')
    v[46:48] = nfloors.to_bytes(2, 'big')
    if nfloors > 1:
        v[48:50] = last[0].to_bytes(2, 'big')
        v[50:52] = last[1].to_bytes(2, 'big')
    g0 = [0] * 2048                 # $202a2
    for br in range(4):
        tb = t[4 * br:4 * br + 4]
        below = t[4 * br + 4:4 * br + 8] if br < 3 else None
        for yy in range(7):
            y = 8 * br + yy
            for bc in range(4):
                if bc < 3 and tb[bc + 1] != tb[bc]:
                    g0[64 * y + 16 * bc + 15] = 0xffff
        y = 8 * br + 7
        for bc in range(4):
            w = 0xffff if below is not None and below[bc] != tb[bc] else 0
            for x in range(16 * bc, 16 * bc + 16):
                g0[64 * y + x] = 0xffff if g0[64 * (y - 1) + x] else w
    return bytes(v), rng.x, b''.join(w.to_bytes(2, 'big') for w in g0)


def gate(lo, hi):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gen import R, MA6, start
    from stclient import StServer
    s = StServer(R)
    ok = 0
    bad = []
    try:
        for d0 in range(lo, hi):
            start(s, d0, 0, 1, 0, stops=[0x23c92], max_steps=2_000_000)
            if s.reg('pc') != 0x23c92:
                bad.append((d0, 'did not stop at $23c92'))
                continue
            ev = s.read(MA6, 56)
            ex = int.from_bytes(s.read(MA6 + 12404, 2), 'big')
            eg = s.read(MA6 + 56, 4096)
            mv, mx, mg = plan(d0)
            if (ev, ex, eg) == (mv, mx, mg):
                ok += 1
            else:
                bad.append((d0, ev.hex(), mv.hex(), ex, mx, sum(a != b for a, b in zip(eg, mg))))
    finally:
        s.close()
    print(f'match {ok}/{hi - lo} (module bytes 0..55, rng word 12404(A6), G0 4096 bytes at the return from $202a2)')
    for b in bad[:10]:
        print('MISMATCH', b)


def show(d0):
    v, x, g = plan(d0)
    t = v[:16]
    print('blocks (row by row; 6 = outside the base):')
    for r in range(4):
        print('  ', ' '.join(str(b) for b in t[4 * r:4 * r + 4]))
    nf = int.from_bytes(v[46:48], 'big')
    print('floors', nf, 'entry column', int.from_bytes(v[32:34], 'big'), 'entry floor', int.from_bytes(v[34:36], 'big'))
    for k in range(nf - 1):
        dx = int.from_bytes(v[16 + 2 * k:18 + 2 * k], 'big', signed=True)
        dy = int.from_bytes(v[24 + 2 * k:26 + 2 * k], 'big', signed=True)
        print(f'  lift floor {k + 1} -> {k + 2}: (x, y) + ({dx}, {dy})')


if __name__ == '__main__':
    if sys.argv[1] == 'gate':
        gate(int(sys.argv[2]), int(sys.argv[3]))
    else:
        show(int(sys.argv[2]))
