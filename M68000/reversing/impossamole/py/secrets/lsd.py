"""LSD! depacker: exact transcription of the resident TRAP #1 hook at $000242 (code $200-$3c2 in low RAM).
Format: 'LSD!' tag, u32 unpacked length U, u32 packed length P, packed stream read BACKWARDS from
file[4+P] (byte at 4+P-1 downwards, after an optional pad byte) down to file offset 12; output written
BACKWARDS from dest+U down to dest.  Bit buffer = byte with sentinel: lsl.b/roxl.b (MSB first)."""
import struct

TAB_LIT_BITS = [0x0a, 0x03, 0x02, 0x02]       # $2da  (index D3)
TAB_LIT_BASE = [0x0e, 0x07, 0x04, 0x01]       # $2de
TAB_LEN_BITS = [0x0a, 0x02, 0x01, 0x00, 0x00] # $336  (index D2)
TAB_LEN_BASE = [0x0a, 0x06, 0x04, 0x03, 0x02] # $33b
TAB_OFF_BITS = [0x0b, 0x04, 0x07]             # $37a  (index D3), count = bits+1
TAB_OFF_BASE = [0x0120, 0x0000, 0x0020]       # $37e

class Stop(Exception): pass

def depack(f, trace=None):
    assert f[:4] == b'LSD!'
    U, P = struct.unpack('>II', f[4:12])
    src = f[4:] + b'\0\0'             # the copy at $60000 (a PRG-embedded payload can be a byte short of its header: MST.IMG)
    a0 = 4 + P                       # A0 after (A0)+ ; adda (A0),A0  -> $60004+P ; subq 4 -> $60000+P
    a0 = P                           # = $60000 + P as offset into src
    a0 -= 2                          # tst.w -(A0)
    w = (src[a0] << 8) | src[a0 + 1]
    if w & 0x8000:
        a0 -= 1                      # subq.l #1,A0
    a0 -= 1; d5 = src[a0]            # move.b -(A0),D5
    out = bytearray(U)               # out[i] is dest byte i; A1 is an index (end = U)
    a1 = U
    state = {'a0': a0, 'd5': d5}
    def getbit():
        d5 = state['d5']
        c = (d5 >> 7) & 1
        d5 = (d5 << 1) & 0xff
        if d5 == 0:
            state['a0'] -= 1
            d5 = src[state['a0']]
            c2 = (d5 >> 7) & 1
            d5 = ((d5 << 1) & 0xff) | c
            state['d5'] = d5
            return c2
        state['d5'] = d5
        return c
    def bits(n):                     # n bits MSB first
        v = 0
        for _ in range(n):
            v = (v << 1) | getbit()
        return v
    nlit = nmatch = 0
    while True:
        if getbit():                                  # literal run
            if not getbit():
                d1 = 0
            else:
                d3 = 3
                while True:
                    nb = TAB_LIT_BITS[d3]
                    d1 = bits(nb)
                    if d3 == 0: break
                    if d1 != (1 << nb) - 1: break
                    d3 -= 1
                d1 += TAB_LIT_BASE[d3]
            for _ in range(d1 + 1):
                state['a0'] -= 1
                a1 -= 1
                out[a1] = src[state['a0']]
            nlit += d1 + 1
        if state['a0'] <= 8:
            break
        d2 = 3
        k = 0
        while k < 4 and getbit():
            k += 1
        d2 = 4 - k
        d1 = bits(TAB_LEN_BITS[d2]) + TAB_LEN_BASE[d2]
        if d1 == 2:
            if getbit():
                off = bits(9) + 64
            else:
                off = bits(6)
        else:
            k = 0
            while k < 2 and getbit():
                k += 1
            d3 = 2 - k
            off = bits(TAB_OFF_BITS[d3] + 1) + TAB_OFF_BASE[d3]
        # A2 = A1 + off + d1 ; copy d1 bytes backwards
        a2 = a1 + off + d1
        for _ in range(d1):
            a2 -= 1; a1 -= 1
            out[a1] = out[a2]
        nmatch += 1
        if trace is not None: trace.append((d1, off))
    return bytes(out), a1, nlit, nmatch

if __name__ == '__main__':
    import sys
    for n in sys.argv[1:]:
        f = open(n, 'rb').read()
        o, a1, nl, nm = depack(f)
        print(n, len(f), len(o), 'a1=', a1, 'lit', nl, 'matches', nm)
