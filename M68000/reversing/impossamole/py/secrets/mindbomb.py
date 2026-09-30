"""MINDBOMB.PRG stub ($c6-$196): a second packer on this disk (MSB-first bit reader: add.l D7,D7 / addx sentinel refill from longwords fetched backwards;
$128 = variable-length number, $17a = 8 raw bits).  Header (file offsets): u32 unpacked length U at $196, u32 P at $19a; the stream ends at $19e+P and is read backwards,
output is written backwards from $596+U.  The unpacked image is itself a PRG (header 601a) which the stub relocates ($1c-$70)."""
import struct, sys
def depack(prg, T=0):          # offsets below are file offsets (the stub's PC-relative operands were disassembled with the file base 0)
    U, P = struct.unpack('>II', prg[T+0x196:T+0x19e])
    end = T + 0x19e + P
    pos = end
    st = {'d7': 0}
    def refill():
        nonlocal pos
        pos -= 4
        w = struct.unpack('>I', prg[pos:pos+4])[0]
        d = ((w << 1) | 1) & 0xffffffff
        c = (w >> 31) & 1
        st['d7'] = d
        return c
    def bit():
        d = st['d7']; c = (d >> 31) & 1
        d = (d << 1) & 0xffffffff
        st['d7'] = d
        if d == 0: return refill()
        return c
    def bits(n):                                    # roxr.b/w #1 accumulation: the FIRST bit read ends up as the LSB
        v = 0
        for k in range(n): v |= bit() << k
        return v
    def number():                                   # $128
        if bit():
            return bits(16) if bit() else bits(8)
        return bits(12) if bit() else bits(4)
    out = bytearray(U); a1 = U
    first = refill()
    c = first
    while True:
        if not c:                                    # literal run: count, then that many bytes
            n = number(); n = n or 65536
            for _ in range(n):
                a1 -= 1; out[a1] = bits(8)
            if a1 <= 0: break
            c = bit()
            if not c: continue
        # match: offset, count
        off = number(); n = number() or 65536
        for _ in range(n):
            a1 -= 1; out[a1] = out[a1 + off] if a1 + off < U else 0
        if a1 <= 0: break
        c = bit()
    return bytes(out), pos
if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    o, pos = depack(d)
    print('unpacked', len(o), 'stream pos', pos, 'head', o[:28].hex(' '))
    open(sys.argv[2], 'wb').write(o)
