"""Pack-Ice 2.x ('ICE!') depacker, transcribed from the depack stub inside STAR.BIN itself (runtime $ac3c..$acee,
tables $acee..$ad2a; the file bytes sit at STAR.BIN offset $1c + (addr - $ab8c)). Not from memory of the format:
every table value below is read out of that stub (see frontend.md "Boot").

usage: ice_depack.py <in.ICE!-file> <out>

Header: 'ICE!', packed length (whole file, header included), unpacked length. The stream is read backwards from the
end of the packed data; the first byte is the bit buffer; bits come out MSB first through `add.b D7,D7` with a
sentinel reload (`move.b -(A5),D7 / addx.b D7,D7`). Output is written from its end backwards."""
import struct, sys

LIT_BITS = (2, 2, 3, 8, 15)                 # $acee longs, low word + 1 bits read, high word = all-ones test
LIT_CMP = (3, 3, 7, 0xFF, 0x7FFF)           # stub order is table end first: k=0 is the LAST long
LIT_ADD = (1, 4, 7, 0x0E, 0x10D)            # add.l 20(A1),D1 for k=0..4
LEN_BITS = {3: -1, 2: -1, 1: 0, 0: 1, -1: 9}     # byte 1(A1,D2) sign-extended: <0 = no extra bits read
LEN_ADD = {3: 0, 2: 1, 1: 2, 0: 4, -1: 8}        # byte 6(A1,D2)
OFF_BITS = {1: 7, 0: 4, -1: 0x0B}                # byte 1(A1,D2) of the offset table; ac74 reads D0+1 bits
OFF_ADD = {1: 0x1F, 0: -1, -1: 0x11F}            # word 6(A1,2*D2)


def depack(buf):
    assert buf[:4] == b'ICE!'
    plen, size = struct.unpack('>II', buf[4:12])
    src = plen                    # A5: end of packed data
    out = bytearray(size)
    q = size                      # A6
    st = {'d7': 0}

    def nb():
        nonlocal src
        src -= 1
        return buf[src]

    st['d7'] = nb()

    def bit():
        d7 = st['d7'] << 1
        c = d7 >> 8
        d7 &= 0xFF
        if d7 == 0:                           # bne not taken: reload, addx.b D7,D7 (X = c of the add)
            d7 = nb()
            t = d7 + d7 + c
            c = t >> 8
            d7 = t & 0xFF
        st['d7'] = d7
        return c

    def bits(n):                              # ac74: reads n+1 bits (dbf D0), n is the D0 value
        v = 0
        for _ in range(n + 1):
            v = (v << 1) | bit()
        return v

    def put(b):
        nonlocal q
        q -= 1
        out[q] = b

    while True:
        if bit():                             # literal run follows
            d1 = 0
            if bit():
                for k in range(5):
                    d1 = bits(LIT_BITS[k] - 1)
                    if d1 != LIT_CMP[k] or k == 4:
                        break
                d1 += LIT_ADD[k]
            for _ in range(d1 + 1):
                put(nb())
        if q <= 0:
            break
        d2 = 3
        while True:
            c = bit()
            if not c:
                break
            d2 -= 1
            if d2 == -1:
                break
        d0 = LEN_BITS[d2]
        d1 = bits(d0) if d0 >= 0 else 0
        d4 = (LEN_ADD[d2] + d1) & 0xFFFF
        if d4 == 0:
            d1 = 0
            d0, d2 = 5, -1
            if bit():
                d0, d2 = 8, 63
            d1 = bits(d0) + d2
        else:
            d2 = 1
            while True:
                if not bit():
                    break
                d2 -= 1
                if d2 == -1:
                    break
            d1 = bits(OFF_BITS[d2])
            d1 = (d1 + OFF_ADD[d2]) & 0xFFFF
            if d1 & 0x8000:                   # bpl not taken
                d1 = (d1 - d4) & 0xFFFF
        d1 &= 0xFFFF
        if d1 & 0x8000:
            d1 -= 0x10000
        a1 = q + 2 + d4 + d1
        for _ in range(d4 + 2):
            a1 -= 1
            put(out[a1])
    depack.src_end = src
    return bytes(out)


if __name__ == '__main__':
    d = depack(open(sys.argv[1], 'rb').read())
    open(sys.argv[2], 'wb').write(d)
    print(len(d))
