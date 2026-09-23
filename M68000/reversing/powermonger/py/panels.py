"""Expand PowerMonger panel templates as $a91a does and list every button ($80 marker) offset."""
import sys
R = open(sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/pm121/run/k60_s2.ram', 'rb').read()
codes = []
a = 0xa99c
while R[a]:
    codes.append(R[a]); a += 1
MAP = {c: R[0xa99c + i + 25] for i, c in enumerate(codes)}
def expand(t):
    out = bytearray(R[t:t+2]); p = t + 2
    while R[p]:
        b = R[p]; p += 1
        if b & 0x80 and b in MAP:
            b = MAP[b]
        out.append(b)
    return out
PANELS = {2: 0x921a, 4: 0xb03a, 6: 0xb0ad, 8: 0xb160, 0xa: 0xb510, 0xc: 0xbb66, 0xe: 0xbfda,
          0x10: 0xcd82, 0x12: 0xc332, 0x14: 0xd048, 0x18: 0xc512, 0x1a: 0xc820}
def show(b):
    return chr(b) if 32 <= b < 127 else {0x80: '[', 0x81: '-', 0x82: ']', 0x83: '|', 0x84: '|'}.get(b, '.')
for pid, t in PANELS.items():
    g = expand(t); w = g[0] * 4; h = g[1]; body = g[2:]
    print(f"panel {pid:#x} template ${t:x}  {w}x{h}  (body {len(body)} bytes)")
    for r in range(h):
        print(f"  {r*w:4x} " + ''.join(show(x) for x in body[r*w:(r+1)*w]))
    btn = [i for i, x in enumerate(body) if x == 0x80]
    for i in btn:
        lab = bytes(body[i+w:i+2*w]).split(b'\x84')[0][1:]
        print(f"    button D3=${i:x}: {lab.decode('latin1')!r}")
