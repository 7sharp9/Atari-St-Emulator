# loader for poolrec.lua output
import struct, sys
FR = 4 + 2048 + 384 + 192 * 13 + 256 + 192 * 16
class Frame:
    def __init__(s, b):
        s.f = struct.unpack('>I', b[:4])[0]; s.a5 = b[4:2052]; s.pl = [b[2052 + 192 * i: 2052 + 192 * (i + 1)] for i in range(2)]
        s.p2 = [b[2436 + 192 * i: 2436 + 192 * (i + 1)] for i in range(13)]
        s.lo = b[2436 + 192 * 13: 2436 + 192 * 13 + 256]  # $ff1100..$ff11ff
        o = 2436 + 192 * 13 + 256
        s.props = [b[o + 192 * i: o + 192 * (i + 1)] for i in range(16)]  # pool $a at $ffb2e8

    def l(s, addr, n=1):  # byte(s) at $ff1100+..
        o = addr - 0xff1100; return int.from_bytes(s.lo[o:o + n], 'big')
    def a(s, off, n=1):  # A5-relative byte(s) (offset < 2048)
        return int.from_bytes(s.a5[off:off + n], 'big')
def load(path):
    b = open(path, 'rb').read()
    return [Frame(b[i * FR:(i + 1) * FR]) for i in range(len(b) // FR)]
def u8(r, o): return r[o]
def u16(r, o): return int.from_bytes(r[o:o + 2], 'big')
def s16(r, o):
    v = u16(r, o); return v - 65536 if v >= 32768 else v
def u32(r, o): return int.from_bytes(r[o:o + 4], 'big')
if __name__ == '__main__':
    fs = load(sys.argv[1])
    print(len(fs), fs[0].f, fs[-1].f)
    for fr in fs[:1]:
        for i, r in enumerate(fr.p2):
            print(i, r[:4].hex(), 'tag', r[18], 'kind', r[19], 'w20', u16(r, 20), 'b21', r[21], 'x', u16(r, 6), 'y', u16(r, 10), 'hp', u16(r, 24), 'p92 %x' % u32(r, 92), 'p56 %x' % u32(r, 56))
