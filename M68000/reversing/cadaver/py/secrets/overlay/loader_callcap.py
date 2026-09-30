"""loader_callcap.py: prove $0154b0 (the game's raw FDC read: D0 = linear sector = track*20 + side*10 + sector-1, D1 = sector count,
destination = A0) reads the overlay sectors, and that $0118ec (depacker: A0 = packed data after the 4-byte length, A1 = destination,
D0 = length) turns them into the RAM overlay.  Start snapshot scratchpad/cadaver/gameplay_empire.snap, disk mounted.
1. callcap 154b0 D0=401 D1=5 A0=$f0000 (delta to out/fdc_delta.json): the bytes at $f0000.. after the call (old RAM patched with
   the delta) must equal the .st bytes 401*512 .. 406*512.
2. poke the 2556 packed bytes (after the 4-byte length) at $f1004, callcap 118ec D0=$c10 A0=$f1004 A1=$f8000 (delta to
   out/depack_delta.json): $f8000.. must equal overlay_level0.bin (3088 bytes incl. the inner 4-byte length) and its last 3084
   bytes must equal RAM at $04c65e.  Expected: 2560/2560, 3088/3088, 3084/3084."""
import sys, json, os
sys.path.insert(0, 'reversing/cadaver/py/secrets/overlay')
from ov import *
sys.path.insert(0, 'tools')
from gfxview import load_ram
DISK = '../Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st'
disk = open(DISK, 'rb').read()
out = 'scratchpad/cadaver/secrets_out/overlay/out/'
ram, _ = load_ram('scratchpad/cadaver/gameplay_empire.snap')
def patched(delta, lo, n):
    b = bytearray(ram[lo:lo + n])
    for a, old, new in delta['mem']:
        if lo <= a < lo + n: b[a - lo] = new
    return bytes(b)
r = Repl()
o = r.cmd('callcap 154b0 3000000 %sfdc_delta.json D0=191 D1=5 A0=f0000' % out)
print([l for l in o if l.startswith('---')][0])
d = json.load(open(out + 'fdc_delta.json'))
got = patched(d, 0xf0000, 2560); want = disk[401 * 512:406 * 512]
print('FDC read sectors 401..405 into $f0000: %d/2560 bytes equal the .st bytes at $%x' % (sum(a == b for a, b in zip(got, want)), 401 * 512))
packed = want[4:]
for i in range(0, len(packed) - 3, 4): wl(r, 0xf1004 + i, int.from_bytes(packed[i:i + 4], 'big'))
size = int.from_bytes(want[:4], 'big')
o = r.cmd('callcap 118ec 20000000 %sdepack_delta.json D0=%x A0=f1004 A1=f8000' % (out, size))
print([l for l in o if l.startswith('---')][0])
d = json.load(open(out + 'depack_delta.json'))
got = patched(d, 0xf8000, size); want2 = open('scratchpad/cadaver/secrets_out/overlay/overlay_level0.bin', 'rb').read()
print('depack: %d/%d bytes of the output equal overlay_level0.bin' % (sum(a == b for a, b in zip(got, want2)), size))
print('depack tail vs RAM $04c65e: %d/%d' % (sum(got[4 + i] == ram[0x4c65e + i] for i in range(size - 4)), size - 4))
r.close()
