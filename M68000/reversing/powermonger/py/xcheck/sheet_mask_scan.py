#!/usr/bin/env python3
"""Count sprite-sheet rows with plane bits under mask-1 pixels in a PowerMonger RAM image.
Both blitters OR the planes in unmasked (port/SPEC.md "Frame index per category"), so such a
pixel draws background | planes; a port that drops mask-1 pixels is exact only where this is 0.
Word sheets $312a0 (16 x 16, 47 frames), $37c7c (32 x 24, 27), $3af1c (32 x 32, 27): rows of
[mask, p0, p1, p2, p3] words per 16 px. Positive control: the $33000 byte sheet (8 x 11,
[mask, p0..p3] bytes), where frame $ab row 6 has one such pixel.
  uv run python <this> <ram> [...]"""
import sys

for path in sys.argv[1:]:
    b = open(path, 'rb').read()
    u = lambda a: (b[a] << 8) | b[a + 1]
    print(path)
    for name, base, stride, groups, rows, n in [("312a0", 0x312a0, 160, 1, 16, (0x33000 - 0x312a0) // 160),
                                               ("37c7c", 0x37c7c, 480, 2, 24, 27),
                                               ("3af1c", 0x3af1c, 640, 2, 32, 27)]:
        hits = []
        for f in range(n):
            for r in range(rows):
                for g in range(groups):
                    o = base + f * stride + r * groups * 10 + g * 10
                    m, p = u(o), u(o + 2) | u(o + 4) | u(o + 6) | u(o + 8)
                    if m & p:
                        hits.append((f, r, bin(m & p).count('1')))
        print(f"  ${name}: {n} frames, {len(hits)} rows, {sum(h[2] for h in hits)} px, frames {sorted({h[0] for h in hits})}")
    ctl = []
    for f in range(0x14a):
        for r in range(11):
            o = 0x33000 + f * 55 + r * 5
            m, p = b[o], b[o + 1] | b[o + 2] | b[o + 3] | b[o + 4]
            if m & p:
                ctl.append((hex(f), r, bin(m & p).count('1')))
    print(f"  $33000 control (frame, row, px): {ctl}")
