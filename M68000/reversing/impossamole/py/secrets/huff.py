"""Second layer: the MDATAn.DCH files, after LSD! depacking, are a static Huffman stream expanded by the routine at $018812.
Layout of the LSD!-depacked buffer (A0 at $53000):  u32 N (= output byte count), 1020-byte tree, then the bit stream as
big-endian words, MSB first.  Tree = words; node at A3 has children at (A3) [bit 0] / 2(A3) [bit 1];
a word with the sign bit set is a leaf whose low byte is the output byte; a non-negative word is a byte offset to the next node."""
import struct
def expand(buf):
    buf = bytes(buf) + b'\0' * 4          # the last word may run one byte past an odd-length buffer (RAM beyond is not part of the file)
    N = struct.unpack('>I', buf[:4])[0]
    tree = buf[4:]                      # A0
    stream = 4 + 1020                   # A2 = A0 + 1020
    out = bytearray()
    d1 = 0; d2 = 0
    pos = stream
    def word(o): return (tree_w(o))
    def tree_w(o): return struct.unpack('>H', buf[4+o:6+o])[0]
    while len(out) < N:
        a3 = 0
        while True:
            d1 -= 1
            if d1 < 0:
                d1 = 15
                d2 = struct.unpack('>H', buf[pos:pos+2])[0]; pos += 2
            bit = (d2 >> 15) & 1
            d2 = (d2 << 1) & 0xffff
            if bit: a3 += 2
            d3 = tree_w(a3)
            if d3 & 0x8000:
                out.append(d3 & 0xff)
                break
            a3 += d3
    return bytes(out), pos - 4
