"""Bitmap font + text blitter of Super Sprint.

Font: 42 glyphs x 8 bytes at -7770(A4) (identical to SUPER.DAT tail[0:336]); glyph rows use bits 7..3 (5 px wide), 6 rows are drawn.
Glyph index: 0..9 = '0'..'9', 10 '.', 11 '!', 12..37 = 'A'..'Z' (either case), 38 blank, 39 '-', 40 "'", 41 solid block.
Char -> glyph ($16496): c > '@' -> (c & 31) + 11 ; else map[c & 31] with map = -8574(A4) bytes (32): 0x20->38, 0x21->11, 0x27->40,
0x2d->39, 0x2e->10, 0x30..0x39 -> 0..9, everything else -> 0.  Advance 6 px per character.
$16528(screen, glyph, x, y, bg, fg): a 6x6 opaque cell: background colour bg, glyph pixels colour fg (colours 0..15 -> plane bytes of the
table at $16634, byte = $ff for each set bit of the colour index).
"""
import struct


def glyph_of(c, cmap):
    if c > 0x40:
        return (c & 0x1F) + 11
    return cmap[c & 0x1F]


def blit_glyph(scr, font, glyph, x, y, bg, fg):
    """scr: bytearray 32000 (ST low-res). exact transcription of $16528 at byte level."""
    d2 = (x >> 3) & 1
    base = ((x & 0xFFF0) >> 1) + y * 160 + d2          # A0: byte offset of plane-0 byte
    a2off = base + (1 if d2 == 0 else 7)               # A2
    d3 = x & 7
    g = font[(glyph & 0xFF) * 8:(glyph & 0xFF) * 8 + 8]
    bgp = [0xFF if (bg >> p) & 1 else 0 for p in range(4)]
    fgp = [0xFF if (fg >> p) & 1 else 0 for p in range(4)]
    for row in range(6):
        d1 = ((g[row] << 8) & 0xFFFF) >> d3
        d5 = d1 >> 8; d6 = d1 & 0xFF
        d4 = 0x03FF
        d4 = ((d4 >> d3) | (d4 << (16 - d3))) & 0xFFFF if d3 else d4
        mlo = d4 & 0xFF; mhi = d4 >> 8
        for p in range(4):
            a0 = base + row * 160 + 2 * p
            a2 = a2off + row * 160 + 2 * p
            # A2 byte keeps mlo, A0 byte keeps mhi
            scr[a2] &= mlo
            scr[a0] &= mhi
            d7 = ((~d5) & 0xFF) & bgp[p] | (d5 & fgp[p])
            d7 &= (~mhi) & 0xFF
            scr[a0] |= d7
            d7b = ((~d6) & 0xFF) & bgp[p] | (d6 & fgp[p])
            d7b &= (~mlo) & 0xFF
            scr[a2] |= d7b


def draw_text(scr, font, cmap, s, x, y, bg, fg):
    for ch in s.encode('ascii'):
        blit_glyph(scr, font, glyph_of(ch, cmap), x, y, bg, fg)
        x += 6
