"""Read an ATARI_TRACE_EVENTS file: records <QIIHBB> (step, pc, target, opcode, kind, flags), 16-byte header."""
import struct, sys
REC = struct.Struct('<QIIHBB')
def read(path):
    b = open(path, 'rb').read()
    out = []
    for o in range(16, len(b) - REC.size + 1, REC.size):
        out.append(REC.unpack_from(b, o))
    return out
if __name__ == '__main__':
    ev = read(sys.argv[1])
    # region timeline: print runs of consecutive records whose pc falls in the same 4K page
    last = None; start = None; n = 0
    for i, (st, pc, tg, op, k, f) in enumerate(ev):
        reg = (pc & 0xffffff) >> 12
        if reg != last:
            if last is not None:
                print(f'{start:8d}..{i-1:8d} n={n:7d} page ${last<<12:06x}')
            last = reg; start = i; n = 0
        n += 1
    print(f'{start:8d}..{len(ev)-1:8d} n={n:7d} page ${last<<12:06x}')
