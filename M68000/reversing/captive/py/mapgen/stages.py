"""Per top-level call of an ATARI_TRACE_EVENTS log: target, start step and steps spent (calls made at call depth
`depth` relative to the first call record). stages.py <evt> [depth]"""
import struct, sys
f = open(sys.argv[1], 'rb').read()
want = int(sys.argv[2]) if len(sys.argv) > 2 else 1
depth = 0; open_ = None; rows = []
for off in range(16, len(f) - 19, 20):
    st, pc, tg, op, k, fl = struct.unpack_from('<QIIHBB', f, off)
    if k == 6: continue
    if k == 3:
        depth += 1
        if depth == want: open_ = (tg, st, pc)
    elif k == 4:
        if depth == want and open_:
            rows.append((open_[0], open_[1], st - open_[1], open_[2])); open_ = None
        depth -= 1
for tg, st, n, pc in rows:
    print(f'{pc:06x} -> {tg:06x}  start {st}  steps {n}')
