"""outside.py <a.ram> <b.ram>: the differing bytes outside the simulation regions of compare.py, attributed to the two
compose buffers (read from the pointers $2df7c / $2df78 in each dump, 32000 bytes each), the HUD master $78000, the
stack page above the second buffer, and the rest as raw ranges. Used to show that what differs is display, stack and
interrupt-counter state."""
import sys
sys.path.insert(0, __import__('os').path.dirname(__file__))
from compare import SIM, ranges
A, B = open(sys.argv[1], 'rb').read(), open(sys.argv[2], 'rb').read()
L = lambda R, a: int.from_bytes(R[a:a + 4], 'big')
bufs = sorted({L(A, 0x2df7c), L(A, 0x2df78), L(B, 0x2df7c), L(B, 0x2df78)})
areas = [(f'screen ${b:x}', b, b + 32000) for b in bufs] + [('hud_master $78000', 0x78000, 0x78000 + 32000)]
diff = [i for i in range(len(A)) if A[i] != B[i] and not any(lo <= i < hi for _, lo, hi in SIM)]
cnt = {n: 0 for n, _, _ in areas}; rest = []
for i in diff:
    for n, lo, hi in areas:
        if lo <= i < hi:
            cnt[n] += 1; break
    else:
        rest.append(i)
print('buffers a', hex(L(A, 0x2df7c)), hex(L(A, 0x2df78)), 'b', hex(L(B, 0x2df7c)), hex(L(B, 0x2df78)))
print('outside total', len(diff), {k: v for k, v in cnt.items() if v})
for lo, hi, c in ranges(rest, gap=8):
    print(f'  ${lo:x}..${hi:x} {c}  a={A[lo:min(hi + 1, lo + 8)].hex()} b={B[lo:min(hi + 1, lo + 8)].hex()}')
