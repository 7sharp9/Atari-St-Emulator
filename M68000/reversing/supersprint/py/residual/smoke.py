"""Python transcription of the smoke-puff system: spawner $b6f8(car, p), per-frame updater $afc6, and the 8x8 puff blitter $143ca(slot).
State (word arrays off A4): x,y of slot i at -4598+4i / -4596+4i (x == 0 means the slot is free), frame -4614+2i, end frame -4630+2i, tick -4646+2i,
dirty-rect word -4678+16*(frame parity)+2i; heading offset table -4566+8*heading (4 words: dx1 dy1 dx2 dy2).  Puff frames: B5 + $1240 + 32*frame
(8 rows x 4 plane bytes).  `mem` is a bytearray of the whole RAM (a shadow); functions mutate it."""
import struct

A4 = 0x1EB44
def gw(m, a): return struct.unpack_from('>h', m, a)[0]
def pw(m, a, v): struct.pack_into('>H', m, a, v & 0xFFFF)
def gl(m, a): return struct.unpack_from('>I', m, a)[0]


def spawn(m, car, p):
    """$b6f8(car, p): two puffs behind car `car` (slots 2*car, 2*car+1)"""
    c2 = car * 2
    x = gw(m, A4 - 3690 + c2); y = gw(m, A4 - 3698 + c2); h = gw(m, A4 - 3706 + c2)
    c2 = car * 4                                              # slot pair 2*car, 2*car+1 in the 2-byte arrays
    t = A4 - 4566 + (h << 3)
    x1 = x + gw(m, t); y1 = y + gw(m, t + 2) - 4
    x2 = x + gw(m, t + 4); y2 = y + gw(m, t + 6) - 4
    s = (((p & 0xFFFF) >> 1) + 1) & 7; s5 = s * 4 + s            # start frame 5*s (D6<<2 + D6)
    d3 = car * 8                                              # and in the 4-byte (x, y) array
    pw(m, A4 - 4598 + d3, x1); pw(m, A4 - 4596 + d3, y1)
    pw(m, A4 - 4614 + c2, s5); e = s5 + 5; pw(m, A4 - 4630 + c2, e)
    pw(m, A4 - 4598 + d3 + 4, x2); pw(m, A4 - 4598 + d3 + 6, y2)
    e2 = e - 15                                              # subi.w #$f
    if e2 < 0: e2 += 0x28
    pw(m, A4 - 4614 + c2 + 2, e2); pw(m, A4 - 4630 + c2 + 2, e2 + 5)
    struct.pack_into('>I', m, A4 - 4646 + c2, 0)             # clr.l: ticks of both slots


def draw_puff(m, slot, b5, parity, screen):
    """$143ca(slot)"""
    fr = gw(m, A4 - 4614 + 2 * slot)
    src = 0x1240 + ((fr << 5) & 0xFFFF)
    x = gw(m, A4 - 4598 + 4 * slot)
    if x == 0: return
    y = struct.unpack_from('>H', m, A4 - 4596 + 4 * slot)[0]
    xx = x & 0xFFFF
    d0 = xx >> 1
    off = ((d0 & 0xFFF8) + ((d0 >> 2) & 1) + (y * 0xA0)) & 0xFFFF
    off = off - 0x10000 if off >= 0x8000 else off           # adda.w: sign-extended word
    pw(m, A4 - 4678 + (parity & 1) * 16 + 2 * slot, off & 0xFFFF)
    a = screen + off
    for r in range(8):
        d0, d1, d2, d3 = b5[src + r * 4:src + r * 4 + 4]
        d4 = (~d3 | d0 | d1 | d2) & 0xFF
        d3 &= d4; keep = ~d4 & 0xFF
        for k, v in enumerate((d0, d1, d2, d3)):
            m[a + 2 * k] = (m[a + 2 * k] & keep) | v
        a += 160


def update(m, b5, parity, screen):
    """$afc6: advance the 8 slots one frame; draw the live ones"""
    for i in range(8):
        i2 = i * 2
        t = (gw(m, A4 - 4646 + i2) + 1); pw(m, A4 - 4646 + i2, t)
        if (t & 0xFFFF) == 4 and gw(m, A4 - 4614 + i2) < 0x28:
            pw(m, A4 - 4614 + i2, gw(m, A4 - 4614 + i2) + 1); pw(m, A4 - 4646 + i2, 0)
        f = gw(m, A4 - 4614 + i2)
        if f == 0x2A:
            pw(m, A4 - 4598 + 4 * i, 0)                       # muls #2 then asl #1: 4*i
        elif f == gw(m, A4 - 4630 + i2):
            pw(m, A4 - 4614 + i2, 0x2A)
        else:
            draw_puff(m, i, b5, parity, screen)
