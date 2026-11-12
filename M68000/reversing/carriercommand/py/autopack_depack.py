#!/usr/bin/env python3
"""Depacker for 'AUTOMATION PACKER V2.3r' PRGs, transcribed from the 68000 stub's depack
loop ($a4ce..$a61c when PACT2.PRG's text loads at $a304). Doc: ../packer.md.

usage: autopack_depack.py in.PRG out.PRG     write the unpacked GEMDOS PRG
       autopack_depack.py --gap in.PRG...    print the closest approach of the write
                                             pointer to the unread stream (in-place safety)

Agrees byte for byte with tools/lsd_depack.py on the payload (same LSD! bitstream)."""
import sys, struct

LIT_BITS = [10, 3, 2, 2]; LIT_BASE = [14, 7, 4, 1]          # stub $a53a
LEN_BITS = [10, 2, 1, 0, 0]; LEN_BASE = [10, 6, 4, 3, 2]    # stub $a594
OFF_BITS = [11 + 1, 4 + 1, 7 + 1]; OFF_BASE = [288, 0, 32]  # stub $a5d8 (counts stored minus 1)

def depack(p, track=None):
    """p = payload bytes (stub's data at $a61e). returns unpacked image."""
    size = struct.unpack('>I', p[4:8])[0]
    plen = struct.unpack('>I', p[8:12])[0]
    pos = 8 + plen - 4                      # $a4da-$a4dc
    pos -= 2                                # tst.w -(A0)
    if p[pos] & 0x80: pos -= 1              # tst.w/bpl skips the subq.l when positive (a4e2-a4e6)
    stop = 4 + 8
    out = bytearray(size); a1 = size        # A1 counts down from the end
    st = {'pos': pos, 'd0': 0, 'first': True}
    def rdbyte():
        st['pos'] -= 1; return p[st['pos']]
    d0 = rdbyte()                           # $a4e8
    def bit():
        nonlocal d0
        c = d0 >> 7; d0 = (d0 << 1) & 0xff
        if d0 == 0 and not (c is None):
            pass
        return c
    # faithful lsl.b / refill / roxl.b: when lsl leaves 0, the shifted-out bit was the sentinel
    def getbit():
        nonlocal d0
        c = (d0 >> 7) & 1; d0 = (d0 << 1) & 0xff
        if d0 == 0:                         # bne not taken: refill, roxl.b with X = c
            nb = rdbyte()
            c2 = nb >> 7
            d0 = ((nb << 1) | c) & 0xff
            return c2
        return c
    def bits(n):                            # MSB first
        v = 0
        for _ in range(n): v = (v << 1) | getbit()
        return v
    while True:
        if getbit():                        # literal run present
            if not getbit(): n = 0
            else:
                d3 = 3
                while True:
                    v = bits(LIT_BITS[d3])
                    if d3 and v == (1 << LIT_BITS[d3]) - 1: d3 -= 1; continue
                    break
                n = v + LIT_BASE[d3]
            for _ in range(n + 1):
                a1 -= 1; out[a1] = rdbyte()
                if track: track(a1, st['pos'])
        if st['pos'] <= stop: break         # $a54e
        k = 3
        while k >= 0 and getbit(): k -= 1   # unary, up to 4 ones
        k += 1                              # 0 ('1111') .. 4 ('0')
        ln = bits(LEN_BITS[k]) + LEN_BASE[k]
        if ln == 2:
            if getbit(): off = bits(9) + 64
            else: off = bits(6)
        else:
            t = 1
            while t >= 0 and getbit(): t -= 1
            t += 1                          # 0 '11', 1 '10', 2 '0'
            off = bits(OFF_BITS[t]) + OFF_BASE[t]
        a2 = a1 + off + ln
        for _ in range(ln):
            a2 -= 1; a1 -= 1; out[a1] = out[a2]
            if track: track(a1, st['pos'])
    return bytes(out), a1, st['pos']

DEST_OFS = 0x400   # stub $a31c: depack destination = tbase + $400


def unpack_prg(path, track=None):
    d = open(path, 'rb').read()
    tl, dl = struct.unpack('>II', d[2:10])
    payload = d[0x1c + tl: 0x1c + tl + dl]
    return depack(payload, track), tl


def min_gap(path):
    """Smallest (address of the byte just written) - (address of the lowest stream byte
    not yet consumed), both relative to tbase. The payload starts at tbase + text length,
    the output at tbase + DEST_OFS; the in-place depack is safe while this stays > 0."""
    m = [None]
    tl = struct.unpack('>I', open(path, 'rb').read()[2:6])[0]
    def track(a1, pos):
        g = (DEST_OFS + a1) - (tl + pos)
        if m[0] is None or g < m[0]: m[0] = g
    (out, _, _), _ = unpack_prg(path, track)
    return len(out), tl, m[0], DEST_OFS - (tl + 12)

if __name__ == '__main__':
    if sys.argv[1] == '--gap':
        for f in sys.argv[2:]:
            n, tl, g, final = min_gap(f)
            print(f'{f}: unpacked {n} text ${tl:x} min gap {g} final gap {final}')
        sys.exit(0)
    (out, a1, pos), _ = unpack_prg(sys.argv[1])
    print('size', len(out), 'a1 at end', a1, 'stream pos', pos, file=sys.stderr)
    open(sys.argv[2], 'wb').write(out)
