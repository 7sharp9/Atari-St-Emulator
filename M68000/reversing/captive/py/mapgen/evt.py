"""Print selected records of an ATARI_TRACE_EVENTS log: evt.py <file> [lo hi] [kinds]"""
import struct, sys
KIND = {0:'seq',1:'bt',2:'bnt',3:'call',4:'ret',5:'trap',6:'irq'}
f = open(sys.argv[1], 'rb').read()
lo = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0
hi = int(sys.argv[3], 16) if len(sys.argv) > 3 else 1 << 32
kinds = set(int(k) for k in sys.argv[4].split(',')) if len(sys.argv) > 4 else None
for off in range(16, len(f) - 19, 20):
    st, pc, tg, op, k, fl = struct.unpack_from('<QIIHBB', f, off)
    if kinds is not None and k not in kinds: continue
    if lo <= (pc & 0xffffff) < hi or lo <= (tg & 0xffffff) < hi:
        print(f'{st} {pc:06x} -> {tg:06x} {KIND.get(k,k)}')
