"""memdiff.py <snapA> <snapB> <lo> <hi> [pokesA...]: dump RAM [lo,hi) of two snapshots via REPL m, print differing ranges (merged within 16 bytes)."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import drv
a, b, lo, hi = sys.argv[1], sys.argv[2], int(sys.argv[3], 16), int(sys.argv[4], 16)
def dump(s):
    cmds = [f'm {x:x} {min(0x10000, hi-x):#x}' for x in range(lo, hi, 0x10000)]
    return b''.join(drv.mem(drv.run(s, cmds)))
A, B = dump(a), dump(b)
assert len(A) == len(B) == hi-lo, (len(A), len(B))
rng = []
for i in range(len(A)):
    if A[i] != B[i]:
        if rng and i - rng[-1][1] <= 16: rng[-1][1] = i
        else: rng.append([i, i])
tot = sum(e-s+1 for s, e in rng)
print(f'{len(rng)} ranges, {tot} bytes differ of {hi-lo}')
for s, e in rng[:int(os.environ.get('MAXR', 60))]:
    print(f'  ${lo+s:06x}..${lo+e:06x} ({e-s+1}B) A={A[s:s+8].hex()} B={B[s:s+8].hex()}')
