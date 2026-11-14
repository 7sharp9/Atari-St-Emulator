"""classify.py <a.snap> <b.snap> [lo hi]: RAM diff of two snapshots over [lo,hi) (default $400..$70000) with every differing
range assigned to a named region of the Virus memory map, and the bytes per region.  Prints the pilot, selector, score and RNG
regions byte by byte when they differ."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import drv
a, b = sys.argv[1], sys.argv[2]
lo = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x400; hi = int(sys.argv[4], 16) if len(sys.argv) > 4 else 0x70000
REG = [(0x2706e, 0x27076, 'RNG $2706e..$27075'), (0x62a5b, 0x62a71, 'selectors $62a5b..$62a70'),
       (0x2708e, 0x270a1, 'score block $2708e..$270a0'), (0x270a2, 0x270b0, 'pilot state $270a2..$270af'),
       (0x270b0, 0x270d4, 'ship $270b0..$270d3'), (0x31d54, 0x32a2e, 'pool $31d54..$32a2d'),
       (0x32a58, 0x42a58, 'object map $32a58..$42a57'), (0x42a58, 0x52a58, 'height map'),
       (0x6e000, 0x70000, 'stack $6e000..$6ffff'), (0xc000, 0x27000, 'code and tables $c000..$26fff'),
       (0x27000, 0x31d54, 'variables $27000..$31d53'), (0x32a2e, 0x32a58, 'game words $32a2e..$32a57'),
       (0x400, 0xc000, 'low RAM and TOS $400..$bfff'), (0x52a58, 0x6e000, 'screens, buffers $52a58..$6dfff')]
def name(x):
    for s, e, n in REG:
        if s <= x < e: return n
    return 'other'
def dump(s):
    cmds = [f'm {x:x} {min(0x10000, hi-x):#x}' for x in range(lo, hi, 0x10000)]
    return b''.join(drv.mem(drv.run(s, cmds)))
A, B = dump(a), dump(b)
assert len(A) == len(B) == hi-lo, (len(A), len(B))
tally = {}; first = {}
for i in range(len(A)):
    if A[i] != B[i]:
        n = name(lo+i); tally[n] = tally.get(n, 0) + 1; first.setdefault(n, lo+i)
        if n in ('RNG $2706e..$27075', 'selectors $62a5b..$62a70', 'score block $2708e..$270a0', 'pilot state $270a2..$270af'):
            print(f'  ${lo+i:06x} A={A[i]:02x} B={B[i]:02x}   ({n})')
print('bytes differing by region:')
for n, c in sorted(tally.items(), key=lambda t: -t[1]): print(f'  {c:6d}  {n}   (first ${first[n]:06x})')
print('total', sum(tally.values()), 'of', hi-lo)
